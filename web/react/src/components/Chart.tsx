import { PieChart } from "@mui/x-charts";
import { type TData } from "../libraries/types";

const Chart = ({ data }: { data: Array<TData> }) => (
  <div>
    <PieChart
      series={[
        {
          data: data.map((d) => ({ ...d, value: Math.abs(d.value) })),
          cornerRadius: 5,
        },
      ]}
      height={250}
      width={300}
    />
  </div>
);

export default Chart;
