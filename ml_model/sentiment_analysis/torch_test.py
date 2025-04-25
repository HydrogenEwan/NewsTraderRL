import torch
print("Torch version:", torch.__version__)
print("CUDA support:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("CUDA version:", torch.version.cuda)
    print("GPU count:", torch.cuda.device_count())
    print("Current device name:", torch.cuda.get_device_name(0))