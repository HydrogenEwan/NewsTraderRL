import { TextField, type TextFieldProps } from "@mui/material";

const TickerSearchbar = (props: TextFieldProps) => (
  <div>
    <TextField
      {...props}
      id="ticker-search-bar"
      fullWidth
      label="Ticker"
      variant="outlined"
      size="small"
    />
  </div>
);

export default TickerSearchbar;
