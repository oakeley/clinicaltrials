# Clinical Trials Data Query Application

Application for querying ClinicalTrials.gov using disease names extracted from ODS spreadsheet files. Automatically generates comprehensive reports with statistics and visualizations in multiple formats (JSON, ODS, Markdown with charts).

## Features

- **Direct Disease Extraction**: Reads ODS spreadsheet files and extracts disease names from headers and cells using pattern matching
- **ClinicalTrials.gov Querying**: Queries ClinicalTrials.gov API v2 for each disease individually
- **Detailed Trial Information Extraction**:
  - Start and completion dates
  - Trial duration (actual, expected, or ongoing - calculated in days, months, years)
  - Primary and secondary objectives with descriptions
  - Success/completion status
  - Results data (if available)
  - Phase, enrollment, and sponsor information
- **Multiple Output Formats**:
  - **JSON**: Complete structured data for machine processing
  - **ODS**: Human-readable spreadsheet with summary sheet and per-disease sheets
  - **Markdown Report**: Comprehensive analysis report with embedded visualizations
- **Automated Visualizations**:
  - Bar chart of trials per disease
  - Pie chart of trial status distribution
  - Histogram of trial durations with mean/median markers
  - Bar chart of phase distribution
- **Comprehensive Logging**: Detailed logs of all operations for debugging and verification

## Prerequisites

- Python 3.8 or higher
- Internet connection for ClinicalTrials.gov API
- ODS file containing disease names in headers or cells

## Installation

1. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure the application by editing `config.json`:
   - Set the Ollama model name
   - Adjust API rate limits if needed
   - Configure logging preferences

## Usage

Basic usage:

```bash
python main.py path/to/your/file.ods
```

With custom config file:

```bash
python main.py path/to/your/file.ods --config custom_config.json
```

With custom output file:

```bash
python main.py path/to/your/file.ods --output results.json
```

## Configuration

The `config.json` file contains the following sections:

### ClinicalTrials.gov API Configuration

```json
"clinicaltrials": {
  "api_base_url": "https://clinicaltrials.gov/api/v2",
  "max_studies": 100,
  "rate_limit_delay": 1.0
}
```

- `api_base_url`: Base URL for ClinicalTrials.gov API v2
- `max_studies`: Maximum number of studies to retrieve per query
- `rate_limit_delay`: Delay between API calls in seconds

### Logging Configuration

```json
"logging": {
  "level": "INFO",
  "log_file": "clinical_trials_query.log",
  "console_output": true
}
```

- `level`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `log_file`: Path to log file
- `console_output`: Whether to output logs to console

### Output Configuration

```json
"output": {
  "json_file": "clinical_trials_results.json"
}
```

- `json_file`: Default output file path

## Output Files

The application generates multiple output files:

### 1. JSON File (clinical_trials_results.json)

Machine-readable structured data containing:
- Complete source data from ODS file
- Relationship graph with nodes and edges
- Ontology mappings for all diseases
- Disease-specific trial results with detailed information
- Summary statistics across all diseases

### 2. ODS Spreadsheet (clinical_trials_results.ods)

Human-readable spreadsheet with:
- **Summary Sheet**: Overview of all diseases with trial counts and statistics
- **Disease-Specific Sheets**: One sheet per disease with detailed trial information including:
  - NCT ID and title
  - Status and dates
  - Duration (months) and duration status (actual/expected/ongoing)
  - Phase and enrollment
  - Primary and secondary outcomes
  - Results availability
  - Sponsor and trial URL

### 3. Analysis Report (clinical_trials_report.md)

Markdown report with embedded visualizations including:
- Executive summary with key statistics
- Overall statistics (status distribution, phase distribution, duration analysis)
- Disease-specific analysis sections
- Visualizations:
  - Bar chart of trials per disease
  - Pie chart of trial status distribution
  - Histogram of trial durations
  - Bar chart of phase distribution
- Key findings and conclusions

### 4. Figures Directory (figures/)

PNG visualizations generated for the report:
- `trials_per_disease.png`
- `status_distribution.png`
- `duration_distribution.png`
- `phase_distribution.png`

## Modules

### ods_reader.py
Reads ODS files and extracts data from all sheets with structured headers and rows.

### disease_extractor.py
Extracts disease names from ODS data using:
- Pattern matching for common disease names
- Regex patterns for "X cancer", "X disease" format
- Built-in list of 40+ common diseases
- Scanning both headers and cell values

### clinical_trials_api.py
Queries the ClinicalTrials.gov API v2:
- Query by disease name
- Extract comprehensive study information with 30+ fields
- Calculate trial durations (actual, expected, ongoing)
- Extract results data if available
- Parse dates in multiple formats

### data_processor.py
Organizes and processes data:
- Organize results by disease
- Compute summary statistics (completion rates, durations, etc.)
- Generate status and phase distributions

### ods_writer.py
Writes results to ODS spreadsheet format:
- Creates summary sheet with overview statistics
- Generates one sheet per disease with detailed trial information
- Properly formats headers and cell data

### report_generator.py
Generates markdown reports with visualizations:
- Executive summary and overall statistics
- Disease-specific analysis sections
- Four automated charts (bar charts, pie chart, histogram)
- Saves figures as PNG files

### main.py
CLI entry point orchestrating the complete workflow with comprehensive logging and error handling.

## Application Workflow

1. **Data Ingestion**: Read ODS file and extract all sheet data
2. **Disease Extraction**: Scan headers and cells for disease names using pattern matching and common disease list
3. **Preview**: Display sample data from ODS file in logs
4. **API Queries**: Query ClinicalTrials.gov for each discovered disease
5. **Detail Extraction**: Extract comprehensive trial information for each study:
   - Dates (start, completion, primary completion with types)
   - Duration calculation (actual, expected, or ongoing in days/months/years)
   - Primary and secondary outcomes with descriptions
   - Results data if available
   - Phase, enrollment count, sponsor information
6. **Data Organization**: Organize all results by disease with statistics
7. **JSON Output**: Save complete structured data to JSON file
8. **ODS Output**: Generate human-readable spreadsheet with:
   - Summary sheet showing trial counts per disease
   - Individual sheets for each disease with detailed trial data
9. **Report Generation**: Create markdown analysis report with:
   - Executive summary and overall statistics
   - Disease-specific analysis sections
   - Four automated visualizations (bar charts, pie chart, histogram)
10. **Logging**: Comprehensive logging of all operations for verification

## Logging

All operations are logged to both console and file. Check the log file for detailed information about the execution process.

## Error Handling

The application does not use try-catch blocks to hide errors. All errors are logged and propagated for debugging and testing purposes.

## API Documentation

ClinicalTrials.gov API v2 documentation: https://clinicaltrials.gov/data-api/about-api/study-data-structure
