export const formatVolume = (value: number): string => {
  if (value < 1000) {
    return value.toString();
  } else if (value < 1_000_000) {
    return (value / 1_000).toFixed(1) + "K";
  } else if (value < 1_000_000_000) {
    return (value / 1_000_000).toFixed(1) + "M";
  } else if (value < 1_000_000_000_000) {
    return (value / 1_000_000_000).toFixed(1) + "B";
  } else {
    return (value / 1_000_000_000_000).toFixed(1) + "T";
  }
};

export function roundToN(num: number, n: number) {
  const factor = Math.pow(10, n);
  return Math.round(num * factor) / factor;
}
