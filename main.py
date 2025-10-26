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
        help='Output JSON file path (overrides config)'
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

    config = load_config(config_file_path)
    setup_logging(config)

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Clinical Trials Data Query Application Starting")
    logger.info("=" * 60)
    logger.info(f"ODS File: {ods_file_path}")
    logger.info(f"Config: {config_file_path}")

    logger.info("Step 1: Reading ODS file")
    ods_reader = ODSReader(ods_file_path)
    structured_data = ods_reader.get_structured_data()
    logger.info(f"Loaded {len(structured_data)} sheets from ODS file")

    logger.info("Step 2: Extracting disease names from column O of first sheet")
    disease_extractor = DiseaseExtractor()

    data_preview = disease_extractor.get_sample_data_preview(structured_data, max_rows=3)
    logger.info(f"\n{data_preview}")

    raw_diseases = disease_extractor.extract_from_column_o(structured_data)

    if not raw_diseases:
        logger.error("No diseases found in column O!")
        logger.info("Please check that column O contains disease names")
        print("ERROR: No diseases found in column O of the ODS file.")
        sys.exit(1)

    logger.info(f"Extracted {len(raw_diseases)} unique diseases from column O")

    use_ollama_dedup = config.get('ollama', {}).get('use_for_deduplication', False)

    if use_ollama_dedup and len(raw_diseases) < 50:
        logger.info("Step 3: Deduplicating and normalizing diseases with Ollama")
        ollama_config = config.get('ollama', {})
        ollama_client = OllamaClient(
            model=ollama_config.get('model', 'qwen3:14b'),
            base_url=ollama_config.get('base_url', 'http://localhost:11434'),
            timeout=ollama_config.get('timeout', 300)
        )

        try:
            diseases = ollama_client.deduplicate_diseases(raw_diseases)
            if not diseases:
                logger.warning("Ollama deduplication returned empty, using raw diseases")
                diseases = raw_diseases
            else:
                logger.info(f"After deduplication: {len(diseases)} diseases")
        except Exception as e:
            logger.warning(f"Ollama deduplication failed: {e}")
            logger.info("Continuing with raw diseases from column O")
            diseases = raw_diseases
    else:
        logger.info(f"Step 3: Using diseases directly from column O (Ollama deduplication: disabled)")
        diseases = raw_diseases

    logger.info(f"Final disease count: {len(diseases)}")
    logger.info(f"Sample diseases: {diseases[:10]}")

    ct_config = config.get('clinicaltrials', {})
    logger.info("Step 4: Initializing ClinicalTrials.gov API client")
    ct_api = ClinicalTrialsAPI(
        base_url=ct_config.get('api_base_url', 'https://clinicaltrials.gov/api/v2'),
        max_studies=ct_config.get('max_studies', 1000),
        rate_limit_delay=ct_config.get('rate_limit_delay', 1.0)
    )

    logger.info("Step 5: Querying clinical trials for each disease")
    logger.info(f"Querying ALL {len(diseases)} diseases (no limit)")
    logger.info("This may take several minutes due to API rate limiting...")
    trials_by_disease = {}

    diseases_to_query = diseases
    logger.info(f"Will query {len(diseases_to_query)} diseases")

    raw_api_data_by_disease = {}

    for disease in diseases_to_query:
        logger.info(f"Querying trials for disease: {disease}")

        api_response = ct_api.query_by_disease(disease)
        studies = api_response['studies']
        logger.info(f"API returned {len(studies)} studies for {disease} (sorted by most recent)")

        raw_api_data_by_disease[disease] = {
            'raw_api_response': api_response['raw_api_response'],
            'query_params': api_response['query_params'],
            'total_count': api_response['total_count']
        }

        detailed_trials = []
        for study in studies:
            detailed_info = ct_api.extract_detailed_study_info(study)
            detailed_trials.append(detailed_info)

        if detailed_trials:
            trials_by_disease[disease] = detailed_trials
            logger.info(f"Processed {len(detailed_trials)} trials for {disease}")
        else:
            logger.warning(f"No trials found for {disease}")

    total_trials = sum(len(trials) for trials in trials_by_disease.values())
    logger.info(f"Total trials retrieved across {len(trials_by_disease)} diseases: {total_trials}")
    logger.info(f"Raw API data stored for {len(raw_api_data_by_disease)} diseases")

    if total_trials == 0:
        logger.error("No trials found for any disease!")
        logger.error("Check if ClinicalTrials.gov API is accessible and disease names are correct")
        print("\nERROR: No clinical trials found for any disease.")
        print("This could mean:")
        print("  - The disease names in your ODS file don't match ClinicalTrials.gov database")
        print("  - The ClinicalTrials.gov API is not accessible")
        print(f"  - Diseases searched: {diseases_to_query}")
        sys.exit(1)

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
            'total_diseases_with_trials': len(trials_by_disease),
            'total_trials': total_trials,
            'max_trials_per_disease': ct_config.get('max_studies', 10000),
            'sorted_by': 'LastUpdatePostDate:desc (most recent first)',
            'source_file': ods_file_path,
            'diseases_queried': diseases_to_query
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

    output_file = args.output or config.get('output', {}).get('json_file', 'clinical_trials_results.json')
    logger.info(f"Step 8: Saving JSON results to {output_file}")
    processor.save_to_json(combined_data, output_file)

    logger.info("Step 9: Writing results to ODS format")
    ods_output_file = output_file.replace('.json', '.ods')
    ods_writer = ODSWriter(ods_output_file)
    ods_writer.write_disease_results(trials_by_disease)
    logger.info(f"ODS file saved: {ods_output_file}")

    logger.info("Step 10: Generating comprehensive analysis report with visualizations")
    report_generator = ReportGenerator(output_dir=str(Path(output_file).parent))
    report_path = report_generator.generate_report(
        trials_by_disease,
        combined_data.get('metadata', {})
    )
    logger.info(f"Report generated: {report_path}")

    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Diseases extracted from column O: {len(raw_diseases)}")
    logger.info(f"Diseases after Ollama deduplication: {len(diseases)}")
    logger.info(f"Diseases with trials found: {len(trials_by_disease)}")
    logger.info(f"Total trials retrieved: {total_trials:,}")
    logger.info(f"Average trials per disease: {total_trials / len(trials_by_disease):.1f}")
    logger.info(f"Max trials per disease (config limit): {ct_config.get('max_studies', 10000):,}")
    logger.info(f"Sorting: Most recent first (LastUpdatePostDate:desc)")
    logger.info("=" * 60)

    logger.info("=" * 60)
    logger.info("Application completed successfully")
    logger.info("=" * 60)

    print(f"\n{'=' * 60}")
    print(f"COMPREHENSIVE CLINICAL TRIALS ANALYSIS COMPLETE")
    print(f"{'=' * 60}")
    print(f"\nOutput files generated:")
    print(f"  - JSON:   {output_file}")
    print(f"  - ODS:    {ods_output_file}")
    print(f"  - Report: {report_path}")
    print(f"  - Figures: {Path(output_file).parent / 'figures'}/ ({len(list((Path(output_file).parent / 'figures').glob('*.png')))} charts)")
    print(f"  - Log:    {config.get('logging', {}).get('log_file', 'clinical_trials_query.log')}")
    print(f"\nData Extraction:")
    print(f"  - Raw diseases from column O: {len(raw_diseases)}")
    print(f"  - Deduplicated diseases: {len(diseases)}")
    print(f"  - Diseases with trials found: {len(trials_by_disease)}")
    print(f"\nClinical Trials:")
    print(f"  - Total trials retrieved: {total_trials:,}")
    print(f"  - Average per disease: {total_trials / len(trials_by_disease):.1f}")
    print(f"  - Max per disease (limit): {ct_config.get('max_studies', 10000):,}")
    print(f"  - Sorted by: Most recent first (LastUpdatePostDate:desc)")
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
