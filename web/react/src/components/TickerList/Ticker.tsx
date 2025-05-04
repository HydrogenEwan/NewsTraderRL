import { type TData } from "../../libraries/types";

const Ticker = ({ value, label, onClick }: TData & { onClick(): void }) => (
  <div style={{ display: "flex", alignItems: "center", height: 24 }}>
    <div
      style={{
        flex: "0 0 120px",
        cursor: "pointer",
        fontWeight: "bold",
        paddingLeft: 16,
      }}
      onClick={onClick}
    >
      {label}
    </div>
    <div style={{ flex: "0 0 40px", fontWeight: "bold" }}>
      {value !== 0 ? (
        value > 0 ? (
          <span style={{ color: "#039855" }}>Long</span>
        ) : (
          <span style={{ color: "#D92D20" }}>Short</span>
        )
      ) : (
        ""
      )}
    </div>
    <div style={{ flex: "0 0 50px", textAlign: "right" }}>
      {Math.abs(value).toFixed(2)}%
    </div>
  </div>
);

export default Ticker;
