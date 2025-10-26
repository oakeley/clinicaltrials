"""
Module for extracting disease names directly from ODS data.
"""

import logging
from typing import List, Set, Dict, Any
import re


class DiseaseExtractor:
    """
    Extracts disease names from ODS spreadsheet data.
    """

    def __init__(self):
        """
        Initialize disease extractor.
        """
        self.logger = logging.getLogger(__name__)

        self.common_diseases = {
            'breast cancer', 'lung cancer', 'colorectal cancer', 'prostate cancer',
            'pancreatic cancer', 'liver cancer', 'stomach cancer', 'ovarian cancer',
            'melanoma', 'leukemia', 'lymphoma', 'myeloma', 'glioblastoma',
            'non-small cell lung cancer', 'small cell lung cancer', 'nsclc', 'sclc',
            'acute myeloid leukemia', 'aml', 'chronic lymphocytic leukemia', 'cll',
            'multiple myeloma', 'hodgkin lymphoma', 'non-hodgkin lymphoma',
            'renal cell carcinoma', 'bladder cancer', 'cervical cancer',
            'endometrial cancer', 'esophageal cancer', 'gastric cancer',
            'hepatocellular carcinoma', 'head and neck cancer', 'thyroid cancer',
            'sarcoma', 'mesothelioma', 'neuroblastoma', 'glioma',
            'alzheimer', 'parkinson', 'diabetes', 'hypertension',
            'rheumatoid arthritis', 'crohn', 'ulcerative colitis',
            'multiple sclerosis', 'psoriasis', 'asthma', 'copd'
        }

    def extract_from_column_o(self, structured_data: Dict[str, Any]) -> List[str]:
        """
        Extract disease names from column O (index 14) of the first sheet.

        Args:
            structured_data: Structured data from ODS reader

        Returns:
            List of unique disease names from column O
        """
        self.logger.info("Extracting diseases from column O of first sheet")

        sheet_names = list(structured_data.keys())
        if not sheet_names:
            self.logger.error("No sheets found in ODS file")
            return []

        first_sheet_name = sheet_names[0]
        first_sheet = structured_data[first_sheet_name]

        self.logger.info(f"Reading from sheet: {first_sheet_name}")

        headers = first_sheet.get('headers', [])
        rows = first_sheet.get('rows', [])

        if len(headers) <= 14:
            self.logger.error(f"Sheet only has {len(headers)} columns, column O (index 14) not found")
            return []

        column_o_header = headers[14]
        self.logger.info(f"Column O header: '{column_o_header}'")

        diseases = set()
        for row in rows:
            value = row.get(column_o_header, '').strip()
            if value and len(value) > 1:
                diseases.add(value)

        diseases_list = sorted(list(diseases))

        self.logger.info(f"Found {len(diseases_list)} unique diseases in column O")
        self.logger.info(f"Sample diseases: {diseases_list[:10]}")

        return diseases_list

    def extract_from_structured_data(self, structured_data: Dict[str, Any],
                                     max_diseases: int = 20) -> List[str]:
        """
        Extract disease names from structured ODS data.

        Args:
            structured_data: Structured data from ODS reader
            max_diseases: Maximum number of diseases to return

        Returns:
            List of disease names found
        """
        self.logger.info("Extracting diseases from ODS data")

        diseases_found = set()

        for sheet_name, sheet_data in structured_data.items():
            self.logger.info(f"Scanning sheet: {sheet_name}")

            headers = sheet_data.get('headers', [])
            rows = sheet_data.get('rows', [])

            header_diseases = self._extract_from_headers(headers)
            diseases_found.update(header_diseases)

            cell_diseases = self._extract_from_cells(rows)
            diseases_found.update(cell_diseases)

        diseases_list = sorted(list(diseases_found))[:max_diseases]

        self.logger.info(f"Found {len(diseases_list)} diseases: {diseases_list}")

        return diseases_list

    def _extract_from_headers(self, headers: List[str]) -> Set[str]:
        """
        Extract disease names from column headers.

        Args:
            headers: List of column headers

        Returns:
            Set of disease names
        """
        diseases = set()

        for header in headers:
            if not header:
                continue

            header_lower = header.lower().strip()

            for disease in self.common_diseases:
                if disease in header_lower:
                    diseases.add(self._capitalize_disease(disease))

        return diseases

    def _extract_from_cells(self, rows: List[Dict[str, Any]],
                           sample_size: int = 100) -> Set[str]:
        """
        Extract disease names from cell values.

        Args:
            rows: List of row dictionaries
            sample_size: Number of rows to sample

        Returns:
            Set of disease names
        """
        diseases = set()

        rows_to_scan = rows[:sample_size]

        for row in rows_to_scan:
            for key, value in row.items():
                if not value or not isinstance(value, str):
                    continue

                value_lower = value.lower().strip()

                for disease in self.common_diseases:
                    if disease in value_lower:
                        diseases.add(self._capitalize_disease(disease))

                    if len(value_lower) < 100:
                        extracted = self._extract_disease_patterns(value)
                        if extracted:
                            diseases.update(extracted)

        return diseases

    def _extract_disease_patterns(self, text: str) -> Set[str]:
        """
        Extract disease names using pattern matching.

        Args:
            text: Text to search

        Returns:
            Set of disease names
        """
        diseases = set()
        text_lower = text.lower()

        cancer_pattern = r'\b(\w+\s+)?cancer\b'
        matches = re.findall(cancer_pattern, text_lower)
        for match in matches:
            disease_name = (match + 'cancer').strip()
            if disease_name and disease_name != 'cancer':
                diseases.add(self._capitalize_disease(disease_name))

        disease_pattern = r'\b(\w{3,})\s+(disease|syndrome|disorder)\b'
        matches = re.findall(disease_pattern, text_lower)
        for match in matches:
            disease_name = ' '.join(match).strip()
            if disease_name and len(match[0]) > 2:
                diseases.add(self._capitalize_disease(disease_name))

        return diseases

    def _capitalize_disease(self, disease: str) -> str:
        """
        Properly capitalize disease name.

        Args:
            disease: Disease name in lowercase

        Returns:
            Properly capitalized disease name
        """
        disease = disease.strip()

        acronyms = {'nsclc', 'sclc', 'aml', 'cll', 'copd'}
        if disease in acronyms:
            return disease.upper()

        special_cases = {
            'non-small cell lung cancer': 'Non-Small Cell Lung Cancer',
            'small cell lung cancer': 'Small Cell Lung Cancer',
            'non-hodgkin lymphoma': 'Non-Hodgkin Lymphoma',
            'hodgkin lymphoma': 'Hodgkin Lymphoma'
        }

        if disease in special_cases:
            return special_cases[disease]

        return disease.title()

    def get_sample_data_preview(self, structured_data: Dict[str, Any],
                                max_rows: int = 5) -> str:
        """
        Get a preview of the data to help understand structure.

        Args:
            structured_data: Structured ODS data
            max_rows: Maximum rows to preview per sheet

        Returns:
            Preview string
        """
        preview_lines = ["=" * 60, "ODS DATA PREVIEW", "=" * 60]

        for sheet_name, sheet_data in structured_data.items():
            preview_lines.append(f"\nSheet: {sheet_name}")

            headers = sheet_data.get('headers', [])
            rows = sheet_data.get('rows', [])

            preview_lines.append(f"Headers: {headers[:10]}")
            preview_lines.append(f"Total rows: {len(rows)}")

            preview_lines.append(f"\nSample rows:")
            for i, row in enumerate(rows[:max_rows]):
                preview_lines.append(f"  Row {i+1}:")
                for key, value in list(row.items())[:5]:
                    if value:
                        preview_lines.append(f"    {key}: {value}")

        preview_lines.append("=" * 60)

        return "\n".join(preview_lines)
