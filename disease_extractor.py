"""
Module for extracting disease names directly from ODS data.
"""

import logging
from typing import List, Set, Dict, Any, Tuple
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

    def remove_brackets_and_content(self, text: str) -> str:
        """
        Remove bracketed content and extra whitespace from disease name.
        Example: "ACUTE CORONARY SYNDROME (ACS)" -> "ACUTE CORONARY SYNDROME"

        Args:
            text: Disease name with possible bracketed content

        Returns:
            Cleaned disease name
        """
        cleaned = re.sub(r'\s*\([^)]*\)', '', text)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()

    def deduplicate_diseases(self, diseases: List[str]) -> Tuple[List[str], Dict[str, List[str]]]:
        """
        Deduplicate diseases by removing bracketed content, similar to 'sort | uniq'.
        Keeps track of original names that map to each deduplicated name.

        Args:
            diseases: List of disease names (may contain duplicates with different brackets)

        Returns:
            Tuple of (deduplicated list, mapping of cleaned name to original names)
        """
        disease_map = {}

        for disease in diseases:
            cleaned = self.remove_brackets_and_content(disease)

            if cleaned not in disease_map:
                disease_map[cleaned] = []
            disease_map[cleaned].append(disease)

        deduplicated = sorted(disease_map.keys())

        self.logger.info(f"Deduplication: {len(diseases)} -> {len(deduplicated)} unique diseases")

        merged_count = sum(1 for originals in disease_map.values() if len(originals) > 1)
        self.logger.info(f"Merged {merged_count} disease groups with multiple bracket variations")

        for cleaned, originals in list(disease_map.items())[:5]:
            if len(originals) > 1:
                self.logger.info(f"  '{cleaned}' merged from: {originals}")

        return deduplicated, disease_map

    def _column_letter_to_index(self, column_letter: str) -> int:
        """
        Convert column letter to zero-based index.
        A -> 0, B -> 1, C -> 2, etc.

        Args:
            column_letter: Column letter (A, B, C, etc.)

        Returns:
            Zero-based column index
        """
        column_letter = column_letter.upper().strip()
        if len(column_letter) != 1 or not column_letter.isalpha():
            raise ValueError(f"Invalid column letter: {column_letter}")

        return ord(column_letter) - ord('A')

    def extract_from_column(self, structured_data: Dict[str, Any], column_letter: str = 'C',
                           data_start_row: int = 2) -> List[str]:
        """
        Extract disease names from specified column of the first sheet.

        Args:
            structured_data: Structured data from ODS reader (contains 'raw_rows' key)
            column_letter: Column letter (A, B, C, etc.) to extract from
            data_start_row: Row number where data starts (1-based, Excel-style)
                          1 = no headers, all rows are data
                          2 = row 1 is header, row 2+ is data (default)
                          3 = row 2 is header, row 3+ is data
                          etc.

        Returns:
            List of unique disease names from specified column
        """
        column_index = self._column_letter_to_index(column_letter)
        self.logger.info(f"Extracting diseases from column {column_letter} (index {column_index}) of first sheet")
        self.logger.info(f"Data starts at row {data_start_row} (1-based)")

        sheet_names = list(structured_data.keys())
        if not sheet_names:
            self.logger.error("No sheets found in ODS file")
            return []

        first_sheet_name = sheet_names[0]
        first_sheet = structured_data[first_sheet_name]

        self.logger.info(f"Reading from sheet: {first_sheet_name}")

        raw_rows = first_sheet.get('raw_rows', [])
        if not raw_rows:
            self.logger.error("No raw_rows data available. Ensure ODSReader includes raw_rows in structured_data.")
            return []

        if data_start_row < 1:
            self.logger.error(f"Invalid data_start_row: {data_start_row}. Must be >= 1.")
            return []

        if data_start_row > len(raw_rows):
            self.logger.error(f"data_start_row {data_start_row} exceeds total rows {len(raw_rows)}")
            return []

        header_row_index = data_start_row - 2 if data_start_row >= 2 else None
        data_rows_start_index = data_start_row - 1

        if header_row_index is not None and header_row_index >= 0:
            headers = raw_rows[header_row_index]
            if len(headers) <= column_index:
                self.logger.error(f"Sheet only has {len(headers)} columns, column {column_letter} (index {column_index}) not found")
                return []
            column_header = headers[column_index] if column_index < len(headers) else ""
            self.logger.info(f"Column {column_letter} header (from row {header_row_index + 1}): '{column_header}'")
        else:
            column_header = None
            self.logger.info(f"No header row (data_start_row=1), extracting from column {column_letter} only")

        diseases = set()
        data_rows = raw_rows[data_rows_start_index:]

        for row_idx, row in enumerate(data_rows, start=data_start_row):
            if column_index >= len(row):
                continue

            value = row[column_index].strip() if column_index < len(row) else ""
            if value and len(value) > 1:
                diseases.add(value)

        diseases_list = sorted(list(diseases))

        self.logger.info(f"Found {len(diseases_list)} unique diseases in column {column_letter}")
        self.logger.info(f"Sample diseases: {diseases_list[:10]}")

        return diseases_list

    def extract_from_column_o(self, structured_data: Dict[str, Any]) -> List[str]:
        """
        Extract disease names from column O (index 14) of the first sheet.
        Maintained for backward compatibility.

        Args:
            structured_data: Structured data from ODS reader

        Returns:
            List of unique disease names from column O
        """
        return self.extract_from_column(structured_data, 'O')

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
