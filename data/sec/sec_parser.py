'''Module for parsing SEC data'''

from common.interface.data_parser import DataParser
from common.model.sec import SecData # TODO: change to corresponding thing

'''
TODO:
- parse the file to content useful for sentiment models
- parse the file to mongodb entry
'''

class SecParser(DataParser):
    '''Class for parsing SEC data'''
    def parse(self, data: dict) -> SecData:
        """Parse raw SEC filing text data into structured SecData object.
        Args:
            data (dict): Raw SEC filing data containing text content.
            
        Returns:
            SecData: Structured SEC data object containing the parsed information.
            
        Example:
            >>> parser = SecParser()
            >>> raw_data = {"text": "SEC filing content..."}
            >>> sec_data = parser.parse(raw_data)
        """

        # Store the cleaned text back in raw for further processing
        return SecData.from_raw(data)