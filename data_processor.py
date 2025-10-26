"""
Module for processing and combining data from multiple sources.
"""

import logging
import json
from typing import Dict, Any, List
from datetime import datetime


class DataProcessor:
    """
    Processes and combines data from ODS files, relationship graphs, and API results.
    """

    def __init__(self):
        """
        Initialize the data processor.
        """
        self.logger = logging.getLogger(__name__)

    def combine_all_data(self, ods_data: Dict[str, Any], graph_data: Dict[str, Any],
                        api_results: List[Dict[str, Any]],
                        ollama_interpretation: Dict[str, Any],
                        ollama_structure: Dict[str, Any],
                        ontology_mappings: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Combine data from all sources into a single structured output.

        Args:
            ods_data: Structured data from ODS file
            graph_data: Relationship graph data
            api_results: Results from ClinicalTrials.gov API
            ollama_interpretation: Interpretation of ODS data from Ollama
            ollama_structure: Structured API results from Ollama
            ontology_mappings: Ontology term mappings for diseases

        Returns:
            Combined data dictionary
        """
        self.logger.info("Combining data from all sources")

        combined = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'source_sheets': list(ods_data.keys()),
                'total_nodes': graph_data.get('statistics', {}).get('node_count', 0),
                'total_edges': graph_data.get('statistics', {}).get('edge_count', 0),
                'api_results_count': len(api_results)
            },
            'source_data': {
                'ods_structured': ods_data,
                'relationship_graph': graph_data
            },
            'ontology_mappings': ontology_mappings or {},
            'ollama_analysis': {
                'data_interpretation': ollama_interpretation,
                'results_structure': ollama_structure
            },
            'clinical_trials': {
                'total_found': len(api_results),
                'studies': self._process_studies(api_results)
            },
            'summary': self._generate_summary(ods_data, api_results, ollama_interpretation)
        }

        self.logger.info(f"Combined data includes {len(api_results)} studies")
        return combined

    def _process_studies(self, api_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process and extract key information from API study results.

        Args:
            api_results: Raw API results

        Returns:
            List of processed study summaries
        """
        processed_studies = []

        for study in api_results:
            protocol_section = study.get('protocolSection', {})

            identification_module = protocol_section.get('identificationModule', {})
            nct_id = identification_module.get('nctId', '')
            brief_title = identification_module.get('briefTitle', '')
            official_title = identification_module.get('officialTitle', '')

            status_module = protocol_section.get('statusModule', {})
            overall_status = status_module.get('overallStatus', '')
            start_date = status_module.get('startDateStruct', {})
            completion_date = status_module.get('completionDateStruct', {})

            conditions_module = protocol_section.get('conditionsModule', {})
            conditions = conditions_module.get('conditions', [])

            interventions_module = protocol_section.get('armsInterventionsModule', {})
            interventions = interventions_module.get('interventions', [])

            description_module = protocol_section.get('descriptionModule', {})
            brief_summary = description_module.get('briefSummary', '')
            detailed_description = description_module.get('detailedDescription', '')

            sponsor_module = protocol_section.get('sponsorCollaboratorsModule', {})
            lead_sponsor = sponsor_module.get('leadSponsor', {})

            processed_study = {
                'nct_id': nct_id,
                'brief_title': brief_title,
                'official_title': official_title,
                'overall_status': overall_status,
                'start_date': start_date,
                'completion_date': completion_date,
                'conditions': conditions,
                'interventions': [
                    {
                        'type': i.get('type', ''),
                        'name': i.get('name', ''),
                        'description': i.get('description', '')
                    } for i in interventions
                ],
                'brief_summary': brief_summary,
                'detailed_description': detailed_description,
                'lead_sponsor': lead_sponsor.get('name', ''),
                'url': f"https://clinicaltrials.gov/study/{nct_id}"
            }

            processed_studies.append(processed_study)

        return processed_studies

    def _generate_summary(self, ods_data: Dict[str, Any], api_results: List[Dict[str, Any]],
                         interpretation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a high-level summary of all data.

        Args:
            ods_data: ODS structured data
            api_results: API results
            interpretation: Ollama interpretation

        Returns:
            Summary dictionary
        """
        total_ods_rows = sum(
            len(sheet_data.get('rows', []))
            for sheet_data in ods_data.values()
        )

        conditions_set = set()
        for study in api_results:
            protocol_section = study.get('protocolSection', {})
            conditions_module = protocol_section.get('conditionsModule', {})
            conditions = conditions_module.get('conditions', [])
            conditions_set.update(conditions)

        summary = {
            'total_source_sheets': len(ods_data),
            'total_source_rows': total_ods_rows,
            'total_clinical_trials_found': len(api_results),
            'unique_conditions': len(conditions_set),
            'extracted_diseases': interpretation.get('diseases', []),
            'extracted_interventions': interpretation.get('interventions', []),
            'extracted_keywords': interpretation.get('keywords', [])
        }

        return summary

    def save_to_json(self, data: Dict[str, Any], output_file: str) -> None:
        """
        Save combined data to a JSON file.

        Args:
            data: Data to save
            output_file: Output file path
        """
        self.logger.info(f"Saving combined data to: {output_file}")

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Data saved successfully to {output_file}")

    def create_summary_report(self, combined_data: Dict[str, Any]) -> str:
        """
        Create a human-readable summary report.

        Args:
            combined_data: Combined data dictionary

        Returns:
            Summary report as string
        """
        summary = combined_data.get('summary', {})
        metadata = combined_data.get('metadata', {})

        report_lines = [
            "Clinical Trials Data Query Summary",
            "=" * 50,
            f"Timestamp: {metadata.get('timestamp', '')}",
            "",
            "Source Data:",
            f"  - Total sheets processed: {summary.get('total_source_sheets', 0)}",
            f"  - Total rows in source: {summary.get('total_source_rows', 0)}",
            f"  - Graph nodes: {metadata.get('total_nodes', 0)}",
            f"  - Graph edges: {metadata.get('total_edges', 0)}",
            "",
            "Clinical Trials Found:",
            f"  - Total studies: {summary.get('total_clinical_trials_found', 0)}",
            f"  - Unique conditions: {summary.get('unique_conditions', 0)}",
            "",
            "Extracted Information:",
            f"  - Diseases: {', '.join(summary.get('extracted_diseases', [])[:5])}",
            f"  - Interventions: {', '.join(summary.get('extracted_interventions', [])[:5])}",
            f"  - Keywords: {', '.join(summary.get('extracted_keywords', [])[:5])}",
            ""
        ]

        return "\n".join(report_lines)

    def organize_results_by_disease(self, diseases: List[str],
                                    trials_by_disease: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Organize clinical trial results by disease with detailed information.

        Args:
            diseases: List of disease names
            trials_by_disease: Dictionary mapping diseases to their trial results

        Returns:
            Organized data structure with detailed trial information per disease
        """
        self.logger.info(f"Organizing results for {len(diseases)} diseases")

        organized_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_diseases': len(diseases),
                'total_trials': sum(len(trials) for trials in trials_by_disease.values())
            },
            'results_by_disease': trials_by_disease,
            'summary_statistics': self._compute_summary_statistics(trials_by_disease)
        }

        return organized_data

    def _compute_summary_statistics(self, trials_by_disease: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Compute summary statistics across all diseases.

        Args:
            trials_by_disease: Dictionary of trials organized by disease

        Returns:
            Dictionary of summary statistics
        """
        all_trials = []
        for trials in trials_by_disease.values():
            all_trials.extend(trials)

        total_trials = len(all_trials)
        completed_trials = sum(1 for t in all_trials if t.get('is_complete', False))
        trials_with_results = sum(1 for t in all_trials if t.get('has_results', False))

        durations = [
            t.get('duration', {}).get('months', 0)
            for t in all_trials
            if t.get('duration', {}).get('months') is not None
        ]

        avg_duration = sum(durations) / len(durations) if durations else 0

        status_distribution = {}
        for trial in all_trials:
            status = trial.get('overall_status', 'Unknown')
            status_distribution[status] = status_distribution.get(status, 0) + 1

        phase_distribution = {}
        for trial in all_trials:
            phases = trial.get('phases', [])
            for phase in phases:
                phase_distribution[phase] = phase_distribution.get(phase, 0) + 1

        statistics = {
            'total_trials': total_trials,
            'completed_trials': completed_trials,
            'ongoing_trials': total_trials - completed_trials,
            'trials_with_results': trials_with_results,
            'completion_rate': 100 * completed_trials / total_trials if total_trials > 0 else 0,
            'results_rate': 100 * trials_with_results / total_trials if total_trials > 0 else 0,
            'average_duration_months': avg_duration,
            'status_distribution': status_distribution,
            'phase_distribution': phase_distribution,
            'diseases_studied': len(trials_by_disease)
        }

        return statistics
