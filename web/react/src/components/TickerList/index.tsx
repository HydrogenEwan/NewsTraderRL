import { useState } from "react";
import { type TData } from "../../libraries/types";
import Ticker from "./Ticker";
import TickerSearchbar from "./TickerSearchbar";

const TickerList = ({
  data,
  onSelect,
}: {
  data: Array<TData>;
  onSelect(ticker: string): void;
}) => {
  const [query, setQuery] = useState<string>("");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ width: 450 }}>
        <TickerSearchbar
          value={query}
          onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
            setQuery(event.target.value);
          }}
        />
      </div>

      <div>
        {data
          .filter((d) => d.label.toLowerCase().includes(query.toLowerCase()))
          .map((d) => (
            <Ticker key={d.id} {...d} onClick={() => onSelect(d.label)} />
          ))}
      </div>
    </div>
  );
};

export default TickerList;
