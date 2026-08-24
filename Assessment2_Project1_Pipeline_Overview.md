# Azure Data Factory Pipeline Analysis
## Pipeline: pl_ingest_orders_incremental_with_watermark

---

## Overview
This pipeline performs an **incremental data ingestion** from a REST API (dummyjson users endpoint) to Azure SQL Database, implementing a **watermark pattern** to track processed records and avoid reprocessing data.

**Data Flow:** REST API → JSON → CSV → SQL Database (with incremental logic)

---

## Pipeline Variables
- **watermark** (Integer): Stores the ID of the last processed record to enable incremental loading

---

## Detailed Activity Breakdown

### 1. **Get Watermark** (Lookup Activity)
- **Type:** Lookup
- **Purpose:** Retrieve the last processed ID from the SQL database to enable incremental processing
- **Source:** Azure SQL Database (`GetWatermark` dataset)
- **Query:** 
  ```sql
  SELECT LastProcessedId FROM dbo.ETL_Watermark
  WHERE TargetTable = 'Users'
  ```
- **Output:** Returns `LastProcessedId` which tracks the highest ID already processed
- **Dependencies:** None (runs first in parallel with other independent activities)

---

### 2. **Set variable1** (SetVariable Activity)
- **Type:** SetVariable
- **Purpose:** Store the watermark value from the lookup into the pipeline variable for use in downstream activities
- **Action:** Sets the `watermark` variable to the `LastProcessedId` value retrieved in the previous step
- **Expression:** `@activity('Get Waternark').output.firstRow.LastProcessedId`
- **Dependencies:** Depends on "Get Watermark" (Succeeded)

---

### 3. **cp_api_to_json** (Copy Activity)
- **Type:** Copy
- **Purpose:** Extract user data from REST API and save as JSON files in Azure Blob Storage
- **Source:** 
  - Type: JsonSource (HTTP)
  - Request Method: GET
  - Dataset: `ds_users_dummyjson` (dummyjson API endpoint)
- **Sink:**
  - Type: JsonSink
  - Destination: Azure Blob Storage (`api_to_json_sink_dummyjson` dataset)
  - Copy Behavior: Preserve Hierarchy
- **Dependencies:** Depends on "Set variable1" (Succeeded)
- **Timeout:** 12 hours
- **Staging:** Disabled

---

### 4. **cp_json_to_csv** (Copy Activity)
- **Type:** Copy
- **Purpose:** Transform JSON data to CSV format with data type conversions and field mappings
- **Source:**
  - Type: JsonSource
  - Location: Azure Blob Storage (output from previous copy)
  - Dataset: `api_to_json_sink_dummyjson`
- **Sink:**
  - Type: DelimitedTextSink (CSV/TXT)
  - Destination: Azure Blob Storage (`ds_json_to_csv` dataset)
  - File Extension: `.txt`
  - Quote All Text: Enabled
- **Data Mappings:** Complex schema mapping including:
  - **Personal Info:** id, firstName, lastName, maidenName, age, gender, email, phone, username, password, birthDate
  - **Physical Attributes:** image, bloodGroup, height, weight, eyeColor, hair (color, type)
  - **Contact Info:** ip, macAddress, userAgent
  - **Address:** Full address details (address, city, state, stateCode, postalCode, coordinates, country)
  - **Financial:** Bank details (cardExpire, cardNumber, cardType, currency, iban), EIN, SSN
  - **Employment:** Company (department, name, title, address)
  - **Crypto:** Wallet details (coin, wallet, network)
  - **Other:** Role, total, skip, limit (API pagination metadata)
- **Translator:** TabularTranslator with 55+ field mappings
- **Dependencies:** Depends on "cp_api_to_json" (Succeeded)
- **Timeout:** 12 hours
- **Staging:** Disabled

---

### 5. **Script1_copy1** (Script Activity)
- **Type:** Script
- **Purpose:** Clear staging/temporary tables before loading new data
- **Target:** Azure SQL Database (`AzureSqlDatabase1`)
- **SQL Commands:** Truncate tables:
  ```sql
  TRUNCATE TABLE dbo.Blue;
  TRUNCATE TABLE dbo.Brown;
  TRUNCATE TABLE dbo.Green;
  TRUNCATE TABLE dbo.Hazel;
  ```
- **Dependencies:** Depends on "cp_json_to_csv" (Succeeded)
- **Timeout:** 2 hours

---

### 6. **CSV_to_SQL** (ExecuteDataFlow Activity)
- **Type:** Data Flow (Mapping Data Flow)
- **Purpose:** Load CSV data into SQL Database with watermark filtering (incremental load)
- **Data Flow:** `df_csv_to_sql`
- **Parameters:** 
  - `p_watermark`: Passes the watermark variable as an integer parameter to filter only new records (ID > last processed ID)
- **Compute:**
  - Core Count: 8
  - Compute Type: General
