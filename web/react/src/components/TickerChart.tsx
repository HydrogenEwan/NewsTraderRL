import { createChart, ColorType, AreaSeries } from "lightweight-charts";
import { useEffect, useRef } from "react";
import { type Ticker } from "../libraries/portfolio";
import { sortBy } from "lodash";

const TickerChart = ({ data }: { data: Ticker["chart"] }) => {
  const chartContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const chartOptions = {
      layout: {
        textColor: "white",
        background: { type: ColorType.Solid, color: "#151924" },
      },
      height: 200,
    };
    const chart = createChart(
      chartContainerRef.current as HTMLElement,
      chartOptions
    );
    const areaSeries = chart.addSeries(AreaSeries, {
      lineColor: "#2962FF",
      topColor: "#2962FF",
      bottomColor: "rgba(41, 98, 255, 0.28)",
    });

    areaSeries.setData(
      sortBy(data, ["date"]).map(({ date, weight }) => ({
        value: weight,
        time: date,
      }))
    );

    chart.timeScale().fitContent();

    return () => {
      chart.remove();
    };
  }, [data]);

  return <div ref={chartContainerRef} />;
};

export default TickerChart;
