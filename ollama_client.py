"""
Module for interacting with local Ollama models.
"""

import logging
import json
from typing import Dict, Any, List
import requests


class OllamaClient:
    """
    Client for interacting with local Ollama LLM models.
    """

    def __init__(self, model: str, base_url: str = "http://localhost:11434", timeout: int = 12000):
        """
        Initialize Ollama client.

        Args:
            model: Name of the Ollama model to use
            base_url: Base URL for Ollama API
            timeout: Request timeout in seconds
        """
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """
        Generate text using the Ollama model.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt for context

        Returns:
            Generated text response
        """
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        if system_prompt:
            payload["system"] = system_prompt

        self.logger.info(f"Sending prompt to Ollama model: {self.model}")
        self.logger.info("=" * 80)
        self.logger.info("SYSTEM PROMPT:")
        self.logger.info(system_prompt if system_prompt else "(none)")
        self.logger.info("-" * 80)
        self.logger.info("USER PROMPT:")
        self.logger.info(prompt)
        self.logger.info("=" * 80)

        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()

        result = response.json()
        generated_text = result.get('response', '')

        self.logger.info(f"Received response from Ollama ({len(generated_text)} characters)")
        self.logger.info("=" * 80)
        self.logger.info("OLLAMA RESPONSE:")
        self.logger.info(generated_text)
        self.logger.info("=" * 80)

        return generated_text

    def interpret_spreadsheet_data(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Ollama to interpret spreadsheet data and extract meaningful entities.

        Args:
            structured_data: Structured data from ODS file

        Returns:
            Interpreted data with extracted entities and relationships
        """
        self.logger.info("Interpreting spreadsheet data using Ollama")

        data_summary = self._create_data_summary(structured_data)

        system_prompt = """You are a data analyst specializing in clinical trials research.
Analyze the provided spreadsheet data and identify key entities such as diseases, treatments,
interventions, conditions, and any other relevant clinical trial parameters.
Respond with a JSON object containing extracted entities."""

        prompt = f"""Analyze this spreadsheet data and extract key clinical trial search parameters:

{data_summary}

Provide a JSON response with the following structure:
{{
  "diseases": ["list of diseases/conditions"],
  "interventions": ["list of interventions/treatments"],
  "keywords": ["list of other relevant keywords"],
  "parameters": {{"key": "value pairs of other parameters"}}
}}"""

        response_text = self.generate(prompt, system_prompt)

        interpretation = self._parse_json_response(response_text)
        return interpretation

    def structure_api_results(self, api_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use Ollama to structure and interpret clinical trials API results.

        Args:
            api_results: Raw results from ClinicalTrials.gov API

        Returns:
            Structured and interpreted results
        """
        self.logger.info(f"Structuring {len(api_results)} API results using Ollama")

        results_summary = json.dumps(api_results[:5], indent=2)

        system_prompt = """You are a clinical trials data analyst. Analyze the provided
clinical trial data and create a structured summary highlighting key findings,
relevant trials, and important patterns."""

        prompt = f"""Analyze these clinical trial results and provide a structured summary:

{results_summary}

Provide a JSON response with:
{{
  "total_trials": number,
  "key_findings": ["list of important observations"],
  "relevant_trials": ["list of most relevant trial IDs"],
  "summary": "brief summary of the results"
}}"""

        response_text = self.generate(prompt, system_prompt)

        structured_results = self._parse_json_response(response_text)
        return structured_results

    def generate_query_parameters(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate ClinicalTrials.gov query parameters from graph data.

        Args:
            graph_data: Relationship graph data

        Returns:
            Dictionary of query parameters for the API
        """
        self.logger.info("Generating query parameters from graph data using Ollama")

        graph_summary = json.dumps(graph_data, indent=2)[:2000]

        system_prompt = """You are a clinical trials search expert. Based on the provided
data graph, generate appropriate search parameters for the ClinicalTrials.gov API."""

        prompt = f"""Based on this relationship graph data, generate search parameters:

{graph_summary}

Provide a JSON response with:
{{
  "query": "search query string",
  "filter": {{"field": "value"}},
  "fields": ["list of fields to retrieve"]
}}"""

        response_text = self.generate(prompt, system_prompt)

        query_params = self._parse_json_response(response_text)
        return query_params

    def extract_diseases_from_data(self, structured_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract disease terms and disease classes from structured data.

        Args:
            structured_data: Structured data from ODS file

        Returns:
            Dictionary with 'diseases' and 'disease_classes' lists
        """
        diseases = []
        disease_classes = []

        for sheet_name, sheet_data in structured_data.items():
            rows = sheet_data.get('rows', [])

            for row in rows:
                for key, value in row.items():
                    if not value or not isinstance(value, str):
                        continue

                    key_lower = key.lower()

                    if 'disease' in key_lower and 'class' not in key_lower:
                        diseases.append(value.strip())
                    elif 'disease' in key_lower and 'class' in key_lower:
                        disease_classes.append(value.strip())
                    elif 'condition' in key_lower:
                        diseases.append(value.strip())
                    elif 'indication' in key_lower:
                        diseases.append(value.strip())

        diseases = list(set(filter(None, diseases)))
        disease_classes = list(set(filter(None, disease_classes)))

        self.logger.info(f"Extracted {len(diseases)} unique diseases and {len(disease_classes)} disease classes")

        return {
            'diseases': diseases,
            'disease_classes': disease_classes
        }

    def match_ontology_terms(self, diseases: List[str], disease_classes: List[str]) -> Dict[str, Any]:
        """
        Map disease terms and disease classes to standard ontology terms.

        Args:
            diseases: List of disease terms from ODS file
            disease_classes: List of disease class terms from ODS file

        Returns:
            Dictionary mapping original terms to ontology matches
        """
        self.logger.info(f"Matching {len(diseases)} diseases and {len(disease_classes)} disease classes to ontologies")

        all_terms = list(set(diseases + disease_classes))

        if not all_terms:
            return {}

        terms_list = "\n".join([f"- {term}" for term in all_terms[:50]])

        system_prompt = """You are a biomedical ontology expert specializing in disease classification.
Map the provided disease terms to standard ontology identifiers from sources such as:
- MONDO (Monarch Disease Ontology)
- DOID (Disease Ontology)
- ICD (International Classification of Diseases)
- SNOMED CT
- MeSH (Medical Subject Headings)

For each term, provide the most appropriate ontology mappings."""

        prompt = f"""Map these disease terms to standard ontology identifiers:

{terms_list}

Provide a JSON response with the following structure:
{{
  "ontology_mappings": [
    {{
      "original_term": "the original disease term",
      "normalized_term": "normalized/standardized form",
      "ontology_matches": [
        {{
          "ontology": "MONDO/DOID/ICD/SNOMED/MeSH",
          "id": "ontology identifier",
          "label": "official ontology label",
          "confidence": "high/medium/low"
        }}
      ],
      "synonyms": ["list of known synonyms"],
      "parent_classes": ["broader disease categories"]
    }}
  ]
}}

Include all available ontology matches for each term."""

        response_text = self.generate(prompt, system_prompt)
        ontology_mappings = self._parse_json_response(response_text)

        return ontology_mappings

    def deduplicate_diseases(self, diseases: List[str]) -> tuple[List[str], List[Dict[str, Any]]]:
        """
        Deduplicate and optimize disease names for ClinicalTrials.gov searching.

        Args:
            diseases: List of disease names from ODS file

        Returns:
            Tuple of (optimized_search_terms, mapping_list)
            where mapping_list contains dicts with 'original' and 'optimized' keys
        """
        self.logger.info(f"Deduplicating and optimizing {len(diseases)} diseases using Ollama")

        if not diseases:
            return [], []

        # Basic deduplication first: remove exact duplicates and empty strings
        unique_diseases = []
        seen = set()
        for disease in diseases:
            disease_clean = disease.strip()
            if disease_clean and disease_clean.upper() not in seen:
                unique_diseases.append(disease_clean)
                seen.add(disease_clean.upper())

        self.logger.info(f"Basic deduplication: {len(diseases)} -> {len(unique_diseases)} unique diseases")

        diseases_text = "\n".join(unique_diseases)

        system_prompt = """You are a ClinicalTrials.gov expert tasked with making a markdown-format dictionary. Correct, expand, and optimise the following disease list for use as search terms on ClinicalTrials.gov."""

        prompt = f"""Rules:
- Correct spelling errors and ensure US English.
- Replace abbreviations and shorthand (e.g., "ACS", "NDD") with full clinical terms.
- Expand vague or umbrella terms to include specific, relevant diseases or comorbidities.
- Include comorbidities commonly studied in relation to the disease if relevant (e.g., disrupted sleep, anxiety, cognitive impairment).
- Remove duplicates and synonyms while keeping medically precise, search-friendly terms.
- Return a table with each of the original values from the "input disease list" together with the new term suitable for use with ClinicalTrials.gov
- No explanations, no JSON formatting, just a simple tab-separated list of each old term and the corresponding new terms
- Return quickly.

Input disease list:
{diseases_text}"""

        response_text = self.generate(prompt, system_prompt)

        # Parse tab-separated output
        mapping = []
        search_terms_set = set()

        for line in response_text.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('-') or line.startswith('|'):
                continue

            # Split by tab
            parts = line.split('\t')
            if len(parts) >= 2:
                original = parts[0].strip()
                optimized = parts[1].strip()

                if original and optimized:
                    mapping.append({
                        'original': original,
                        'optimized': optimized
                    })
                    search_terms_set.add(optimized)

        # Deduplicate search terms while preserving order
        search_terms = []
        seen_terms = set()
        for item in mapping:
            term = item['optimized']
            if term not in seen_terms:
                search_terms.append(term)
                seen_terms.add(term)

        self.logger.info(f"Ollama optimization: {len(unique_diseases)} -> {len(search_terms)} optimized search terms")
        self.logger.info(f"Created {len(mapping)} term mappings")

        if search_terms:
            self.logger.info(f"Sample optimized terms (first 10):")
            for term in search_terms[:10]:
                self.logger.info(f"  - {term}")

        # If parsing failed, fall back to original list
        if not mapping:
            self.logger.warning("Failed to parse Ollama tab-separated output, using original terms")
            mapping = []
            for original in unique_diseases:
                mapping.append({
                    'original': original,
                    'optimized': original
                })
            search_terms = unique_diseases

        return search_terms, mapping

    def _create_data_summary(self, structured_data: Dict[str, Any], max_rows_per_sheet: int = 3) -> str:
        """
        Create a text summary of structured data for the LLM.

        Args:
            structured_data: Structured spreadsheet data
            max_rows_per_sheet: Maximum number of sample rows to include per sheet

        Returns:
            Text summary limited to avoid overwhelming the model
        """
        summary_parts = []

        for sheet_name, sheet_data in structured_data.items():
            headers = sheet_data.get('headers', [])
            rows = sheet_data.get('rows', [])

            summary_parts.append(f"Sheet: {sheet_name}")
            summary_parts.append(f"Headers: {', '.join(headers)}")
            summary_parts.append(f"Total rows: {len(rows)}")

            if rows:
                sample_count = min(max_rows_per_sheet, len(rows))
                summary_parts.append(f"Sample rows (showing {sample_count} of {len(rows)}):")

                for i, row in enumerate(rows[:sample_count]):
                    summary_parts.append(f"  Row {i+1}: {json.dumps(row, indent=2)}")

            summary_parts.append("")

        return "\n".join(summary_parts)

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response text.

        Args:
            response_text: Raw response text from LLM

        Returns:
            Parsed JSON object
        """
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start != -1 and json_end > json_start:
            json_text = response_text[json_start:json_end]
            parsed = json.loads(json_text)
            return parsed

        self.logger.warning("Could not parse JSON from response, returning default")
        return {}
