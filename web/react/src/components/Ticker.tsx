import { useEffect, useState } from "react";
import { type TData } from "../libraries/types";
import { getDetail, type Ticker as TTicker } from "../libraries/portfolio";

import TickerChart from "./TickerChart";

const Ticker = ({ ticker }: { ticker: TData["label"] }) => {
  const [data, setData] = useState<TTicker>();

  useEffect(() => {
    if (ticker) {
      (async () => {
        const resp = await getDetail(ticker);
        setData(resp.data as TTicker);
      })();
    }
  }, [ticker]);

  return data !== undefined ? (
    <div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <div style={{ width: 1000 }}>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 36 }}>
            <div
              style={{
                flex: "0 1 350px",
                display: "flex",
                flexDirection: "column",
                gap: 24,
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <img src={data?.company_profile.logo} width={30} height={30} />

                <div
                  style={{
                    fontSize: 16,
                    fontWeight: "var(--font-bold)",
                    paddingBottom: "12px",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <div style={{ paddingTop: 3 }}>
                    {data.company_profile.name}
                  </div>
                </div>

                <div
                  style={{ display: "flex", flexDirection: "column", gap: 8 }}
                >
                  <div
                    style={{ display: "flex", flexDirection: "column", gap: 4 }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                      }}
                    >
                      <div>Ticker</div>
                      <div>{data.company_profile.ticker}</div>
                    </div>
                  </div>

                  <div
                    style={{ display: "flex", flexDirection: "column", gap: 4 }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                      }}
                    >
                      <div>Exchange</div>
                      <div>{data.company_profile.exchange}</div>
                    </div>
                  </div>

                  <div
                    style={{ display: "flex", flexDirection: "column", gap: 4 }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                      }}
                    >
                      <div>Industry</div>
                      <div>{data.company_profile.finnhub_industry}</div>
                    </div>
                  </div>

                  <div
                    style={{ display: "flex", flexDirection: "column", gap: 4 }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                      }}
                    >
                      <div>Sector</div>
                      <div>{data.company_profile.gsector}</div>
                    </div>
                  </div>

                  <div
                    style={{ display: "flex", flexDirection: "column", gap: 4 }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                      }}
                    >
                      <div>Group</div>
                      <div>{data.company_profile.ggroup}</div>
                    </div>
                  </div>

                  <div
                    style={{ display: "flex", flexDirection: "column", gap: 4 }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                      }}
                    >
                      <div>Market Cap</div>
                      <div>{data.company_profile.market_capitalization}</div>
                    </div>
                  </div>

                  <div
                    style={{ display: "flex", flexDirection: "column", gap: 4 }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                      }}
                    >
                      <div>Currency</div>
                      <div>{data.company_profile.currency}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* ////// */}
              <div>
                <div>
                  <div
                    style={{ display: "flex", flexDirection: "column", gap: 4 }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                      }}
                    >
                      <div>Sentiment Score</div>
                      <div>
                        {data.sentiment.label} : {data.sentiment.avg_score}
                        {/* {formatVolume(data.company_profile.market_capitalization)} */}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div style={{ flexGrow: 1 }}>
              <TickerChart data={data.chart} />
            </div>
          </div>

          <div>
            <div
              style={{
                fontWeight: "bold",
                padding: "20px 0 12px 0",
                fontSize: 16,
              }}
            >
              NEWS
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {data.news.map(({ headline, date }) => (
                <div>
                  <span
                    style={{
                      color: "gray",
                      width: 80,
                      display: "inline-block",
                    }}
                  >
                    {date}
                  </span>{" "}
                  <span
                  // style={{
                  //   overflow: "hidden",
                  //   whiteSpace: "nowrap",
                  //   textOverflow: "ellipsis",
                  //   wordBreak: "break-all",
                  // }}
                  >
                    {headline}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  ) : (
    <></>
  );
};

export default Ticker;
