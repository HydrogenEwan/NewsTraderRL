import math
import gc

import numpy as np
import torch
import torch.nn as nn
from torch.distributions.normal import Normal

from .model.ASU import ASU
from .model.MSU import MSU

EPS = 1e-20


class RLActor(nn.Module):
    def __init__(self, supports, args):
        super(RLActor, self).__init__()
        self.asu = ASU(num_nodes=args.num_assets,
                       in_features=args.in_features[0],
                       hidden_dim=args.hidden_dim,
                       window_len=args.window_len,
                       dropout=args.dropout,
                       kernel_size=args.kernel_size,
                       layers=args.num_blocks,
                       supports=supports,
                       spatial_bool=args.spatial_bool,
                       addaptiveadj=args.addaptiveadj)
        if args.msu_bool:
            self.msu = MSU(in_features=args.in_features[1],
                           window_len=args.window_len,
                           hidden_dim=args.hidden_dim)
        self.args = args
        
        # Move model to device
        self.to(args.device)
        if supports is not None:
            self.supports = [s.to(args.device) for s in supports]

    def forward(self, x_a, x_m, masks=None, deterministic=False, logger=None, y=None):
        scores = self.asu(x_a, masks)
        if self.args.msu_bool:
            res = self.msu(x_m)
        else:
            res = None
        return self.__generator(scores, res, deterministic)

    def __generator(self, scores, res, deterministic=None):
        batch_size = scores.shape[0]
        num_assets = scores.shape[1]
        weights = torch.zeros((batch_size, 2 * num_assets), device=self.args.device)

        winner_scores = scores
        loser_scores = scores.sign() * (1 - scores)

        scores_p = torch.softmax(scores, dim=-1)

        w_s, w_idx = torch.topk(winner_scores, self.args.G)
        long_ratio = torch.softmax(w_s, dim=-1)

        # Create a scatter index tensor for long positions
        long_indices = torch.zeros((batch_size, self.args.G, 2), device=self.args.device, dtype=torch.long)
        long_indices[:, :, 0] = torch.arange(batch_size, device=self.args.device).unsqueeze(1).expand(-1, self.args.G)
        long_indices[:, :, 1] = w_idx
        weights.scatter_(1, w_idx, long_ratio)

        l_s, l_idx = torch.topk(loser_scores, self.args.G)
        short_ratio = torch.softmax(l_s, dim=-1)
        
        # Create a scatter index tensor for short positions
        short_indices = torch.zeros((batch_size, self.args.G, 2), device=self.args.device, dtype=torch.long)
        short_indices[:, :, 0] = torch.arange(batch_size, device=self.args.device).unsqueeze(1).expand(-1, self.args.G)
        short_indices[:, :, 1] = l_idx + num_assets
        weights.scatter_(1, l_idx + num_assets, short_ratio)

        if self.args.msu_bool:
            mu = res[..., 0]
            sigma = torch.log(1 + torch.exp(res[..., 1]))
            
            # Handle NaN values in mu and sigma
            if torch.isnan(mu).any():
                if self.logger:
                    self.logger.warning(f"NaN values detected in mu tensor. Replacing with 0.5")
                mu = torch.where(torch.isnan(mu), torch.tensor(0.5, device=self.args.device), mu)
            
            if torch.isnan(sigma).any():
                if self.logger:
                    self.logger.warning(f"NaN values detected in sigma tensor. Replacing with 0.1")
                sigma = torch.where(torch.isnan(sigma), torch.tensor(0.1, device=self.args.device), sigma)
            
            # Ensure sigma is positive and not too small
            sigma = torch.clamp(sigma, min=0.01)
            
            if deterministic:
                rho = torch.clamp(mu, 0.0, 1.0)
                rho_log_p = None
            else:
                try:
                    m = Normal(mu, sigma)
                    sample_rho = m.sample()
                    rho = torch.clamp(sample_rho, 0.0, 1.0)
                    rho_log_p = m.log_prob(sample_rho)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error in Normal distribution: {str(e)}")
                        self.logger.error(f"mu shape: {mu.shape}, sigma shape: {sigma.shape}")
                        self.logger.error(f"mu min: {mu.min()}, mu max: {mu.max()}, mu mean: {mu.mean()}")
                        self.logger.error(f"sigma min: {sigma.min()}, sigma max: {sigma.max()}, sigma mean: {sigma.mean()}")
                    # Fallback to deterministic behavior
                    rho = torch.clamp(mu, 0.0, 1.0)
                    rho_log_p = None
        else:
            rho = torch.ones((batch_size), device=self.args.device) * 0.5
            rho_log_p = None
        return weights, rho, scores_p, rho_log_p


