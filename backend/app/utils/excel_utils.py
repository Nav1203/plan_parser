"""
Merge Multi-Row Excel Headers into Single Semantic Column Headers

This module provides functionality to convert multi-row Excel headers (with merged cells)
into meaningful single header strings per column, suitable for downstream semantic
interpretation (e.g., LLM-based stage mapping).
"""

import pandas as pd
from typing import Optional, Union
from pathlib import Path


def is_data_value(value) -> bool:
    """
    Check if a value appears to be data (numeric or date-like) rather than a header.
    
    Args:
        value: The cell value to check
        
    Returns:
        bool: True if the value appears to be data, False otherwise
    """
    if pd.isna(value):
        return False
    
    # Check if it's a numeric type
    if isinstance(value, (int, float)):
        return True
    
    # Check if it's a datetime type
    if isinstance(value, pd.Timestamp):
        return True
    
    # Convert to string for further checks
    str_val = str(value).strip()
    
    if not str_val:
        return False
    
    # Check if it looks like a number
    try:
        float(str_val.replace(',', ''))
        return True
    except (ValueError, AttributeError):
        pass
    
    # Check for date-like patterns (various formats)
    date_patterns = [
        # DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
        r'^\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}$',
        # YYYY-MM-DD
        r'^\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}$',
        # DD-MM-YY, DD/MM/YY, DD.MM.YY
        r'^\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2}$',
    ]
    
    import re
    for pattern in date_patterns:
        if re.match(pattern, str_val):
            return True
    
    return False


def is_data_row(row: pd.Series, threshold: float = 0.3) -> bool:
    """
    Determine if a row is a data row based on the proportion of data-like values.
    
    Args:
        row: A pandas Series representing a row
        threshold: Minimum proportion of data values to consider it a data row
        
    Returns:
        bool: True if the row appears to be a data row
    """
    non_null_values = row.dropna()
    
    if len(non_null_values) == 0:
        return False
    
    data_count = sum(1 for val in non_null_values if is_data_value(val))
    
    # A row is considered a data row if enough of its non-null values are data-like
    return (data_count / len(non_null_values)) >= threshold


def detect_header_row_count(df: pd.DataFrame) -> int:
    """
    Detect the number of header rows by finding the first data row.
    
    Args:
        df: DataFrame loaded without headers
        
    Returns:
        int: Number of header rows
    """
    for idx in range(len(df)):
        if is_data_row(df.iloc[idx]):
            return idx
    
    # If no data row found, assume first row is data (edge case)
    return 0


def remove_consecutive_duplicates(tokens: list) -> list:
    """
    Remove consecutive duplicate tokens from a list.
    
    Args:
        tokens: List of string tokens
        
    Returns:
        List with consecutive duplicates removed
    """
    if not tokens:
        return tokens
    
    result = [tokens[0]]
    for token in tokens[1:]:
        if token != result[-1]:
            result.append(token)
    
    return result


def merge_excel_headers(
    excel_path: Union[str, Path],
    sheet_name: Optional[Union[str, int]] = 0
) -> pd.DataFrame:
    """
    Merge multi-row Excel headers into single semantic column headers.
    
    This function converts multi-row Excel headers (with merged cells) into 
    meaningful single header strings per column. It handles:
    - 2-4 header rows
    - Merged cells (forward-filled horizontally)
    - Empty header cells
    - Various date formats in data detection
    
    Args:
        excel_path: Path to the Excel file
        sheet_name: Sheet name or index (default: 0, first sheet)
        
    Returns:
        pd.DataFrame: Cleaned DataFrame with merged headers and data rows only
        
    Example:
        >>> df = merge_excel_headers('tna-uno.xlsx')
        >>> print(df.columns.tolist())
        ['Nike Fall 2025 IO Number', 'Nike Fall 2025 Style', ...]
    """
    # Step 1: Load the Excel sheet without headers, preserving original layout
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
    
    # Step 2: Detect the number of header rows
    header_row_count = detect_header_row_count(df)
    
    if header_row_count == 0:
        # No header rows detected, return as-is with default column names
        return df
    
    # Step 3: Extract header rows
    header_df = df.iloc[:header_row_count].copy()
    
    # Step 4: Forward-fill merged header cells horizontally for each header row
    # ffill(axis=1) fills left-to-right within each row
    header_df = header_df.ffill(axis=1)
    
    # Step 5: Construct merged headers per column
    merged_headers = []
    
    for col_idx in range(len(df.columns)):
        # Collect non-empty, non-null values from header rows (top to bottom)
        header_parts = []
        
        for row_idx in range(header_row_count):
            cell_value = header_df.iloc[row_idx, col_idx]
            
            # Skip null/empty values
            if pd.isna(cell_value):
                continue
            
            # Convert to string and strip whitespace
            str_value = str(cell_value).strip()
            
            if str_value:
                header_parts.append(str_value)
        
        # Remove consecutive duplicates (e.g., "Fabric Fabric" -> "Fabric")
        header_parts = remove_consecutive_duplicates(header_parts)
        
        # Join with single space
        merged_header = ' '.join(header_parts) if header_parts else f'Column_{col_idx}'
        merged_headers.append(merged_header)
    
    # Step 6: Create the result DataFrame with merged headers
    data_df = df.iloc[header_row_count:].copy()
    data_df.columns = merged_headers
    
    # Step 7: Reset index
    data_df = data_df.reset_index(drop=True)
    
    return data_df


def merge_excel_headers_with_info(
    excel_path: Union[str, Path],
    sheet_name: Optional[Union[str, int]] = 0
) -> tuple:
    """
    Merge headers and return additional information about the processing.
    
    Args:
        excel_path: Path to the Excel file
        sheet_name: Sheet name or index
        
    Returns:
        tuple: (DataFrame, dict with processing info)
    """
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
    header_row_count = detect_header_row_count(df)
    
    result_df = merge_excel_headers(excel_path, sheet_name)
    
    info = {
        'original_shape': df.shape,
        'header_row_count': header_row_count,
        'result_shape': result_df.shape,
        'columns': result_df.columns.tolist()
    }
    
    return result_df, info