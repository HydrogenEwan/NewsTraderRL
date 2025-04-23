'''Module for fetching SEC data'''
import uuid
from pathlib import Path
from typing import Iterator
from datetime import datetime

from secedgar import filings, FilingType
from bs4 import BeautifulSoup

from common.interface.data_fetcher import DataFetcher
from common.interface.data_parser import DataParser


DOWNLOAD_DIR = Path(__file__).parent / "downloaded_sec_filings"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True) # Ensure the directory exists

class SecFetcher(DataFetcher):
    '''Class for fetching SEC data'''
    def __init__(self, parser: DataParser, ticker: str):
        '''Input: 
         - parser: DataParser object, for parsing SEC 10Q data
         - ticker: str, the ticker of the company whose data we are fetching
         '''
        # TODO:
        # Assume the ticker is fixed throughout this project
        self.parser = parser
        self.ticker = ticker

    def fetch(self, start: str, end: str) -> Iterator:
        my_filings = filings(cik_lookup=[self.ticker],
                        filing_type=FilingType.FILING_10Q,
                        user_agent="Your name (123@gmail.com)",
                        start_date=start,
                        end_date=end)
        save_dir = DOWNLOAD_DIR / f"{start}_to_{end}"
        print(f"Downloading filings to: {save_dir}")
        my_filings.save(str(save_dir))
        # Process downloaded files
        downloaded_files = list(save_dir.glob('**/*.txt'))  # Recursively search for all .txt files
        # print(f"files are {downloaded_files}")
        print(f"Successfully downloaded {len(downloaded_files)} filing(s).")

        for file_path in downloaded_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read file content and extract stock name from path
                raw = {}
                content = f.read()

                filing_id = str(uuid.uuid4())
                raw['id'] = filing_id

                ticker = str(file_path).split('/')[-3]  # Extract stock name from path structure
                raw['ticker'] = ticker

                clean_text, ts = self.clean_xml(content)
                raw['text'] = clean_text
                raw['datetime'] = ts
                # print("start")
                # print(f"content: {type(content)}")
                # print(f"file_path: {(file_path)}")
                # print(f"stock_name: {ticker}")
                # print("end")
                yield self.parser.parse(raw)

    def clean_xml(self, raw_text: str) -> tuple[str, int]:
        """Clean raw SEC filing text data by removing XBRL markup and extracting clean text.
        will also return the timestamp of the filing

        Args:
            raw_text (str): Raw SEC filing text containing XML/XBRL markup

        Returns:
            str: Cleaned text with markup removed and proper newline separators
            int: Timestamp of the filing
        """
        # Parse the raw text as XML using BeautifulSoup
        soup = BeautifulSoup(raw_text, 'xml')
        unix_ts = None
        acceptance_tag = soup.find("ACCEPTANCE-DATETIME")
        if acceptance_tag:
            # Extract the timestamp of the filing from the raw text
            # since ACCEPTANCE-DATETIME will match many paragrahs, we will use the first match
            ts = acceptance_tag.text.split('\n')[0]
            # Parse it to a datetime object
            dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
            # Convert to Unix timestamp
            unix_ts = int(dt.timestamp())
            # print("ts: ", ts)

        # Remove all ix namespace elements as they're typically XBRL markup
        for tag in soup.find_all(lambda tag: tag.name and tag.name.startswith("ix:")):
            tag.decompose()

        # Get clean text with newline separators
        clean_text = soup.get_text(separator="\n").strip()
         # Replace multiple newlines with a single newline
        clean_text = '\n'.join(line for line in clean_text.splitlines() if line.strip())
        # print("clean_text: ", clean_text)
        # print( "ts: ", ts)
        return clean_text, unix_ts
