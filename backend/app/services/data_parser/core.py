from app.utils.excel_utils import merge_excel_headers_with_info
from typing import List, Dict, Any
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from fastapi import UploadFile

class DataParser:
    """Service layer for parsing data from Excel files."""
    def __init__(self):
        self.json_output_parser = JsonOutputParser()
        self.chat_openai = ChatOpenAI(model="gpt-4.1", temperature=0)

    def parse_llm_response(self, data: str) -> Dict[str, Any]:
        """Parse the data from the Excel file."""
        return self.json_output_parser.parse(data)
    
    def parse_excel_file(self, excel_file: UploadFile) -> Dict:
        """Parse the Excel file."""
        df, info = merge_excel_headers_with_info(excel_file)
        

        
    