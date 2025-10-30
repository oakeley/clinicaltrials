"""
Main entry point for the Clinical Trials data query application.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

from ods_reader import ODSReader
from disease_extractor import DiseaseExtractor
from ollama_client import OllamaClient
from clinical_trials_api import ClinicalTrialsAPI
from data_processor import DataProcessor
from ods_writer import ODSWriter
from report_generator import ReportGenerator


def setup_logging(config: Dict[str, Any]) -> None:
    """
    Configure logging based on config settings.

    Args:
        config: Configuration dictionary
    """
    logging_config = config.get('logging', {})

    log_level_str = logging_config.get('level', 'INFO')
    log_level = getattr(logging, log_level_str)
    log_file = logging_config.get('log_file', 'clinical_trials_query.log')
    console_output = logging_config.get('console_output', True)

    handlers = []

    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    handlers.append(file_handler)

    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)

    logging.basicConfig(
        level=log_level,
        handlers=handlers
    )

    logging.info(f"Logging initialized at {log_level_str} level")
    logging.info(f"Log file: {log_file}")


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    return config


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by replacing spaces and removing punctuation.
    Also normalizes Unicode characters to avoid font errors in reports.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for use in paths and reports
    """
    import unicodedata
    import re

    # Normalize Unicode characters to ASCII equivalents
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')

    # Replace spaces with underscores
    filename = filename.replace(' ', '_')

    # Remove all punctuation except underscores, hyphens, and dots
    filename = re.sub(r'[^\w\-.]', '', filename)

    # Remove multiple consecutive underscores
    filename = re.sub(r'_+', '_', filename)

    return filename