- **Trace Level:** Fine (detailed logging)
- **Dependencies:** Depends on "Script1_copy1" (Succeeded)
- **Timeout:** 12 hours
- **Key Feature:** Uses the watermark parameter to load only records with ID greater than the last processed ID (incremental logic)

---

### 7. **GetMaxId** (Lookup Activity)
- **Type:** Lookup
- **Purpose:** Retrieve the maximum ID from the Users table to update the watermark for the next run
- **Source:** Azure SQL Database (`GetWatermark` dataset)
- **Query:**
  ```sql
  SELECT MAX(id) AS MaxId
  FROM dbo.Users;
  ```
- **Output:** Returns the highest ID in the Users table
- **Dependencies:** Depends on "CSV_to_SQL" (Succeeded)

---

### 8. **Script1** (Script Activity)
- **Type:** Script
- **Purpose:** Update the watermark in the ETL_Watermark table for the next incremental run
- **Target:** Azure SQL Database (`AzureSqlDatabase1`)
- **SQL Command:**
  ```sql
  UPDATE dbo.ETL_Watermark
  SET LastProcessedId = @MaxId
  WHERE TargetTable = 'Users';
  ```
- **Input Parameter:** `MaxId` (from GetMaxId lookup)
- **Dependencies:** Depends on "GetMaxId" (Succeeded)
- **Timeout:** 2 hours
- **Purpose:** Ensures the next pipeline run only processes new records added after this execution

---

## Execution Sequence

```
┌─────────────────────┐
│ Get Watermark       │ ──┐
│ (Lookup)            │  │
└─────────────────────┘  │
                         │
                         ▼
                ┌────────────────────┐
                │ Set variable1      │
                │ (SetVariable)      │
                └────────────────────┘
                         │
                         ▼
                ┌────────────────────┐
                │ cp_api_to_json     │
                │ (Copy: API→JSON)   │
                └────────────────────┘
                         │
                         ▼
                ┌────────────────────┐
                │ cp_json_to_csv     │
                │ (Copy: JSON→CSV)   │
                └────────────────────┘
                         │
                         ▼
                ┌────────────────────┐
                │ Script1_copy1      │
                │ (Truncate tables)  │
                └────────────────────┘
                         │
                         ▼
                ┌────────────────────┐
                │ CSV_to_SQL         │
                │ (Data Flow)        │
                └────────────────────┘
                         │
                         ▼
                ┌────────────────────┐
                │ GetMaxId           │
                │ (Lookup)           │
                └────────────────────┘
                         │
                         ▼
                ┌────────────────────┐
                │ Script1            │
                │ (Update Watermark) │
                └────────────────────┘
```

---

## Data Processing Summary

| Stage | Input | Output | Format | Records |
|-------|-------|--------|--------|---------|
| Extract | dummyjson API | Azure Blob Storage | JSON | All users from API |
| Transform | JSON files | Azure Blob Storage | CSV/TXT | All users (with schema mapping) |
| Stage | CSV files | SQL (temp tables) | Staging | All users |
| Load | Staging tables | SQL dbo.Users | Database table | Only new/updated (ID > watermark) |
| Update | dbo.Users | ETL_Watermark | Metadata | Max ID from current run |

---

## Key Features & Patterns

### ✅ **Incremental Loading Pattern**
- Uses a watermark table to track the last processed ID
- Only processes records with ID > last watermark
- Updates watermark after successful load

### ✅ **Data Validation**
- Multiple lookup operations to verify data state
- Staging tables truncated before each load to ensure clean data

### ✅ **Error Handling**
- All activities have retry policy set to 0 (no automatic retry)
- Timeout set to 12 hours for copy and data flow activities
- Dependencies ensure activities run only after previous steps succeed

### ✅ **Performance Optimization**
- Data flow uses 8 core cluster for parallel processing
- No staging enabled in copy activities (direct streaming)
- Trace level set to "Fine" for detailed debugging

---

## Data Sources & Destinations

| Component | Type | Purpose |
|-----------|------|---------|
| `ds_users_dummyjson` | HTTP/REST API | Source data (dummyjson users endpoint) |
| `api_to_json_sink_dummyjson` | Azure Blob Storage | Intermediate JSON storage |
| `ds_json_to_csv` | Azure Blob Storage | CSV staging location |
| `GetWatermark` | Azure SQL Database | Watermark metadata table |
| `dbo.Users` | Azure SQL Database | Target table for user data |
| `dbo.ETL_Watermark` | Azure SQL Database | Incremental load tracking |
| `dbo.Blue, Brown, Green, Hazel` | Azure SQL Database | Temporary staging tables (truncated each run) |

---

## Notes

- **Pipeline Name Mismatch:** The pipeline is named "pl_ingest_orders_incremental_with_watermark" but actually processes user data, not orders
- **Staging Tables:** The tables Blue, Brown, Green, Hazel appear to be color-coded staging/temporary tables
- **Complex Schema:** 55+ field mappings in the JSON-to-CSV conversion, including nested object flattening
- **Watermark Strategy:** Ensures idempotent incremental loads - safe for scheduled execution
