from app.utils.excel_utils import process_excel_file_with_info
from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from fastapi import UploadFile
import pandas as pd
import re
from app.services.data_parser.prompt_utils.prompt_templates import SystemPromptTemplate, UserPromptTemplate
from app.database.models import ProductionItemModel, ProductionDates, StageData, ExtractionMetadataModel
from app.database.repository import ProductionRepository, ExtractionMetadataRepository
from app.database import database
import asyncio


def parse_date_to_ddmmyyyy(value: Any) -> Optional[str]:
    """
    Parse a date value from various formats and convert to dd/mm/yyyy.
    
    Handles:
    - datetime objects (from pandas/Excel)
    - Strings with various delimiters: /, -, ., ' ', etc.
    - Various formats: dd/mm/yyyy, dd/mm/yy, dd-mm-yyyy, dd.mm.yyyy, etc.
    - Timestamps
    """
    if value is None:
        return None
    
    # Check for pandas NaN/NaT
    if pd.isna(value):
        return None
    
    # If it's already a datetime object (common from pandas/Excel)
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    
    # If it's a pandas Timestamp
    if isinstance(value, pd.Timestamp):
        return value.strftime("%d/%m/%Y")
    
    # Convert to string for parsing
    date_str = str(value).strip()
    
    if not date_str or date_str.lower() in ('nan', 'nat', 'none', ''):
        return None
    
    # Normalize delimiters: replace -, ., whitespace with /
    normalized = re.sub(r'[-.\s]+', '/', date_str)
    
    # Date format patterns to try (day-first priority)
    date_formats = [
        "%d/%m/%Y",      # 31/12/2025
        "%d/%m/%y",      # 31/12/25
        "%Y/%m/%d",      # 2025/12/31
        "%y/%m/%d",      # 25/12/31
        "%m/%d/%Y",      # 12/31/2025
        "%m/%d/%y",      # 12/31/25
        "%d/%b/%Y",      # 31/Dec/2025
        "%d/%b/%y",      # 31/Dec/25
        "%d/%B/%Y",      # 31/December/2025
        "%d/%B/%y",      # 31/December/25
        "%b/%d/%Y",      # Dec/31/2025
        "%B/%d/%Y",      # December/31/2025
    ]
    
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(normalized, fmt)
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            continue
    
    # Try pandas to_datetime as fallback (handles edge cases)
    try:
        parsed = pd.to_datetime(date_str, dayfirst=True)
        if not pd.isna(parsed):
            return parsed.strftime("%d/%m/%Y")
    except (ValueError, TypeError, Exception):
        pass
    
    # If all else fails, return None
    return None