def main():
    """
    Main application entry point.
    """
    parser = argparse.ArgumentParser(
        description='Query ClinicalTrials.gov using data from ODS spreadsheet'
    )
    parser.add_argument(
        'ods_file',
        type=str,
        help='Path to the ODS file to process'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Path to configuration file (default: config.json)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output folder name (default: uses UNIX timestamp)'
    )
    parser.add_argument(
        '--disease-column',
        type=str,
        default='C',
        help='Column letter for disease extraction (default: C, was originally O)'
    )
    parser.add_argument(
        '--datarow',
        type=int,
        default=2,
        help='Row number where data starts, 1-based like Excel (default: 2, meaning row 1 is header, row 2+ is data). Use 1 for no headers, 3+ if headers are in row 2, etc.'
    )
    parser.add_argument(
        '--no-filters',
        action='store_true',
        help='Disable API filters (interventional, industry, date range)'
    )
    parser.add_argument(
        '--years-back',
        type=int,
        default=10,
        help='Number of years back for completion date filter (default: 10)'
    )

    args = parser.parse_args()

    ods_file_path = args.ods_file
    config_file_path = args.config

    if not Path(ods_file_path).exists():
        print(f"Error: ODS file not found: {ods_file_path}")
        sys.exit(1)

    if not Path(config_file_path).exists():
        print(f"Error: Config file not found: {config_file_path}")
        sys.exit(1)

    # Create output folder
    import time
    if args.output:
        output_folder_name = sanitize_filename(args.output)
    else:
        output_folder_name = str(int(time.time()))

    output_dir = Path('output') / output_folder_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate base filename from input ODS file
    ods_basename = Path(ods_file_path).stem
    base_filename = sanitize_filename(ods_basename)

    config = load_config(config_file_path)

    # Update logging config to use output folder
    if 'logging' in config:
        config['logging']['log_file'] = str(output_dir / f"{base_filename}_query.log")

    setup_logging(config)

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Clinical Trials Data Query Application Starting")
    logger.info("=" * 60)
    logger.info(f"ODS File: {ods_file_path}")
    logger.info(f"Config: {config_file_path}")
    logger.info(f"Output Folder: {output_dir}")
    logger.info(f"Base Filename: {base_filename}")

    logger.info("Step 1: Reading ODS file")
    ods_reader = ODSReader(ods_file_path)
    structured_data = ods_reader.get_structured_data()
    logger.info(f"Loaded {len(structured_data)} sheets from ODS file")

    disease_column = args.disease_column.upper()
    data_start_row = args.datarow
    logger.info(f"Step 2: Extracting disease names from column {disease_column} of first sheet")
    logger.info(f"Data starts at row {data_start_row} (1-based)")
    disease_extractor = DiseaseExtractor()

    data_preview = disease_extractor.get_sample_data_preview(structured_data, max_rows=3)
    logger.info(f"\n{data_preview}")

    raw_diseases = disease_extractor.extract_from_column(structured_data, disease_column, data_start_row)

    if not raw_diseases:
        logger.error(f"No diseases found in column {disease_column}!")
        logger.info(f"Please check that column {disease_column} contains disease names")
        print(f"ERROR: No diseases found in column {disease_column} of the ODS file.")
        sys.exit(1)

    logger.info(f"Extracted {len(raw_diseases)} unique diseases from column {disease_column}")

    use_ollama_dedup = config.get('ollama', {}).get('use_for_deduplication', False)
    ollama_disease_limit = config.get('ollama', {}).get('deduplication_limit', 500)

    disease_mapping = []
    ollama_model_used = None

    if use_ollama_dedup and len(raw_diseases) <= ollama_disease_limit:
        ollama_config = config.get('ollama', {})
        ollama_model_used = ollama_config.get('model', 'qwen3-30b-256k')
        logger.info(f"Step 3: Deduplicating and optimizing {len(raw_diseases)} diseases with Ollama ({ollama_model_used})")

        ollama_client = OllamaClient(
            model=ollama_model_used,
            base_url=ollama_config.get('base_url', 'http://localhost:11434'),
            timeout=ollama_config.get('timeout', 600)
        )

        try:
            diseases, disease_mapping = ollama_client.deduplicate_diseases(raw_diseases)
            if not diseases:
                logger.warning("Ollama deduplication returned empty, using simple deduplication")
                diseases, disease_map = disease_extractor.deduplicate_diseases(raw_diseases)
                diseases = list(diseases)
                disease_mapping = []
                ollama_model_used = None
            else:
                logger.info(f"Ollama optimized {len(raw_diseases)} -> {len(diseases)} search terms")
        except Exception as e:
            logger.warning(f"Ollama deduplication failed: {e}")
            logger.info(f"Falling back to simple deduplication")
            diseases, disease_map = disease_extractor.deduplicate_diseases(raw_diseases)
            diseases = list(diseases)
            disease_mapping = []
            ollama_model_used = None
    else:
        if use_ollama_dedup:
            logger.info(f"Step 3: Skipping Ollama deduplication ({len(raw_diseases)} diseases exceeds limit of {ollama_disease_limit})")
        else:
            logger.info(f"Step 3: Using simple deduplication (Ollama disabled in config)")
        diseases, disease_map = disease_extractor.deduplicate_diseases(raw_diseases)
        diseases = list(diseases)

    logger.info(f"Final disease count: {len(diseases)}")
    logger.info(f"Sample diseases: {diseases[:10]}")

    ct_config = config.get('clinicaltrials', {})
    logger.info("Step 4: Initializing ClinicalTrials.gov API client")
    ct_api = ClinicalTrialsAPI(
        base_url=ct_config.get('api_base_url', 'https://clinicaltrials.gov/api/v2'),
        max_studies=ct_config.get('max_studies', 1000),
        rate_limit_delay=ct_config.get('rate_limit_delay', 1.0)
    )

    apply_filters = not args.no_filters
    years_back = args.years_back

    logger.info("Step 5: Querying clinical trials for each disease")
    logger.info(f"Querying ALL {len(diseases)} diseases (no limit)")
    if apply_filters:
        logger.info(f"Filters enabled: INTERVENTIONAL studies, INDUSTRY sponsors, completion within last {years_back} years")
    else:
        logger.info("Filters disabled: all study types, all sponsors, all dates")
    logger.info("This may take several minutes due to API rate limiting...")
    trials_by_disease = {}

    diseases_to_query = diseases
    logger.info(f"Will query {len(diseases_to_query)} diseases")

    raw_api_data_by_disease = {}
    failed_queries = []

    for disease in diseases_to_query:
        disease_lower = disease.lower()
        logger.info(f"Querying trials for disease: {disease} (query: {disease_lower})")

        try:
            api_response = ct_api.query_by_disease(disease_lower, apply_filters=apply_filters, years_back=years_back)

            if 'error' in api_response:
                logger.error(f"Query failed for {disease}: {api_response['error']}")
                failed_queries.append(disease)
                continue

            studies = api_response['studies']
            logger.info(f"API returned {len(studies)} studies for {disease} (sorted by most recent)")

            raw_api_data_by_disease[disease] = {
                'raw_api_response': api_response['raw_api_response'],
                'query_params': api_response['query_params'],
                'total_count': api_response['total_count']
            }

            detailed_trials = []
            for study in studies:
                try:
                    detailed_info = ct_api.extract_detailed_study_info(study)
                    detailed_trials.append(detailed_info)
                except Exception as e:
                    logger.warning(f"Failed to extract info from study: {e}")
                    continue

            if detailed_trials:
                trials_by_disease[disease] = detailed_trials
                logger.info(f"Processed {len(detailed_trials)} trials for {disease}")
            else:
                logger.warning(f"No trials found for {disease}")

        except Exception as e:
            logger.error(f"Unexpected error querying {disease}: {e}")
            failed_queries.append(disease)
            continue

    total_trials = sum(len(trials) for trials in trials_by_disease.values())
    logger.info(f"Total trials retrieved across {len(trials_by_disease)} diseases: {total_trials}")
    logger.info(f"Raw API data stored for {len(raw_api_data_by_disease)} diseases")

    if failed_queries:
        logger.warning(f"Failed to query {len(failed_queries)} diseases: {failed_queries[:10]}")
        if len(failed_queries) > 10:
            logger.warning(f"... and {len(failed_queries) - 10} more")

    if total_trials == 0 and len(trials_by_disease) == 0:
        logger.error("No trials found for any disease!")
        logger.error("Check if ClinicalTrials.gov API is accessible and disease names are correct")
        if failed_queries:
            logger.error(f"Additionally, {len(failed_queries)} queries failed")
        print("\nWARNING: No clinical trials found for any disease.")
        print("This could mean:")
        print("  - The disease names in your ODS file don't match ClinicalTrials.gov database")
        print("  - The filters are too restrictive")
        print("  - The ClinicalTrials.gov API is not accessible")
        if failed_queries:
            print(f"  - {len(failed_queries)} diseases failed to query")
        print("\nContinuing with output generation...")

    logger.info("Step 6: Organizing results by disease")
    processor = DataProcessor()
    organized_data = processor.organize_results_by_disease(diseases_to_query, trials_by_disease)

    logger.info("Step 7: Preparing comprehensive JSON output with raw API data")
    all_trials = [trial for trials in trials_by_disease.values() for trial in trials]

    combined_data = {
        'metadata': {
            'timestamp': organized_data['metadata']['timestamp'],
            'total_diseases_extracted': len(raw_diseases),
            'total_diseases_deduplicated': len(diseases),
            'total_diseases_queried': len(diseases_to_query),
            'total_diseases_with_trials': len(trials_by_disease),
            'total_diseases_failed': len(failed_queries),
            'total_trials': total_trials,
            'max_trials_per_disease': ct_config.get('max_studies', 10000),
            'sorted_by': 'LastUpdatePostDate:desc (most recent first)',
            'source_file': ods_file_path,
            'disease_column': disease_column,
            'data_start_row': data_start_row,
            'diseases_queried': diseases_to_query,
            'failed_queries': failed_queries,
            'ollama_model': ollama_model_used,
            'disease_mapping': disease_mapping,
            'optimized_diseases': diseases if ollama_model_used else [],
            'filters_applied': {
                'enabled': apply_filters,
                'study_type': 'INTERVENTIONAL' if apply_filters else 'ALL',
                'sponsor_class': 'INDUSTRY' if apply_filters else 'ALL',
                'completion_date_years_back': years_back if apply_filters else 'ALL'
            }
        },
        'source_data': {
            'ods_structured': structured_data,
            'raw_diseases_from_column_o': raw_diseases
        },
        'raw_api_data': {
            'description': 'Complete raw API responses for each disease, queryable and referenceable',
            'by_disease': raw_api_data_by_disease
        },
        'disease_specific_results': organized_data,
        'summary_statistics': organized_data['summary_statistics'],
        'all_trials': all_trials
    }

    logger.info("JSON output includes:")
    logger.info(f"  - Raw API responses for {len(raw_api_data_by_disease)} diseases")
    logger.info(f"  - Processed trial data for {len(trials_by_disease)} diseases")
    logger.info(f"  - {total_trials} total trial records")

    json_output_file = output_dir / f"{base_filename}_results.json"
    logger.info(f"Step 8: Saving JSON results to {json_output_file}")
    processor.save_to_json(combined_data, str(json_output_file))

    logger.info("Step 9: Writing results to ODS format")
    ods_output_file = output_dir / f"{base_filename}_results.ods"
    ods_writer = ODSWriter(str(ods_output_file))
    ods_writer.write_disease_results(trials_by_disease)
    logger.info(f"ODS file saved: {ods_output_file}")

    logger.info("Step 10: Generating comprehensive analysis report with visualizations")
    report_generator = ReportGenerator(output_dir=str(output_dir), base_filename=base_filename)
    report_path = report_generator.generate_report(
        trials_by_disease,
        combined_data.get('metadata', {})
    )
    logger.info(f"Report generated: {report_path}")

    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Diseases extracted from column {disease_column}: {len(raw_diseases)}")
    logger.info(f"Diseases after Ollama deduplication: {len(diseases)}")
    logger.info(f"Diseases queried: {len(diseases_to_query)}")
    logger.info(f"Diseases with trials found: {len(trials_by_disease)}")
    logger.info(f"Failed queries: {len(failed_queries)}")
    logger.info(f"Total trials retrieved: {total_trials:,}")
    if len(trials_by_disease) > 0:
        logger.info(f"Average trials per disease: {total_trials / len(trials_by_disease):.1f}")
    logger.info(f"Max trials per disease (config limit): {ct_config.get('max_studies', 10000):,}")
    logger.info(f"Sorting: Most recent first (LastUpdatePostDate:desc)")
    if apply_filters:
        logger.info(f"Filters: INTERVENTIONAL studies, INDUSTRY sponsors, last {years_back} years")
    else:
        logger.info("Filters: DISABLED")
    logger.info("=" * 60)

    logger.info("=" * 60)
    logger.info("Application completed successfully")
    logger.info("=" * 60)

    figures_dir = output_dir / 'figures'
    figure_count = len(list(figures_dir.glob('*.png'))) if figures_dir.exists() else 0

    print(f"\n{'=' * 60}")
    print(f"COMPREHENSIVE CLINICAL TRIALS ANALYSIS COMPLETE")
    print(f"{'=' * 60}")
    print(f"\nOutput folder: {output_dir}")
    print(f"\nOutput files generated:")
    print(f"  - JSON:   {json_output_file.name}")
    print(f"  - ODS:    {ods_output_file.name}")
    print(f"  - Report: {Path(report_path).name}")
    print(f"  - Figures: figures/ ({figure_count} charts)")
    print(f"  - Log:    {Path(config.get('logging', {}).get('log_file', '')).name}")
    print(f"\nData Extraction:")
    print(f"  - Disease column: {disease_column}")
    print(f"  - Data start row: {data_start_row} (1-based)")
    print(f"  - Raw diseases extracted: {len(raw_diseases)}")
    print(f"  - Deduplicated diseases: {len(diseases)}")
    print(f"  - Diseases queried: {len(diseases_to_query)}")
    print(f"  - Diseases with trials found: {len(trials_by_disease)}")
    if failed_queries:
        print(f"  - Failed queries: {len(failed_queries)}")
    print(f"\nClinical Trials:")
    print(f"  - Total trials retrieved: {total_trials:,}")
    if len(trials_by_disease) > 0:
        print(f"  - Average per disease: {total_trials / len(trials_by_disease):.1f}")
    print(f"  - Max per disease (limit): {ct_config.get('max_studies', 10000):,}")
    print(f"  - Sorted by: Most recent first (LastUpdatePostDate:desc)")
    if apply_filters:
        print(f"  - Filters: INTERVENTIONAL, INDUSTRY sponsors, last {years_back} years")
    else:
        print(f"  - Filters: DISABLED (all studies)")
    print(f"  - Raw API data: Stored in JSON for querying/referencing")
    print(f"\nSample diseases analyzed:")
    for i, disease in enumerate(diseases_to_query[:10], 1):
        trial_count = len(trials_by_disease.get(disease, []))
        print(f"  {i}. {disease} ({trial_count} trials)")
    if len(diseases_to_query) > 10:
        print(f"  ... and {len(diseases_to_query) - 10} more diseases")
    print(f"\n{'=' * 60}")


if __name__ == '__main__':
    main()
