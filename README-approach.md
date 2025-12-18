# Extraction Approach

## Excel Production Tracking Extraction – Approach Overview

## Goal

Extract meaningful production tracking data from Excel files that vary in layout, header structure, and stage naming, without hardcoding column positions or names.

---

## Core Idea

**Separate structure from meaning.**

* Use **deterministic code** to handle Excel layout and cleanup
* Use an **LLM once per sheet** to understand column semantics
* Perform all row-level extraction deterministically

---

## High-Level Flow

```
Excel sheet
 → Parse with pandas
 → Merge multi-row / merged headers
 → Classify columns using LLM
 → Deterministic row-wise extraction
```

---

## Step-by-Step Approach

### 1. Parse Excel (Deterministic)

* Load sheets without headers
* Detect header rows vs data rows
* Preserve original layout

### 2. Merge Headers (Deterministic)

* Forward-fill merged cells horizontally
* Vertically concatenate header fragments per column
* Produce one semantic header string per column
* No interpretation or normalization at this stage

### 3. Column Classification (LLM)

* Send merged column names + sample values to the LLM
* Classify each column into:
  * identifier
  * quantity
  * stage_date
  * ignore
* Normalize stage names using semantic mapping (e.g., `feeding → sewing`)
* This step runs **once per sheet**

### 4. Deterministic Extraction

* Use the column classification map as a contract
* Loop through rows and extract values mechanically
* No LLM usage beyond this point

---

## Key Design Principles

* **LLMs classify, they don’t extract**
* **Column meaning is frozen once per sheet**
* **Row processing is fast, deterministic, and debuggable**
* **Unknown stages are mapped semantically or ignored explicitly**

---

## Why This Works

* Robust to changing Excel formats
* Avoids brittle column-name rules
* Scales efficiently (no per-row LLM calls)
* Easy to extend as new stages or fields appear

---

**In short:**
Clean the structure with code, understand the meaning with an LLM once, then extract deterministically.

# Database Schema and Model

## Overview

MongoDB is used with two collections: `production_items` and `extraction_metadata`.

---

## Models

### ProductionItemModel

Stores extracted production records.

| Field                 | Type                 | Description                                               |
| --------------------- | -------------------- | --------------------------------------------------------- |
| `order_number`      | string               | Unique order identifier                                   |
| `style`             | string               | Product style/SKU                                         |
| `fabric`, `color` | string               | Optional product attributes                               |
| `quantity`          | int                  | Order quantity                                            |
| `status`            | string               | Current status (default: "pending")                       |
| `dates`             | ProductionDates      | Milestone dates (fabric, cutting, sewing, shipping)       |
| `stages`            | Dict[str, StageData] | Stage-wise data with flexible fields                      |
| `stage_order`       | list                 | Processing order: fabric → cutting → sewing → shipping |
| `source`            | ProductionSource     | Source file and sheet name                                |

### ExtractionMetadataModel

Stores processing metadata for each uploaded file.

| Field                | Type     | Description                         |
| -------------------- | -------- | ----------------------------------- |
| `file_name`        | string   | Uploaded file name                  |
| `upload_date`      | datetime | When the file was processed         |
| `header_row_count` | int      | Number of header rows detected      |
| `original_shape`   | tuple    | Original Excel dimensions           |
| `final_shape`      | tuple    | Dimensions after processing         |
| `column_mapping`   | dict     | LLM-generated column classification |

---

## Design Notes

- **Flexible `stages` dict** allows new stages without schema changes.
- **Metadata tracking** enables debugging and audit of extraction logic along with confidence check and LLM remarks for classification which can be used to refine classification prompt.

---

## Disclaimer

I have used AI tools (Cursor, ChatGPT) for helping to understand the data and at the same time do a lot of the heavy lifting in terms of writing syntax, since no prehand warning wasn't given suggesting not to. The apporach and the method implemented remains to be my contribution. Looking forward to your review.
