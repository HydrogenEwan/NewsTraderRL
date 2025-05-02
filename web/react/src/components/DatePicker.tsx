import {
  DatePicker as MuiDatePicker,
  type DatePickerProps,
} from "@mui/x-date-pickers";

const DatePicker = (props: DatePickerProps) => (
  <div>
    <MuiDatePicker label="Date" {...props} />
  </div>
);

export default DatePicker;