class RLAgent():
    def __init__(self, env, actor, args, logger=None):
        self.actor = actor
        self.env = env
        self.args = args
        self.logger = logger

        self.total_steps = 0
        self.optimizer = torch.optim.Adam(self.actor.parameters(),
                                          lr=args.lr,
                                          weight_decay=args.weight_decay)

    def train_episode(self):
        self.__set_train()
        states, masks = self.env.reset()

        steps = 0
        batch_size = states[0].shape[0]

        steps_log_p_rho = []
        steps_reward_total = []
        steps_asu_grad = []

        rho_records = []

        # Initialize agent_wealth as a numpy array since environment expects numpy
        agent_wealth = np.ones((batch_size, 1), dtype=np.float32)

        while True:
            steps += 1
            # Move data to device
            x_a = torch.from_numpy(states[0]).float().to(self.args.device)
            masks = torch.from_numpy(masks).bool().to(self.args.device)
            if self.args.msu_bool:
                x_m = torch.from_numpy(states[1]).float().to(self.args.device)
            else:
                x_m = None

            weights, rho, scores_p, log_p_rho = self.actor(x_a, x_m, masks, deterministic=False)

            # Move rewards to device
            ror = torch.from_numpy(self.env.ror).float().to(self.args.device)
            normed_ror = (ror - torch.mean(ror, dim=-1, keepdim=True)) / \
                         torch.std(ror, dim=-1, keepdim=True)

            # Convert weights and rho to numpy for environment step
            # Ensure they are float32 to match environment expectations
            weights_np = weights.detach().cpu().numpy().astype(np.float32)
            rho_np = rho.detach().cpu().numpy().astype(np.float32)

            next_states, rewards, rho_labels, masks, done, info = \
                self.env.step(weights_np, rho_np)

            # For loss calculation, use the current batch's values (do not detach)
            reward_diff = rewards.total - info['market_avg_return']
            asu_grad_val = torch.log(torch.clamp(torch.sum(normed_ror * scores_p, dim=-1), min=1e-10))

            # For logging/history, detach
            if log_p_rho is not None:
                steps_log_p_rho.append(log_p_rho.detach().cpu())
            else:
                steps_log_p_rho.append(None)
            if isinstance(reward_diff, torch.Tensor):
                steps_reward_total.append(reward_diff.detach().cpu())
            else:
                steps_reward_total.append(reward_diff)
            steps_asu_grad.append(asu_grad_val.detach().cpu())

            # Update agent_wealth using numpy
            agent_wealth = np.concatenate((agent_wealth, info['total_value'][..., None]), axis=1)
            states = next_states
            rho_records.append(np.mean(rho_np))

            if done:
                if self.args.msu_bool:
                    stacked_log_p_rho = torch.stack([lp for lp in steps_log_p_rho if lp is not None], dim=-1) if any(lp is not None for lp in steps_log_p_rho) else None
                
                # Convert reward_diff to tensor if it's not already
                stacked_reward_total = []
                for rt in steps_reward_total:
                    if isinstance(rt, torch.Tensor):
                        stacked_reward_total.append(rt.to(self.args.device))
                    else:
                        # Create a tensor with requires_grad=True
                        stacked_reward_total.append(torch.tensor(rt, device=self.args.device, requires_grad=True))
                
                stacked_reward_total = torch.stack(stacked_reward_total, dim=-1)
                
                # Ensure asu_grad has requires_grad=True
                stacked_asu_grad = []
                for ag in steps_asu_grad:
                    stacked_asu_grad.append(ag.to(self.args.device).requires_grad_(True))
                stacked_asu_grad = torch.stack(stacked_asu_grad, dim=1)

                rewards_total = stacked_reward_total.transpose(0, 1)
                rewards_total = (rewards_total - torch.mean(rewards_total, dim=-1, keepdim=True)) \
                                / torch.std(rewards_total, dim=-1, keepdim=True)

                gradient_asu = torch.mean(stacked_asu_grad, dim=-1)

                # Calculate MDD using numpy
                mdd = self.cal_MDD_numpy(agent_wealth)
                # Convert mdd to tensor for torch.mean and ensure it has requires_grad=True
                mdd_tensor = torch.from_numpy(mdd).float().to(self.args.device).requires_grad_(True)
                rewards_mdd = -2 * (mdd_tensor - 0.5)

                # Combine all rewards
                if self.args.rho:
                    if self.args.msu_bool and stacked_log_p_rho is not None:
                        gradient_rho = torch.mean(stacked_log_p_rho.to(self.args.device), dim=-1)
                        gradient_rho = torch.clamp(gradient_rho, -1, 1)
                    else:
                        gradient_rho = torch.tensor(0.0, device=self.args.device, requires_grad=True)

                    loss = torch.mean(rewards_total) + self.args.rho * torch.mean(rewards_mdd) \
                            - self.args.eta * torch.mean(gradient_asu) \
                            - self.args.eta * self.args.rho * torch.mean(gradient_rho)
                else:
                    loss = torch.mean(rewards_total) + self.args.rho * torch.mean(rewards_mdd) \
                            - self.args.eta * torch.mean(gradient_asu)

                # Check for NaN values in loss
                if torch.isnan(loss):
                    print("Warning: NaN loss detected. Skipping this training step.")
                    break
                
                self.optimizer.zero_grad()
                loss.backward()
                grad_norm, grad_norm_clip = self.clip_grad_norms(self.optimizer.param_groups, self.args.max_grad_norm)
                self.optimizer.step()
                break

        rtns = (agent_wealth[:, -1] / agent_wealth[:, 0]).mean()
        avg_rho = np.mean(rho_records)
        avg_mdd = mdd.mean()
        return rtns, avg_rho, avg_mdd

    def evaluation(self, logger=None):
        self.__set_test()
        with torch.no_grad():
            states, masks = self.env.reset()

            steps = 0
            batch_size = states[0].shape[0]

            agent_wealth = np.ones((batch_size, 1), dtype=np.float32)
            rho_record = []
            while True:
                steps += 1
                x_a = torch.from_numpy(states[0]).to(self.args.device)
                masks = torch.from_numpy(masks).to(self.args.device)
                if self.args.msu_bool:
                    x_m = torch.from_numpy(states[1]).to(self.args.device)
                else:
                    x_m = None

                weights, rho, _, _ \
                    = self.actor(x_a, x_m, masks, deterministic=True)
                
                # Convert weights and rho to numpy for environment step
                weights_np = weights.detach().cpu().numpy().astype(np.float32)
                rho_np = rho.detach().cpu().numpy().astype(np.float32)
                
                next_states, rewards, _, masks, done, info = self.env.step(weights_np, rho_np)

                agent_wealth = np.concatenate((agent_wealth, info['total_value'][..., None]), axis=1)
                states = next_states

                if done:
                    break

            return agent_wealth

    def clip_grad_norms(self, param_groups, max_norm=math.inf):
        """
        Clips the norms for all param groups to max_norm
        :param param_groups:
        :param max_norm:
        :return: gradient norms before clipping
        """
        grad_norms = [
            torch.nn.utils.clip_grad_norm_(
                group['params'],
                max_norm if max_norm > 0 else math.inf,  # Inf so no clipping but still call to calc
                norm_type=2
            )
            for group in param_groups
        ]
        grad_norms_clipped = [min(g_norm, max_norm) for g_norm in grad_norms] if max_norm > 0 else grad_norms
        return grad_norms, grad_norms_clipped

    def __set_train(self):
        self.actor.train()
        self.env.set_train()

    def __set_eval(self):
        self.actor.eval()
        self.env.set_eval()

    def __set_test(self):
        self.actor.eval()
        self.env.set_test()

    def cal_MDD_numpy(self, wealth):
        """Calculate Maximum Drawdown using numpy arrays"""
        max_wealth = np.maximum.accumulate(wealth, axis=1)
        drawdown = (wealth - max_wealth) / max_wealth
        mdd = np.min(drawdown, axis=1)
        return mdd

    def cal_MDD(self, wealth):
        """Calculate Maximum Drawdown using PyTorch tensors"""
        max_wealth = torch.maximum.accumulate(wealth, dim=1)
        drawdown = (wealth - max_wealth) / max_wealth
        mdd = torch.min(drawdown, dim=1)[0]
        return mdd

    def cal_CR(self, agent_wealth):
        pr = np.mean(agent_wealth[:, 1:] / agent_wealth[:, :-1] - 1, axis=-1, keepdims=True)
        mdd = self.cal_MDD_numpy(agent_wealth)
        softplus_mdd = np.log(1 + np.exp(mdd))
        CR = pr / softplus_mdd
        return CR
