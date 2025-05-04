import { useEffect, useState } from "react";
import logoPng from "./assets/logo.png";
import { getPortfolio, type Portfolio } from "./libraries";

import { Chart, DatePicker, Ticker, TickerList } from "./components";
import dayjs from "dayjs";
import { type TData } from "./libraries/types";
import { type PickerValue } from "@mui/x-date-pickers/internals";
import { roundToN } from "./libraries/utils";

function App() {
  const [selectedDate, setSelectedDate] = useState<PickerValue>();
  const [selectedTicker, setSelectedTicker] = useState<string>("");

  const [portfolio, setgetPortfolio] = useState<Portfolio>();

  const chartData: Array<TData> | undefined = portfolio?.rounded_weights.map(
    (weight, i) => ({
      id: portfolio.tickers[i],
      value: roundToN(weight * 100, 8),
      label: portfolio.tickers[i],
    })
  );

  useEffect(() => {
    (async () => {
      const resp = await getPortfolio(selectedDate?.format("YYYY-MM-DD"));
      if (resp.result) {
        setgetPortfolio(resp.data as Portfolio);
        setSelectedTicker((resp.data as Portfolio).tickers[0]);
      } else {
      }
    })();
  }, [selectedDate]);

  return (
    <>
      <div
        className="__header"
        style={{
          height: 60,
          backgroundColor: "var(--gray-800)",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            height: "100%",
            display: "flex",
            alignItems: "center",
            gap: 20,
            // padding: "0 40px",
            width: 1000,
          }}
        >
          <a href="https://vite.dev" target="_blank">
            <img
              src={logoPng}
              className="logo"
              alt="Vite logo"
              width={26}
              height={26}
            />
          </a>
          <h1>AI Portfolio Manager</h1>
        </div>
      </div>

      <div
        className="__body"
        style={{
          padding: 40,
          display: "flex",
          flexDirection: "column",
          gap: 28,
        }}
      >
        <div
          style={{
            backgroundColor: "var(--gray-700)",
            borderRadius: 8,
            padding: 16,
            display: "flex",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              width: 1000,
              display: "flex",
              alignItems: "center",
              gap: 40,
            }}
          >
            <DatePicker
              value={dayjs(selectedDate || portfolio?.date)}
              onChange={(value) => setSelectedDate(value)}
            />
            {portfolio !== undefined && (
              <>
                <div style={{ fontSize: 16 }}>
                  <span style={{ fontWeight: "bold" }}>Return :</span>{" "}
                  {(portfolio.expected_return * 100).toFixed(2)}%
                </div>

                <div style={{ fontSize: 16 }}>
                  <span style={{ fontWeight: "bold" }}>Long Ratio :</span>{" "}
                  {(portfolio.long_ratio * 100).toFixed(2)}%
                </div>
              </>
            )}
          </div>
        </div>

        <div
          style={{
            backgroundColor: "var(--gray-700)",
            borderRadius: 8,
            padding: 24,
            display: "flex",
            justifyContent: "center",
            // flexDirection: "column",
            gap: 32,
          }}
        >
          <div style={{ display: "flex", width: 1000 }}>
            <div style={{ flex: "1 0 50%" }}>
              {chartData !== undefined && <Chart data={chartData} />}
            </div>
            <div style={{ flex: "1 0 50%" }}>
              <div className="__body_tickerlist">
                {chartData !== undefined && (
                  <TickerList
                    data={chartData}
                    onSelect={(ticker: string) => setSelectedTicker(ticker)}
                  />
                )}
              </div>
            </div>
          </div>
        </div>

        {selectedTicker && (
          <div
            style={{
              backgroundColor: "var(--gray-700)",
              padding: 40,
              borderRadius: 8,
            }}
          >
            <Ticker ticker={selectedTicker} />
          </div>
        )}
      </div>
    </>
  );
}

export default App;
