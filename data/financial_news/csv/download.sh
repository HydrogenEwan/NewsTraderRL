#!/bin/bash

# exit on error
set -e

# define variables
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TARGET_FILE="$SCRIPT_DIR/keydev.csv"
GZ_FILE="$SCRIPT_DIR/keydev.csv.gz"
TEMP_FILE="$SCRIPT_DIR/temp.csv"

# download file
echo "Downloading keydev.csv.gz..."
if ! wget -q -O "$GZ_FILE" "http://finnhub.io/static/keydev.csv.gz"; then
    echo "Error: Failed to download file"
    exit 1
fi

# check if file is downloaded
if [ ! -f "$GZ_FILE" ]; then
    echo "Error: Downloaded file not found"
    exit 1
fi

# check if downloaded file is HTML (error page)
if grep -q "<html" "$GZ_FILE"; then
    echo "Error: Downloaded file is HTML (possibly an error page)"
    cat "$GZ_FILE"
    rm "$GZ_FILE"
    exit 1
fi

# unzip file
echo "Unzipping file..."
if ! gunzip -f "$GZ_FILE"; then
    echo "Error: Failed to unzip file"
    exit 1
fi

# check if unzipped file exists
if [ ! -f "$TARGET_FILE" ]; then
    echo "Error: Unzipped file not found"
    exit 1
fi

# add column headers
echo "Adding column headers..."
echo "id1,ticker,id2,datetime,headline,summary" | cat - "$TARGET_FILE" > "$TEMP_FILE" && mv "$TEMP_FILE" "$TARGET_FILE"

# clean up temporary file
if [ -f "$TEMP_FILE" ]; then
    rm "$TEMP_FILE"
fi

# verify file
if [ -f "$TARGET_FILE" ]; then
    echo "Success! File saved to: $TARGET_FILE"
    echo "File size: $(du -h "$TARGET_FILE" | cut -f1)"
    echo "Line count: $(wc -l < "$TARGET_FILE")"
else
    echo "Error: Final file not found"
    exit 1
fi