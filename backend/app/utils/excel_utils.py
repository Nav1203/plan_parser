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
    df: pd.DataFrame
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
    df: pd.DataFrame
) -> tuple:
    """
    Merge headers and return additional information about the processing.
    
    Args:
        excel_path: Path to the Excel file
        sheet_name: Sheet name or index
        
    Returns:
        tuple: (DataFrame, dict with processing info)
    """
    header_row_count = detect_header_row_count(df)
    
    result_df = merge_excel_headers(df)
    
    info = {
        'original_shape': df.shape,
        'header_row_count': header_row_count,
        'result_shape': result_df.shape,
        'columns': result_df.columns.tolist()
    }
    
    return result_df, info


def identify_group_columns(df: pd.DataFrame, null_threshold: float = 0.1) -> list:
    """
    Identify columns that appear to be grouped (have NaN values that should be forward-filled).
    
    These are typically columns like Style Code, Fabric Spec, Supplier where:
    - The first row of a group has the value
    - Subsequent rows in the group have NaN (inheriting from parent)
    
    Args:
        df: DataFrame with merged headers
        null_threshold: Minimum proportion of NaN values to consider a column as grouped
        
    Returns:
        list: Column names that appear to be grouped columns
    """
    group_columns = []
    
    if len(df) == 0:
        return group_columns
    
    # Iterate by column index to handle duplicate column names
    for col_idx in range(len(df.columns)):
        col_name = df.columns[col_idx]
        col_series = df.iloc[:, col_idx]
        
        null_count = int(col_series.isna().sum())
        null_ratio = null_count / len(df)
        
        # A column is considered a group column if:
        # 1. It has some NaN values (above threshold)
        # 2. But not ALL values are NaN (that would be an empty column)
        # 3. The NaN values appear to follow a pattern (not random)
        if null_threshold <= null_ratio < 1.0:
            # Check if NaN values follow a grouping pattern
            # (NaN values should follow non-NaN values, not be at the start)
            first_is_null = pd.isna(col_series.iloc[0])
            if not first_is_null:  # First value should not be NaN
                group_columns.append(col_name)
    
    return group_columns


def expand_merged_rows(
    df: pd.DataFrame,
    columns_to_fill: Optional[list] = None,
    auto_detect: bool = True,
    null_threshold: float = 0.1
) -> pd.DataFrame:
    """
    Expand merged rows by forward-filling grouped columns.
    
    In many Excel files, production orders are grouped where:
    - Multiple color variants share the same Style Code, Fabric Spec, Supplier
    - Only the first row of each group has these values filled
    - Subsequent rows have NaN for these inherited columns
    
    This function forward-fills these columns so every row has complete data.
    
    Args:
        df: DataFrame with merged headers (output from merge_excel_headers)
        columns_to_fill: Explicit list of column names to forward-fill.
                        If None and auto_detect=True, columns are auto-detected.
        auto_detect: Whether to automatically detect group columns (default: True)
        null_threshold: For auto-detection, minimum NaN ratio to consider grouped
        
    Returns:
        pd.DataFrame: DataFrame with all grouped columns forward-filled
        
    Example:
        >>> df = merge_excel_headers('tna-dos.xlsx')
        >>> df_expanded = expand_merged_rows(df)
        >>> # Now every row has Style Code, Fabric Spec, Supplier filled
    """
    result_df = df.copy()
    
    # Determine which columns to forward-fill
    if columns_to_fill is not None:
        # Use explicitly provided columns
        fill_columns = [col for col in columns_to_fill if col in result_df.columns]
    elif auto_detect:
        # Auto-detect group columns
        fill_columns = identify_group_columns(result_df, null_threshold)
    else:
        # No columns to fill
        fill_columns = []
    
    # Forward-fill the identified columns
    if fill_columns:
        result_df[fill_columns] = result_df[fill_columns].ffill()
    
    return result_df


