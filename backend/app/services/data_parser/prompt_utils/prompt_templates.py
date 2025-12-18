import random
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
        return """You are given column metadata extracted from a production tracking Excel sheet.

Context:
- The sheet tracks production orders through multiple manufacturing stages.
- Column headers have already been merged into single semantic strings.
- Columns may represent identifiers, quantities, stage milestone dates, or irrelevant information.
- Stage names may be abbreviated or inconsistently phrased.

Your task:
For each column, classify it into exactly ONE of the following roles:

1. identifier
   - order_number
   - style
   - color

2. quantity
   - order_quantity

3. stage_date
   - requires identifying:
     - stage name (normalized)
     - date type (planned | actual)

4. ignore

Possible stage names:
- fabric
- cutting
- embroidery
- sewing
- finishing
- vap
- packing
- shipping


Rules:
- Do NOT invent columns, stages, or values.
- Do NOT normalize header text beyond stage name identification.
- If a column does not clearly belong to any role, mark it as "ignore".
- If unsure between planned vs actual, use "unknown".
- Base decisions on BOTH header text and sample values.

Input format:
Each column is provided as:
{
  "column_name": "string",
  "sample_values": ["value1", "value2", "..."]
}

Input:
{columns_samples_json}

Output format:
Return STRICT JSON only, matching this schema:

{
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
}""".format(columns_samples_json=columns_samples)