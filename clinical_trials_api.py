"""
Module for querying ClinicalTrials.gov API v2.
"""

import logging
import time
from typing import Dict, Any, List, Optional
import requests


class ClinicalTrialsAPI:
    """
    Client for querying the ClinicalTrials.gov API v2.
    """

    def __init__(self, base_url: str = "https://clinicaltrials.gov/api/v2",
                 max_studies: int = 100, rate_limit_delay: float = 1.0):
        """
        Initialize ClinicalTrials.gov API client.

        Args:
            base_url: Base URL for the API
            max_studies: Maximum number of studies to retrieve per query
            rate_limit_delay: Delay between API calls in seconds
        """
        self.base_url = base_url
        self.max_studies = max_studies
        self.rate_limit_delay = rate_limit_delay
        self.logger = logging.getLogger(__name__)

    def search_studies(self, query: str, filters: Optional[Dict[str, Any]] = None,
                      fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Search for clinical trials studies.

        Args:
            query: Search query string
            filters: Dictionary of filter parameters
            fields: List of fields to retrieve

        Returns:
            API response containing studies
        """
        endpoint = f"{self.base_url}/studies"

        params = {
            "query.term": query,
            "pageSize": self.max_studies
        }

        if filters:
            for key, value in filters.items():
                params[f"filter.{key}"] = value

        if fields:
            params["fields"] = ",".join(fields)

        self.logger.info(f"Searching ClinicalTrials.gov with query: {query}")
        self.logger.debug(f"Parameters: {params}")

        response = requests.get(endpoint, params=params)
        response.raise_for_status()

        data = response.json()

        studies_count = len(data.get('studies', []))
        self.logger.info(f"Retrieved {studies_count} studies from API")

        time.sleep(self.rate_limit_delay)

        return data

    def get_study_details(self, nct_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific study.

        Args:
            nct_id: NCT identifier for the study

        Returns:
            Detailed study data
        """
        endpoint = f"{self.base_url}/studies/{nct_id}"

        self.logger.info(f"Fetching details for study: {nct_id}")

        response = requests.get(endpoint)
        response.raise_for_status()

        data = response.json()

        time.sleep(self.rate_limit_delay)

        return data

    def search_multiple_terms(self, search_terms: List[str],
                             filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for studies using multiple search terms.

        Args:
            search_terms: List of search terms
            filters: Optional filters to apply to all searches

        Returns:
            List of all retrieved studies
        """
        all_studies = []
        seen_nct_ids = set()

        self.logger.info(f"Searching with {len(search_terms)} terms")

        for term in search_terms:
            if not term:
                continue

            self.logger.info(f"Searching for term: {term}")

            result = self.search_studies(term, filters)
            studies = result.get('studies', [])

            for study in studies:
                protocol_section = study.get('protocolSection', {})
                identification_module = protocol_section.get('identificationModule', {})
                nct_id = identification_module.get('nctId', '')

                if nct_id and nct_id not in seen_nct_ids:
                    all_studies.append(study)
                    seen_nct_ids.add(nct_id)

        self.logger.info(f"Retrieved {len(all_studies)} unique studies from {len(search_terms)} searches")
        return all_studies

    def extract_study_summary(self, study: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract key information from a study record.

        Args:
            study: Full study record

        Returns:
            Dictionary with key study information
        """
        protocol_section = study.get('protocolSection', {})

        identification_module = protocol_section.get('identificationModule', {})
        nct_id = identification_module.get('nctId', '')
        brief_title = identification_module.get('briefTitle', '')
        official_title = identification_module.get('officialTitle', '')

        status_module = protocol_section.get('statusModule', {})
        overall_status = status_module.get('overallStatus', '')

        conditions_module = protocol_section.get('conditionsModule', {})
        conditions = conditions_module.get('conditions', [])

        interventions_module = protocol_section.get('armsInterventionsModule', {})
        interventions = interventions_module.get('interventions', [])

        description_module = protocol_section.get('descriptionModule', {})
        brief_summary = description_module.get('briefSummary', '')

        summary = {
            'nct_id': nct_id,
            'brief_title': brief_title,
            'official_title': official_title,
            'overall_status': overall_status,
            'conditions': conditions,
            'interventions': [i.get('name', '') for i in interventions],
            'brief_summary': brief_summary
        }

        return summary

    def query_from_graph(self, graph_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate and execute queries based on relationship graph data.

        Args:
            graph_data: Relationship graph data

        Returns:
            List of studies matching the graph data
        """
        search_terms = set()

        nodes = graph_data.get('nodes', {})

        for node_id, node_data in nodes.items():
            attributes = node_data.get('attributes', {})
            for value in attributes.values():
                if value and isinstance(value, str) and len(value) > 2:
                    search_terms.add(value.strip())

        search_terms = list(search_terms)[:20]

        self.logger.info(f"Generated {len(search_terms)} search terms from graph")

        results = self.search_multiple_terms(search_terms)

        return results

    def query_by_disease(self, disease: str, max_studies: int = None,
                        apply_filters: bool = True, years_back: int = 10) -> Dict[str, Any]:
        """
        Query clinical trials for a specific disease with detailed information.
        Returns most recent trials first (sorted by LastUpdatePostDate descending).
        Uses pagination to retrieve up to max_studies results.

        Args:
            disease: Disease name or condition
            max_studies: Maximum number of studies to retrieve
            apply_filters: Whether to apply interventional/industry/date filters
            years_back: How many years back to search for completion date

        Returns:
            Dictionary containing studies list and raw API response
        """
        if max_studies is None:
            max_studies = self.max_studies

        filter_desc = ""
        if apply_filters:
            filter_desc = f" (interventional, pharma industry, last {years_back} years)"

        self.logger.info(f"Querying clinical trials for disease: {disease} (max: {max_studies}, sorted by most recent{filter_desc})")

        endpoint = f"{self.base_url}/studies"

        query_parts = [f'"{disease}"']
        if apply_filters:
            query_parts.append("AND AREA[StudyType]Interventional")
            query_parts.append("AND AREA[LeadSponsorClass]Industry")

        query_term = " ".join(query_parts)

        # API limit is 1000 per page
        page_size = min(1000, max_studies)

        base_params = {
            "query.term": query_term,
            "pageSize": page_size,
            "sort": "LastUpdatePostDate:desc",
            "format": "json"
        }

        if apply_filters:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=years_back * 365)
            cutoff_str = cutoff_date.strftime("%Y-%m-%d")

            self.logger.info(f"Query: {query_term}")
            self.logger.info(f"Post-retrieval filter: completion date >= {cutoff_str}")

        # Pagination loop to retrieve up to max_studies
        all_studies = []
        page_token = None
        page_count = 0

        while len(all_studies) < max_studies:
            page_count += 1
            params = base_params.copy()
            if page_token:
                params['pageToken'] = page_token

            try:
                response = requests.get(endpoint, params=params, timeout=30)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                self.logger.error(f"API request failed for disease '{disease}' on page {page_count}: {e}")
                if page_count == 1:
                    return {
                        'disease': disease,
                        'studies': [],
                        'raw_api_response': {},
                        'query_params': base_params,
                        'total_count': 0,
                        'error': str(e)
                    }
                else:
                    break

            raw_data = response.json()
            studies = raw_data.get('studies', [])

            if not studies:
                break

            all_studies.extend(studies)
            self.logger.info(f"  Page {page_count}: fetched {len(studies)} studies (total: {len(all_studies)})")

            page_token = raw_data.get('nextPageToken')
            if not page_token:
                break

            time.sleep(self.rate_limit_delay)

        # Truncate to max_studies if we got more
        if len(all_studies) > max_studies:
            all_studies = all_studies[:max_studies]
            self.logger.info(f"Truncated to {max_studies} studies")

        if apply_filters and years_back:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=years_back * 365)
            original_count = len(all_studies)

            filtered_studies = []
            for study in all_studies:
                protocol_section = study.get('protocolSection', {})
                status_module = protocol_section.get('statusModule', {})
                completion_date_struct = status_module.get('completionDateStruct', {})
                completion_date_str = completion_date_struct.get('date', '')

                if completion_date_str:
                    try:
                        completion_date = self._parse_date(completion_date_str)
                        if completion_date < cutoff_date:
                            continue
                    except ValueError:
                        pass

                filtered_studies.append(study)

            all_studies = filtered_studies
            self.logger.info(f"Client-side date filtering (>={years_back}y): {original_count} -> {len(all_studies)} studies")

        self.logger.info(f"Retrieved {len(all_studies)} studies for disease: {disease} (sorted by most recent{filter_desc})")

        return {
            'disease': disease,
            'studies': all_studies,
            'raw_api_response': raw_data,
            'query_params': base_params,
            'total_count': len(all_studies)
        }

    def extract_detailed_study_info(self, study: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract comprehensive information from a study record including dates, objectives, and results.

        Args:
            study: Full study record

        Returns:
            Dictionary with detailed study information
        """
        protocol_section = study.get('protocolSection', {})
        results_section = study.get('resultsSection', {})
        derived_section = study.get('derivedSection', {})

        identification_module = protocol_section.get('identificationModule', {})
        nct_id = identification_module.get('nctId', '')
        brief_title = identification_module.get('briefTitle', '')
        official_title = identification_module.get('officialTitle', '')

        status_module = protocol_section.get('statusModule', {})
        overall_status = status_module.get('overallStatus', '')
        start_date = status_module.get('startDateStruct', {})
        completion_date = status_module.get('completionDateStruct', {})
        primary_completion_date = status_module.get('primaryCompletionDateStruct', {})

        conditions_module = protocol_section.get('conditionsModule', {})
        conditions = conditions_module.get('conditions', [])

        design_module = protocol_section.get('designModule', {})
        phases = design_module.get('phases', [])
        study_type = design_module.get('studyType', '')
        enrollment_info = design_module.get('enrollmentInfo', {})

        outcomes_module = protocol_section.get('outcomesModule', {})
        primary_outcomes = outcomes_module.get('primaryOutcomes', [])
        secondary_outcomes = outcomes_module.get('secondaryOutcomes', [])

        description_module = protocol_section.get('descriptionModule', {})
        brief_summary = description_module.get('briefSummary', '')
        detailed_description = description_module.get('detailedDescription', '')

        sponsor_module = protocol_section.get('sponsorCollaboratorsModule', {})
        lead_sponsor = sponsor_module.get('leadSponsor', {})
        lead_sponsor_name = lead_sponsor.get('name', '')
        lead_sponsor_class = lead_sponsor.get('class', '')

        has_results = bool(results_section and len(results_section) > 0)

        start_date_str = start_date.get('date', '') if start_date else ''
        completion_date_str = completion_date.get('date', '') if completion_date else ''
        primary_completion_date_str = primary_completion_date.get('date', '') if primary_completion_date else ''

        is_complete = overall_status in ['COMPLETED', 'TERMINATED', 'WITHDRAWN', 'SUSPENDED']

        duration_info = self._calculate_duration(start_date_str, completion_date_str, is_complete)

        detailed_info = {
            'nct_id': nct_id,
            'brief_title': brief_title,
            'official_title': official_title,
            'overall_status': overall_status,
            'is_complete': is_complete,
            'has_results': has_results,
            'conditions': conditions,
            'phases': phases,
            'study_type': study_type,
            'dates': {
                'start_date': start_date_str,
                'start_date_type': start_date.get('type', '') if start_date else '',
                'primary_completion_date': primary_completion_date_str,
                'primary_completion_date_type': primary_completion_date.get('type', '') if primary_completion_date else '',
                'completion_date': completion_date_str,
                'completion_date_type': completion_date.get('type', '') if completion_date else ''
            },
            'duration': duration_info,
            'enrollment': {
                'count': enrollment_info.get('count', 0),
                'type': enrollment_info.get('type', '')
            },
            'primary_outcomes': [
                {
                    'measure': outcome.get('measure', ''),
                    'description': outcome.get('description', ''),
                    'timeFrame': outcome.get('timeFrame', '')
                }
                for outcome in primary_outcomes
            ],
            'secondary_outcomes': [
                {
                    'measure': outcome.get('measure', ''),
                    'description': outcome.get('description', ''),
                    'timeFrame': outcome.get('timeFrame', '')
                }
                for outcome in secondary_outcomes
            ],
            'descriptions': {
                'brief_summary': brief_summary,
                'detailed_description': detailed_description
            },
            'sponsor': {
                'name': lead_sponsor_name,
                'class': lead_sponsor_class
            },
            'url': f"https://clinicaltrials.gov/study/{nct_id}"
        }

        if has_results:
            detailed_info['results'] = self._extract_results(results_section)

        return detailed_info

    def _calculate_duration(self, start_date: str, completion_date: str, is_complete: bool) -> Dict[str, Any]:
        """
        Calculate trial duration in months and days.

        Args:
            start_date: Start date string (YYYY-MM-DD or YYYY-MM)
            completion_date: Completion date string
            is_complete: Whether the trial is complete

        Returns:
            Dictionary with duration information
        """
        from datetime import datetime

        duration_info = {
            'months': None,
            'days': None,
            'years': None,
            'status': 'unknown'
        }

        if not start_date:
            return duration_info

        try:
            start_dt = self._parse_date(start_date)

            if completion_date:
                end_dt = self._parse_date(completion_date)
                duration_info['status'] = 'actual' if is_complete else 'expected'

                delta = end_dt - start_dt
                duration_info['days'] = delta.days
                duration_info['months'] = round(delta.days / 30.44)
                duration_info['years'] = round(delta.days / 365.25, 1)
            else:
                if is_complete:
                    duration_info['status'] = 'completed_no_date'
                else:
                    end_dt = datetime.now()
                    duration_info['status'] = 'ongoing'

                    delta = end_dt - start_dt
                    duration_info['days'] = delta.days
                    duration_info['months'] = round(delta.days / 30.44)
                    duration_info['years'] = round(delta.days / 365.25, 1)

        except ValueError:
            self.logger.warning(f"Could not parse dates: {start_date}, {completion_date}")

        return duration_info

    def _parse_date(self, date_str: str) -> 'datetime':
        """
        Parse date string in various formats.

        Args:
            date_str: Date string

        Returns:
            datetime object
        """
        from datetime import datetime

        for fmt in ['%Y-%m-%d', '%Y-%m', '%Y']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        raise ValueError(f"Could not parse date: {date_str}")

    def _extract_results(self, results_section: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract results information from results section.

        Args:
            results_section: Results section from API response

        Returns:
            Dictionary with results information
        """
        outcome_measures_module = results_section.get('outcomeMeasuresModule', {})
        adverse_events_module = results_section.get('adverseEventsModule', {})

        outcome_measures = outcome_measures_module.get('outcomeMeasures', [])

        results = {
            'has_outcome_data': len(outcome_measures) > 0,
            'outcome_measures': [
                {
                    'title': om.get('title', ''),
                    'description': om.get('description', ''),
                    'timeFrame': om.get('timeFrame', '')
                }
                for om in outcome_measures[:5]
            ],
            'has_adverse_events': bool(adverse_events_module),
            'results_summary': f"{len(outcome_measures)} outcome measures reported"
        }

        return results