class DataParser:
    """Service layer for parsing data from Excel files."""
    def __init__(self):
        self.json_output_parser = JsonOutputParser()
        self.chat_openai = ChatOpenAI(model="gpt-4.1", temperature=0)
        self.repository = ProductionRepository()
        self.metadata_repository = ExtractionMetadataRepository()

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
        return self.parse_llm_response(self.chat_openai.invoke(messages).content)
    
    def extract_and_transform_data(self, df: pd.DataFrame, mapping: Dict) -> List[ProductionItemModel]:
        """Extract the data from the Excel file using column mapping."""
        sheet_data = df.to_dict(orient="records")
        
        # Build lookup: column_name -> mapping info
        column_lookup = {col['column_name']: col for col in mapping['columns']}
        
        production_items = []
        
        for row in sheet_data:
            # Initialize fields for ProductionItemModel
            item_data = {
                'order_number': None,
                'style': None,
                'fabric': None,
                'color': None,
                'quantity': None,
            }
            
            # Initialize dates for each stage
            dates_data = {
                'fabric': None,
                'cutting': None,
                'sewing': None,
                'shipping': None,
            }
            
            # Initialize stages dict: stage_name -> {field_name: value}
            stages_data: Dict[str, Dict[str, Any]] = {}
            
            # Iterate through each column in the row
            for column_name, value in row.items():
                if column_name not in column_lookup:
                    continue
                    
                col_mapping = column_lookup[column_name]
                role = col_mapping['role']
                field = col_mapping.get('field')
                stage = col_mapping.get('stage')
                date_type = col_mapping.get('date_type')
                
                if role == 'ignore':
                    continue
                
                elif role == 'identifier':
                    # Map identifier fields to ProductionItemModel fields
                    if field == 'order_number':
                        item_data['order_number'] = str(value) if value is not None else None
                    elif field == 'style':
                        item_data['style'] = str(value) if value is not None else None
                    elif field == 'fabric_spec':
                        item_data['fabric'] = str(value) if value is not None else None
                    elif field == 'color':
                        item_data['color'] = str(value) if value is not None else None
                
                elif role == 'quantity':
                    # Use the first quantity field found (order_quantity)
                    if item_data['quantity'] is None and value is not None:
                        try:
                            item_data['quantity'] = int(value)
                        except (ValueError, TypeError):
                            item_data['quantity'] = None
                    
                    # Also add quantity to stage if stage is specified
                    if stage:
                        if stage not in stages_data:
                            stages_data[stage] = {}
                        field_name = field or 'quantity'
                        stages_data[stage][field_name] = value
                
                elif role == 'stage_date':
                    # Parse and format the date to dd/mm/yyyy once
                    parsed_date = parse_date_to_ddmmyyyy(value)
                    
                    if stage:
                        # Add to stages with the date_type as field name
                        if stage not in stages_data:
                            stages_data[stage] = {}
                        field_name = f"{date_type}_date" if date_type else 'date'
                        stages_data[stage][field_name] = parsed_date
                        
                        # Also map to ProductionDates if it's a known stage
                        if stage in dates_data:
                            dates_data[stage] = parsed_date
            
            # Skip rows without required fields
            if not item_data['order_number'] or not item_data['style']:
                continue
            
            # Set default quantity if not found
            if item_data['quantity'] is None:
                item_data['quantity'] = 0
            
            # Create ProductionDates if any dates exist
            production_dates = None
            if any(dates_data.values()):
                production_dates = ProductionDates(**dates_data)
            
            # Create StageData objects for each stage
            stages = {
                stage_name: StageData(stage_name=stage_name, fields=fields)
                for stage_name, fields in stages_data.items()
                if fields  # Only include stages that have data
            }
            
            # Create ProductionItemModel
            production_item = ProductionItemModel(
                order_number=item_data['order_number'],
                style=item_data['style'],
                fabric=item_data['fabric'],
                color=item_data['color'],
                quantity=item_data['quantity'],
                dates=production_dates,
                stages=stages,
            )
            
            production_items.append(production_item)
        
        return production_items
    
    async def update_database(
        self,
        objects: List[ProductionItemModel],
        file_name: str,
        info: Dict,
        column_mapping: Dict
    ) -> None:
        """Update the database with the production items and metadata."""
        await self.repository.create_many(objects)

        metadata = ExtractionMetadataModel(
            file_name=file_name,
            upload_date=datetime.utcnow(),
            header_row_count=info['header_processing']['header_row_count'],
            original_shape=info['header_processing']['original_shape'],
            final_shape=info['final_shape'],
            final_columns=info['final_columns'],
            columns_filled=info['row_expansion']['columns_filled'],
            rows_affected=info['row_expansion']['rows_affected'],
            column_mapping=column_mapping
        )
        await self.metadata_repository.create(metadata)

    async def parse_data_from_excel(self, excel_file: UploadFile|str) -> Dict:
        """Parse the Excel file."""
        import io

        # Read with header=None to preserve multi-row headers for proper detection
        content = await excel_file.read()
        df = pd.read_excel(io.BytesIO(content), header=None)

        df, info = process_excel_file_with_info(df)

        column_mapping=self.extract_mapping(df)

        # column_mapping={'columns': [{'column_name': 'Nike Fall 2025 IO Number', 'role': 'identifier', 'field': 'order_number', 'stage': None, 'date_type': None, 'confidence': 1.0, 'notes': "Header contains 'IO Number', sample values are numeric and match order number format."}, {'column_name': 'Nike Fall 2025 Style', 'role': 'identifier', 'field': 'style', 'stage': None, 'date_type': None, 'confidence': 1.0, 'notes': "Header contains 'Style', sample values are alphanumeric codes typical for style."}, {'column_name': 'Nike Fall 2025 Fabric', 'role': 'identifier', 'field': 'fabric_spec', 'stage': None, 'date_type': None, 'confidence': 1.0, 'notes': "Header contains 'Fabric', sample values are fabric compositions."}, {'column_name': 'Nike Fall 2025 Color', 'role': 'identifier', 'field': 'color', 'stage': None, 'date_type': None, 'confidence': 1.0, 'notes': "Header contains 'Color', sample values are color codes."}, {'column_name': 'Nike Fall 2025 Quantity', 'role': 'quantity', 'field': 'order_quantity', 'stage': None, 'date_type': None, 'confidence': 1.0, 'notes': "Header contains 'Quantity', sample values are numeric and match order quantities."}, {'column_name': 'Nike Fall 2025 Handover Date', 'role': 'ignore', 'field': None, 'stage': None, 'date_type': None, 'confidence': 0.7, 'notes': "Header does not match any known stage or identifier; 'Handover' is ambiguous and not a synonym for any listed stage."}, {'column_name': 'Fabric Reqd Wt', 'role': 'ignore', 'field': None, 'stage': None, 'date_type': None, 'confidence': 0.9, 'notes': 'Header refers to required fabric weight, not a tracked quantity or stage date.'}, {'column_name': 'Fabric Plan Date', 'role': 'stage_date', 'field': None, 'stage': 'fabric', 'date_type': 'planned', 'confidence': 1.0, 'notes': "Header contains 'Fabric' and 'Plan Date', sample values are dates."}, {'column_name': 'Cutting Qty', 'role': 'quantity', 'field': 'order_quantity', 'stage': None, 'date_type': None, 'confidence': 0.9, 'notes': "Header contains 'Cutting' and 'Qty', sample values are numeric; interpreted as quantity at cutting stage."}, {'column_name': 'VAP Plan', 'role': 'stage_date', 'field': None, 'stage': 'vap', 'date_type': 'planned', 'confidence': 1.0, 'notes': "Header contains 'VAP' and 'Plan', sample values are dates."}, {'column_name': 'VAP Supplier', 'role': 'identifier', 'field': 'supplier', 'stage': None, 'date_type': None, 'confidence': 1.0, 'notes': "Header contains 'Supplier', sample values are company names."}, {'column_name': 'VAP Planed Date', 'role': 'stage_date', 'field': None, 'stage': 'vap', 'date_type': 'planned', 'confidence': 1.0, 'notes': "Header contains 'VAP' and 'Planed Date', sample values are dates. Typo in 'Planed' assumed to mean 'Planned'."}, {'column_name': 'Feeding Quantity', 'role': 'quantity', 'field': 'order_quantity', 'stage': None, 'date_type': None, 'confidence': 0.8, 'notes': "Header contains 'Feeding' and 'Quantity'; 'Feeding' is a synonym for late sewing stage, but column is a quantity."}, {'column_name': 'Feeding Plan Qty', 'role': 'quantity', 'field': 'order_quantity', 'stage': None, 'date_type': None, 'confidence': 0.8, 'notes': "Header contains 'Feeding' and 'Plan Qty'; 'Feeding' is a synonym for late sewing stage, but column is a quantity."}, {'column_name': 'Feeding Planned Date', 'role': 'stage_date', 'field': None, 'stage': 'sewing', 'date_type': 'planned', 'confidence': 1.0, 'notes': "'Feeding' is a synonym for late sewing stage; header contains 'Planned Date', sample values are dates."}]}

        objects=self.extract_and_transform_data(df, column_mapping)

        await self.update_database(objects, excel_file.filename, info, column_mapping)
        
        return objects



if __name__ == "__main__":
    asyncio.run(database.connect())
    data_parser=DataParser()
    print(asyncio.run(data_parser.parse_data_from_excel("../data/tna-uno.xlsx")))
    asyncio.run(database.disconnect())
