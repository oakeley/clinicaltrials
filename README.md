# Clinical Trials Data Query Application

A comprehensive Python application that extracts disease names from ODS spreadsheet files, optimizes them using AI-powered deduplication with Ollama, and queries ClinicalTrials.gov to generate detailed reports with statistics and visualizations.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [1. Python Dependencies](#1-python-dependencies)
  - [2. Ollama Setup (Required for AI Features)](#2-ollama-setup-required-for-ai-features)
- [Configuration](#configuration)
- [Usage](#usage)
- [Output Files](#output-files)
- [Application Workflow](#application-workflow)
- [Module Overview](#module-overview)
- [Command-Line Options](#command-line-options)
- [Examples](#examples)

## Features

- **Direct Disease Extraction**: Reads ODS spreadsheet files and extracts disease names from specified columns
- **AI-Powered Disease Optimization**: Uses Ollama LLM to deduplicate and optimize disease search terms for ClinicalTrials.gov
- **ClinicalTrials.gov Querying**: Queries ClinicalTrials.gov API v2 with configurable filters (interventional studies, industry sponsors, date ranges)
- **Comprehensive Trial Information**:
  - Study status, phases, and enrollment
  - Start and completion dates with duration calculations (actual, expected, or ongoing)
  - Primary and secondary outcomes with descriptions
  - Results availability and sponsor information
  - Trial URLs for direct access
- **Multiple Output Formats**:
  - **JSON**: Complete structured data including raw API responses for further analysis
  - **ODS Spreadsheet**: Human-readable format with summary sheet and per-disease sheets
  - **Markdown Report**: Comprehensive analysis with embedded visualizations
- **Automated Visualizations**:
  - Bar chart of trials per disease
  - Pie chart of trial status distribution
  - Histogram of trial durations with statistical markers
  - Bar chart of phase distribution
  - Per-disease status and phase charts
- **Configurable Filters**: Control study type, sponsor class, and date ranges
- **Detailed Logging**: Comprehensive logs of all operations for debugging and verification

## Prerequisites

- **Python 3.8 or higher**
- **Internet connection** for ClinicalTrials.gov API access
- **ODS file** containing disease names in a specified column
- **Ollama** (optional but recommended for AI-powered disease deduplication)

## Installation

### 1. Python Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

The `requirements.txt` includes:
- `odfpy>=1.4.1` - For reading and writing ODS spreadsheet files
- `requests>=2.31.0` - For API communication
- `matplotlib>=3.7.0` - For generating visualizations
- `numpy>=1.24.0` - For statistical calculations

### 2. Ollama Setup (Required for AI Features)

The application uses Ollama with the Qwen3 30B model to intelligently deduplicate and optimize disease search terms. This significantly improves search quality by:
- Correcting spelling errors
- Expanding abbreviations to full clinical terms
- Removing duplicates and synonyms
- Adding relevant comorbidities
- Optimizing terms for ClinicalTrials.gov search syntax

#### Step 1: Install Ollama

Download and install Ollama from the official website:

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**macOS:**
```bash
brew install ollama
```

**Windows:**
Download the installer from [https://ollama.com/download](https://ollama.com/download)

#### Step 2: Start Ollama Service

Start the Ollama service (it will run in the background):

```bash
ollama serve
```

Leave this running in a separate terminal, or set it up as a system service.

#### Step 3: Download the Base Model

Pull the base Qwen3 30B model (this is a large download, approximately 17GB):

```bash
ollama pull qwen3:30b
```

This may take some time depending on your internet connection.

#### Step 4: Create Extended Context Model

The application requires an extended context window (32K tokens) for processing large disease lists. Create the custom model using the provided Modelfile:

```bash
ollama create qwen3-30b-32k -f Modelfile.qwen3-30b-32k
```

This command:
- Reads the `Modelfile.qwen3-30b-32k` configuration file
- Creates a new model named `qwen3-30b-32k` based on `qwen3:30b`
- Extends the context window from the default to 32,768 tokens
- Sets temperature to 0 for deterministic output

**Contents of Modelfile.qwen3-30b-32k:**
```
FROM qwen3:30b

PARAMETER num_ctx 32768
PARAMETER temperature 0
```

#### Step 5: Verify Installation

Verify that your custom model is available:

```bash
ollama list
```

You should see `qwen3-30b-32k` in the list of available models.

#### Testing Ollama

Test that Ollama is working correctly:

```bash
ollama run qwen3-30b-32k "What is a clinical trial?"
```

If you see a response, Ollama is properly configured!

#### Ollama Configuration Notes

- **Model Name**: The config file must reference `qwen3-30b-32k` (not `qwen3:30b`)
- **Context Window**: The 32K context window allows processing up to 1000 disease terms in a single batch
- **Performance**: First run may be slow as the model loads into memory
- **Memory Requirements**: The 30B model requires approximately 20GB of RAM
- **Disabling Ollama**: Set `"use_for_deduplication": false` in `config.json` to disable AI features

## Configuration

Edit `config.json` to customize the application behavior:

### Ollama Configuration

```json
"ollama": {
  "model": "qwen3-30b-32k",
  "base_url": "http://localhost:11434",
  "timeout": 1000,
  "use_for_deduplication": true,
  "deduplication_limit": 1000
}
```

- `model`: Name of the Ollama model to use (must be `qwen3-30b-32k` or your custom model name)
- `base_url`: URL where Ollama service is running
- `timeout`: Request timeout in seconds
- `use_for_deduplication`: Enable/disable AI-powered deduplication
- `deduplication_limit`: Maximum number of diseases to process with Ollama (exceeding this falls back to simple deduplication)

### ClinicalTrials.gov API Configuration

```json
"clinicaltrials": {
  "api_base_url": "https://clinicaltrials.gov/api/v2",
  "max_studies": 10000,
  "rate_limit_delay": 1.0
}
```

- `api_base_url`: Base URL for ClinicalTrials.gov API v2
- `max_studies`: Maximum number of studies to retrieve per disease (default: 10000)
- `rate_limit_delay`: Delay between API calls in seconds (default: 1.0)

### Logging Configuration

```json
"logging": {
  "level": "INFO",
  "log_file": "clinical_trials_query.log",
  "console_output": true
}
```

- `level`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- `log_file`: Path to log file (will be created in output folder)
- `console_output`: Whether to display logs in console

## Usage

### Basic Usage

```bash
python main.py path/to/your/file.ods
```

By default, the application extracts disease names from **column C** starting at **row 2** (treating row 1 as headers).

### Specify Custom Column

To extract diseases from a different column (e.g., column O):

```bash
python main.py path/to/your/file.ods --disease-column O
```

### Specify Custom Data Start Row

If your data starts at a different row (e.g., row 3, with row 2 as headers):

```bash
python main.py path/to/your/file.ods --datarow 3
```

### Custom Output Folder

```bash
python main.py path/to/your/file.ods --output my_analysis
```

Without `--output`, the application creates a timestamped folder (e.g., `output/1698765432/`).

### Custom Configuration File

```bash
python main.py path/to/your/file.ods --config custom_config.json
```

### Disable Filters

To retrieve all study types, sponsors, and dates (not just interventional, industry, recent):

```bash
python main.py path/to/your/file.ods --no-filters
```

### Adjust Date Range

To query trials completed within the last 5 years instead of 10:

```bash
python main.py path/to/your/file.ods --years-back 5
```

## Output Files

All output files are saved to the output directory (default: `output/<timestamp>/` or `output/<custom-name>/`).

### 1. JSON File (`<basename>_results.json`)

Complete structured data including:
- **Metadata**: Extraction statistics, filter settings, Ollama model used
- **Source Data**: Original ODS file structure and extracted disease names
- **Disease Mapping**: Mapping from original terms to Ollama-optimized search terms
- **Raw API Data**: Complete API responses for each disease (queryable for reference)
- **Processed Trial Data**: Detailed trial information organized by disease
- **Summary Statistics**: Aggregate statistics across all diseases

### 2. ODS Spreadsheet (`<basename>_results.ods`)

Human-readable spreadsheet with:
- **Summary Sheet**: Overview of all diseases with counts and statistics
- **Per-Disease Sheets**: One sheet per disease containing:
  - NCT ID and title
  - Status (completed, recruiting, etc.)
  - Start and completion dates
  - Duration in months with status (actual/expected/ongoing)
  - Phase and enrollment count
  - Primary and secondary outcomes
  - Results availability
  - Sponsor name
  - Direct link to trial

### 3. Markdown Report (`<basename>_report.md`)

Comprehensive analysis report with:
- Executive summary with key metrics
- Overall statistics (status distribution, phase distribution, duration analysis)
- Disease-specific analysis sections with:
  - Per-disease statistics
  - Status and phase distribution charts
  - Top trials by enrollment
- Global visualizations
- Key findings and conclusions
- Appendix with disease term mapping (if Ollama was used)

The markdown report can be converted to PDF using pandoc:

```bash
pandoc <basename>_report.md -o report.pdf --pdf-engine=xelatex
```

### 4. Figures Directory (`figures/`)

PNG visualizations including:
- `trials_per_disease.png`: Bar chart comparing trial counts
- `status_distribution.png`: Pie chart of trial statuses
- `duration_distribution.png`: Histogram of trial durations
- `phase_distribution.png`: Bar chart of trial phases
- Per-disease charts: `<disease>_status.png`, `<disease>_phases.png`

### 5. Log File (`<basename>_query.log`)

Detailed execution log containing:
- Data extraction process
- Ollama prompts and responses (if used)
- API queries and responses
- Processing steps and statistics
- Any errors or warnings

## Application Workflow

The application follows this sequential workflow:

1. **Data Ingestion**
   - Read ODS file using the `odfpy` library
   - Extract all sheets with headers and raw row data

2. **Disease Extraction**
   - Extract disease names from specified column (default: column C)
   - Start from specified row (default: row 2)
   - Remove empty entries and collect unique values

3. **AI-Powered Deduplication** (Optional)
   - Send disease list to Ollama LLM
   - Correct spelling errors
   - Expand abbreviations (e.g., "ACS" -> "Acute Coronary Syndrome")
   - Remove duplicates and synonyms
   - Optimize for ClinicalTrials.gov search
   - Create mapping from original to optimized terms

4. **ClinicalTrials.gov Queries**
   - Query API for each disease (optimized or original)
   - Apply filters if enabled:
     - Study type: INTERVENTIONAL
     - Sponsor class: INDUSTRY
     - Completion date: within last N years
   - Sort results by most recent (LastUpdatePostDate:desc)
   - Retrieve up to max_studies per disease (default: 10,000)
   - Store raw API responses for reference

5. **Detail Extraction**
   - Extract comprehensive information from each study:
     - Identification (NCT ID, title)
     - Status and phase
     - Dates (start, primary completion, completion)
     - Duration calculation with status (actual/expected/ongoing)
     - Enrollment count
     - Primary and secondary outcomes
     - Results availability
     - Sponsor information

6. **Data Organization**
   - Organize trials by disease
   - Calculate per-disease statistics
   - Compute aggregate statistics

7. **Output Generation**
   - **JSON**: Save complete structured data with raw API responses
   - **ODS**: Create spreadsheet with summary and per-disease sheets
   - **Report**: Generate markdown report with visualizations
   - **Figures**: Save all charts as PNG files

8. **Summary Display**
   - Display execution summary in console
   - Show disease counts, trial counts, and filter settings

## Module Overview

### main.py
Main entry point that orchestrates the complete workflow. Handles command-line arguments, logging configuration, and coordinates all other modules.

### ods_reader.py
Reads ODS spreadsheet files using the `odfpy` library. Extracts data from all sheets and provides structured access to headers and rows.

### disease_extractor.py
Extracts disease names from specified columns in ODS data. Supports flexible column selection and data start row configuration. Includes basic deduplication by removing bracketed content.

### ollama_client.py
Interfaces with local Ollama LLM service. Key features:
- Disease deduplication and optimization
- Spelling correction
- Abbreviation expansion
- Search term optimization
- Prompt and response logging

### clinical_trials_api.py
Queries the ClinicalTrials.gov API v2. Features include:
- Disease-specific queries
- Configurable filters (study type, sponsor, dates)
- Pagination support for large result sets
- Comprehensive detail extraction (dates, durations, outcomes, results)
- Client-side date filtering
- Rate limiting

### data_processor.py
Processes and organizes query results:
- Disease-based organization
- Summary statistics computation
- Status and phase distribution analysis
- Duration calculations
- JSON output formatting

### ods_writer.py
Writes results to ODS spreadsheet format using `odfpy`:
- Summary sheet with overview statistics
- Per-disease sheets with detailed trial data
- Formatted headers and cells
- Sheet name sanitization

### report_generator.py
Generates comprehensive markdown reports with visualizations:
- Executive summary
- Overall statistics
- Per-disease analysis sections
- Global and per-disease charts
- Disease mapping appendix
- LaTeX-compatible formatting for PDF generation

### relationship_graph.py
Builds relationship graphs from spreadsheet data (optional module for advanced use cases):
- Node and edge management
- Cross-sheet relationship detection
- Search term extraction

## Command-Line Options

```
usage: main.py [-h] [--config CONFIG] [--output OUTPUT]
               [--disease-column DISEASE_COLUMN] [--datarow DATAROW]
               [--no-filters] [--years-back YEARS_BACK]
               ods_file

positional arguments:
  ods_file              Path to the ODS file to process

optional arguments:
  -h, --help            Show this help message and exit
  --config CONFIG       Path to configuration file (default: config.json)
  --output OUTPUT       Output folder name (default: uses UNIX timestamp)
  --disease-column DISEASE_COLUMN
                        Column letter for disease extraction (default: C)
  --datarow DATAROW     Row number where data starts, 1-based like Excel
                        (default: 2, meaning row 1 is header, row 2+ is data)
  --no-filters          Disable API filters (interventional, industry, date range)
  --years-back YEARS_BACK
                        Number of years back for completion date filter (default: 10)
```

### Column and Row Specification

- **Column Letter**: Use A, B, C, D, etc. (case-insensitive)
- **Data Row**: 1-based index (like Excel row numbers)
  - `--datarow 1`: No headers, all rows are data
  - `--datarow 2`: Row 1 is header, rows 2+ are data (default)
  - `--datarow 3`: Row 2 is header, rows 3+ are data

## Examples

### Example 1: Basic Analysis with Default Settings

```bash
python main.py diseases.ods
```

- Extracts diseases from column C
- Uses Ollama to optimize search terms
- Applies filters (interventional, industry, last 10 years)
- Creates timestamped output folder

### Example 2: Custom Column and Output

```bash
python main.py diseases.ods --disease-column O --output parkinsons_study
```

- Extracts diseases from column O
- Saves results to `output/parkinsons_study/`

### Example 3: No Headers, All Studies

```bash
python main.py diseases.ods --datarow 1 --no-filters
```

- Treats row 1 as data (no headers)
- Retrieves all study types, sponsors, and dates

### Example 4: Recent Studies Only

```bash
python main.py diseases.ods --years-back 3
```

- Only retrieves studies completed within last 3 years

### Example 5: Without Ollama

Edit `config.json` to disable Ollama:

```json
"ollama": {
  "use_for_deduplication": false
}
```

Then run:

```bash
python main.py diseases.ods
```

- Uses simple deduplication (removes bracketed content)
- No AI-powered optimization

### Example 6: Large Dataset with Custom Limits

Edit `config.json`:

```json
"clinicaltrials": {
  "max_studies": 20000,
  "rate_limit_delay": 0.5
}
```

Then run:

```bash
python main.py large_diseases.ods
```

- Retrieves up to 20,000 studies per disease
- Faster API queries (0.5 second delay)

## Troubleshooting

### Ollama Not Found

**Error**: `Failed to connect to Ollama`

**Solution**: Ensure Ollama service is running:
```bash
ollama serve
```

### Model Not Found

**Error**: `model 'qwen3-30b-32k' not found`

**Solution**: Create the custom model:
```bash
ollama pull qwen3:30b
ollama create qwen3-30b-32k -f Modelfile.qwen3-30b-32k
```

### Out of Memory

**Error**: Ollama crashes or system freezes

**Solution**: The 30B model requires ~20GB RAM. Consider:
- Using a smaller model (e.g., `qwen3:14b`)
- Disabling Ollama in config
- Adding swap space

### No Diseases Found

**Error**: `No diseases found in column C`

**Solution**:
- Verify the column letter with `--disease-column`
- Check data start row with `--datarow`
- View log file for preview of extracted data

### API Rate Limiting

**Error**: `429 Too Many Requests`

**Solution**: Increase `rate_limit_delay` in config:
```json
"rate_limit_delay": 2.0
```

### Empty Results

**Warning**: `No trials found for any disease`

**Solution**:
- Check if disease names match ClinicalTrials.gov database
- Try `--no-filters` to remove restrictive filters
- Increase `--years-back` for broader date range

## API Documentation

- **ClinicalTrials.gov API v2**: [https://clinicaltrials.gov/data-api/about-api](https://clinicaltrials.gov/data-api/about-api)
- **Study Data Structure**: [https://clinicaltrials.gov/data-api/about-api/study-data-structure](https://clinicaltrials.gov/data-api/about-api/study-data-structure)

## License

This project is provided as-is for research and analysis purposes.

## Contributing

Contributions are welcome! Please ensure that:
- Code follows the existing style
- Logging is comprehensive
- Documentation is updated
- No unicode characters are introduced in output files

## Acknowledgments

- ClinicalTrials.gov for providing the public API
- Ollama team for the local LLM infrastructure
- Qwen team for the foundation models