def expand_merged_rows_with_info(
    df: pd.DataFrame,
    columns_to_fill: Optional[list] = None,
    auto_detect: bool = True,
    null_threshold: float = 0.1
) -> tuple:
    """
    Expand merged rows and return information about the expansion.
    
    Args:
        df: DataFrame with merged headers
        columns_to_fill: Explicit list of columns to forward-fill
        auto_detect: Whether to auto-detect group columns
        null_threshold: For auto-detection, minimum NaN ratio
        
    Returns:
        tuple: (expanded DataFrame, dict with expansion info)
    """
    # Get columns that will be filled
    if columns_to_fill is not None:
        fill_columns = [col for col in columns_to_fill if col in df.columns]
    elif auto_detect:
        fill_columns = identify_group_columns(df, null_threshold)
    else:
        fill_columns = []
    
    # Count NaNs before expansion (handle duplicate column names by using first occurrence)
    null_counts_before = {}
    for col in fill_columns:
        col_idx = df.columns.get_loc(col)
        if isinstance(col_idx, slice) or hasattr(col_idx, '__iter__'):
            # Duplicate column name - use first occurrence
            col_idx = col_idx.start if isinstance(col_idx, slice) else list(col_idx)[0]
        null_counts_before[col] = int(df.iloc[:, col_idx].isna().sum())
    
    # Expand
    result_df = expand_merged_rows(df, columns_to_fill, auto_detect, null_threshold)
    
    # Count NaNs after expansion
    null_counts_after = {}
    for col in fill_columns:
        col_idx = result_df.columns.get_loc(col)
        if isinstance(col_idx, slice) or hasattr(col_idx, '__iter__'):
            col_idx = col_idx.start if isinstance(col_idx, slice) else list(col_idx)[0]
        null_counts_after[col] = int(result_df.iloc[:, col_idx].isna().sum())
    
    info = {
        'columns_filled': fill_columns,
        'null_counts_before': null_counts_before,
        'null_counts_after': null_counts_after,
        'rows_affected': sum(null_counts_before.values()),
        'total_rows': len(df)
    }
    
    return result_df, info


def process_excel_file(
    excel_path: Union[str, Path],
    sheet_name: Optional[Union[str, int]] = 0,
    expand_rows: bool = True,
    columns_to_fill: Optional[list] = None
) -> pd.DataFrame:
    """
    Complete Excel processing pipeline: merge headers and expand merged rows.
    
    This is a convenience function that combines:
    1. merge_excel_headers() - Combine multi-row headers into single headers
    2. expand_merged_rows() - Forward-fill grouped columns
    
    Args:
        excel_path: Path to the Excel file
        sheet_name: Sheet name or index (default: 0)
        expand_rows: Whether to expand merged rows (default: True)
        columns_to_fill: Explicit columns to forward-fill (auto-detected if None)
        
    Returns:
        pd.DataFrame: Fully processed DataFrame with:
            - Semantic column headers
            - All rows having complete data (no grouped NaN values)
            
    Example:
        >>> df = process_excel_file('tna-dos.xlsx')
        >>> # Returns DataFrame with merged headers and expanded rows
    """
    # Step 1: Merge headers
    df = merge_excel_headers(excel_path, sheet_name)
    
    # Step 2: Expand merged rows (if requested)
    if expand_rows:
        df = expand_merged_rows(df, columns_to_fill)
    
    return df


def process_excel_file_with_info(
    df: pd.DataFrame,
    expand_rows: bool = True,
    columns_to_fill: Optional[list] = None
) -> tuple:
    """
    Complete Excel processing pipeline with detailed information.
    
    Args:
        excel_path: Path to the Excel file
        sheet_name: Sheet name or index
        expand_rows: Whether to expand merged rows
        columns_to_fill: Explicit columns to forward-fill
        
    Returns:
        tuple: (processed DataFrame, dict with processing info)
    """
    # Step 1: Merge headers with info
    df, header_info = merge_excel_headers_with_info(df)
    
    # Step 2: Expand merged rows with info (if requested)
    if expand_rows:
        df, expand_info = expand_merged_rows_with_info(df, columns_to_fill)
    else:
        expand_info = {'columns_filled': [], 'rows_affected': 0}
    
    info = {
        'header_processing': header_info,
        'row_expansion': expand_info,
        'final_shape': df.shape,
        'final_columns': df.columns.tolist()
    }
    
    return df, info