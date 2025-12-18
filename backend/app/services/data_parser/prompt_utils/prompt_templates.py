import random
import json
import pandas as pd

class SystemPromptTemplate:
    @staticmethod
    def get_system_prompt() -> str:
        return (
            """You are a data normalization expert specializing in manufacturing and production tracking spreadsheets.
You classify Excel columns into semantic roles based on header names and sample values.

You do not extract row data.
You do not infer missing information.
You only classify columns based on evidence provided.""")

class UserPromptTemplate:
    @staticmethod
    def get_user_prompt(df: pd.DataFrame) -> str:
        
        columns_samples = []
        num_samples_per_col = 2

        for col in df.columns:
            # Drop NA, get unique, convert to str
            non_null_vals = df[col].dropna().astype(str).unique()
            # Get up to num_samples_per_col random samples (or fewer if less available)
            if len(non_null_vals) == 0:
                samples = ["" for _ in range(num_samples_per_col)]
            else:
                samples = list(non_null_vals)
                random.shuffle(samples)
                samples = samples[:num_samples_per_col]
                # Pad with "" if not enough samples
                while len(samples) < num_samples_per_col:
                    samples.append("")
            columns_samples.append({
                "column_name": col,
                "sample_values": samples
            })

        columns_samples = json.dumps(columns_samples,indent=2)

        expected_output_json=json.dumps({
            "columns": [
                {
                "column_name": "string",
                "role": "identifier | quantity | stage_date | ignore",

                "field": "order_number | style | color | order_quantity | null",

                "stage": "fabric | cutting | embroidery | sewing | finishing | vap | packing | shipping | null",

                "date_type": "planned | actual | unknown | null",

                "confidence": 0.0,

                "notes": "string"
                }
            ]
        },indent=2)
        return f"""You are given column metadata extracted from a production tracking Excel sheet.

Context:
- The sheet tracks production orders through multiple manufacturing stages.
- Column headers have already been merged into single semantic strings.
- Columns may represent identifiers, quantities, stage milestone dates, or irrelevant information.
- Stage names may be abbreviated, phrased differently, or use domain-specific synonyms.

Your task:
For each column, classify it into exactly ONE of the following roles:

1. identifier
   - requires identifying one of:
     - order_number
     - style
     - color
     - fabric_spec
     - supplier

2. quantity
   - requires identifying:
     - quantity_type = order_quantity

3. stage_date
   - requires identifying:
     - normalized stage name
     - date type (planned | actual | unknown)

4. ignore

Canonical production stages:
- fabric
- cutting
- embroidery
- sewing
- finishing
- vap
- packing
- shipping

Stage mapping rules:
- If a column refers to a production stage using a different name, abbreviation, or synonym,
  map it to the closest matching canonical stage.
- Examples:
  - "feeding" → sewing
  - "line loading" → sewing
  - "fabric inhouse" → fabric
- Only ignore a column if:
  - It is clearly unrelated to production tracking, AND
  - It does not semantically map to any canonical stage.

Additional rules:
- Do NOT invent columns, stages, or values.
- Do NOT normalize or rewrite header text beyond identifying the stage name.
- Base decisions on BOTH header text and sample values.
- If planned vs actual cannot be confidently determined, use "unknown".
- Each column must be assigned exactly one role.
- Quantity columns represent total order-level quantities unless explicitly stated otherwise.

Input format:
Each column is provided as:
{{
  "column_name": "string",
  "sample_values": ["value1", "value2", "..."]
}}

Input:
{columns_samples}

Output format:
Return STRICT JSON only, matching this schema exactly:

{expected_output_json}
"""