import os
import pandas as pd

# 1. 사용자 입력 예시 (원하는 방식으로 reemplazar)
date_start = "2000-01-01"
date_end = "2009-12-31"
ticker_list = [
            "AAPL",
            "AMGN",
            "AXP",
            "BA",
            "CAT",
            "CRM",
            "CSCO",
            "CVX",
            "DIS",
            "DOW",
            "GS",
            "HD",
            "HON",
            "IBM",
            "INTC",
            "JNJ",
            "JPM",
            "KO",
            "MCD",
            "MMM",
            "MRK",
            "MSFT",
            "NKE",
            "PG",
            "TRV",
            "UNH",
            "V",
            "VZ",
            "WBA",
            "WMT"
        ]

INPUT_CSV = "/home/newstraderrl/.cache/huggingface/nasdaq_exteral_data.csv"
OUTPUT_CSV = f"/home/newstraderrl/.cache/huggingface/filtered_{date_start}_{date_end}.csv"
CHUNK_SIZE = 100_000

# 1) Count total rows (minus header) for progress reporting
print("Counting total rows in CSV…")
with open(INPUT_CSV, "r", encoding="utf-8") as f:
    total_lines = sum(1 for _ in f) - 1  # subtract header line
print(f"Total rows to process: {total_lines}")

# 2) Initialize output file
if os.path.exists(OUTPUT_CSV):
    os.remove(OUTPUT_CSV)

# 3) Read in chunks, loading all columns
reader = pd.read_csv(
    INPUT_CSV,
    chunksize=CHUNK_SIZE,
    parse_dates=["Date"],         # parse Date as datetime
    dtype={"Stock_symbol": str},  # ensure ticker is string
    encoding="utf-8"
)

processed_rows = 0
total_matches  = 0

for idx, chunk in enumerate(reader, start=1):
    rows_in_chunk = len(chunk)
    processed_rows += rows_in_chunk

    # Apply filters
    mask_date   = (chunk["Date"] >= date_start) & (chunk["Date"] <= date_end)
    mask_ticker = chunk["Stock_symbol"].isin(ticker_list)
    filtered    = chunk.loc[mask_date & mask_ticker]

    matches_in_chunk = len(filtered)
    total_matches   += matches_in_chunk

    # Write matches (all columns) to output CSV
    if not filtered.empty:
        filtered.to_csv(
            OUTPUT_CSV,
            mode="a",
            header=not os.path.exists(OUTPUT_CSV),
            index=False
        )

    # Calculate percentage done
    percent_done = processed_rows / total_lines * 100

    # Print progress in English with total-row context
    print(
        f"[Chunk {idx}] Processed {rows_in_chunk} rows "
        f"(cumulative {processed_rows}/{total_lines} → {percent_done:.2f}%) | "
        f"Matches this chunk: {matches_in_chunk} | "
        f"Total matches: {total_matches}"
    )

print(
    f"\nDone! Processed {processed_rows} rows out of {total_lines}, "
    f"with {total_matches} total matches saved to {OUTPUT_CSV}."
)