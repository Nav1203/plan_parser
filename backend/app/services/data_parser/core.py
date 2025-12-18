from app.utils.excel_utils import merge_excel_headers_with_info
from typing import List, Dict, Any
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from fastapi import UploadFile
from pandas as pd
from app.services.data_parser.prompt_utils.prompt_templates import SystemPromptTemplate, UserPromptTemplate

class DataParser:
    """Service layer for parsing data from Excel files."""
    def __init__(self):
        self.json_output_parser = JsonOutputParser()
        self.chat_openai = ChatOpenAI(model="gpt-4.1", temperature=0)

    def parse_llm_response(self, data: str) -> Dict[str, Any]:
        """Parse the data from the Excel file."""
        return self.json_output_parser.parse(data)


    def build_prompt(self, df: pd.DataFrame) -> str:
        """Build the prompt for the LLM."""
        return SystemPromptTemplate.get_system_prompt(), UserPromptTemplate.get_user_prompt(df)
    

    def extract_mapping(self, df: pd.DataFrame) -> Dict:
        """Extract the mapping from the LLM response."""

        sys_prompt, user_prompt= self.build_prompt(df)

        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return self.parse_llm_response(self.chat_openai.invoke(messages))
    
    def parse_excel_file(self, excel_file: UploadFile|str) -> Dict:
        """Parse the Excel file."""

        if isinstance(excel_file, UploadFile):
            df=pd.read_excel(excel_file.file)
        else:
            df=pd.read_excel(excel_file)

        df, info = merge_excel_headers_with_info(excel_file)

        column_mapping=self.extract_mapping(df)

        return mapping




if __name__ == "__main__":
    data_parser=DataParser()
    print(data_parser.parse_excel_file("data/tna-uno.xlsx"))
