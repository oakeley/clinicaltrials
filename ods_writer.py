"""
Module for writing data to ODS spreadsheet files.
"""

import logging
from typing import Dict, List, Any
from odf.opendocument import OpenDocumentSpreadsheet
from odf.style import Style, TextProperties, TableColumnProperties, TableCellProperties
from odf.text import P
from odf.table import Table, TableColumn, TableRow, TableCell
from odf.number import NumberStyle, Number, Text as NumberText


class ODSWriter:
    """
    Writes clinical trials data to ODS spreadsheet format.
    """

    def __init__(self, output_path: str):
        """
        Initialize ODS writer.

        Args:
            output_path: Path to output ODS file
        """
        self.output_path = output_path
        self.logger = logging.getLogger(__name__)
        self.doc = OpenDocumentSpreadsheet()
        self._setup_styles()

    def _setup_styles(self) -> None:
        """
        Set up cell styles for the spreadsheet.
        """
        bold_style = Style(name="BoldHeader", family="table-cell")
        bold_text_props = TextProperties(fontweight="bold")
        bold_style.addElement(bold_text_props)
        self.doc.styles.addElement(bold_style)
        self.bold_style = bold_style

    def write_disease_results(self, results_by_disease: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Write clinical trials results organized by disease to ODS file.

        Args:
            results_by_disease: Dictionary mapping disease names to lists of trial results
        """
        self.logger.info(f"Writing results for {len(results_by_disease)} diseases to ODS")

        self._create_summary_sheet(results_by_disease)

        for disease, trials in results_by_disease.items():
            safe_sheet_name = self._sanitize_sheet_name(disease)
            self._create_disease_sheet(safe_sheet_name, disease, trials)

        self.doc.save(self.output_path)
        self.logger.info(f"ODS file saved to: {self.output_path}")

    def _create_summary_sheet(self, results_by_disease: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Create summary sheet with overview statistics.

        Args:
            results_by_disease: Dictionary of results by disease
        """
        table = Table(name="Summary")

        headers = ["Disease", "Total Trials", "Completed", "Ongoing", "With Results", "Avg Duration (months)"]
        self._add_row(table, headers, is_header=True)

        for disease, trials in results_by_disease.items():
            total_trials = len(trials)
            completed = sum(1 for t in trials if t.get('is_complete', False))
            ongoing = total_trials - completed
            with_results = sum(1 for t in trials if t.get('has_results', False))

            durations = [
                t.get('duration', {}).get('months', 0)
                for t in trials
                if t.get('duration', {}).get('months') is not None
            ]
            avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

            row_data = [
                disease,
                str(total_trials),
                str(completed),
                str(ongoing),
                str(with_results),
                str(avg_duration)
            ]
            self._add_row(table, row_data)

        self.doc.spreadsheet.addElement(table)

    def _create_disease_sheet(self, sheet_name: str, disease: str, trials: List[Dict[str, Any]]) -> None:
        """
        Create a sheet with detailed trial information for a specific disease.

        Args:
            sheet_name: Sanitized sheet name
            disease: Disease name
            trials: List of trial dictionaries
        """
        table = Table(name=sheet_name)

        headers = [
            "NCT ID",
            "Title",
            "Status",
            "Start Date",
            "Completion Date",
            "Duration (months)",
            "Duration Status",
            "Phase",
            "Enrollment",
            "Primary Outcome",
            "Secondary Outcomes",
            "Has Results",
            "Sponsor",
            "URL"
        ]
        self._add_row(table, headers, is_header=True)

        for trial in trials:
            dates = trial.get('dates', {})
            duration = trial.get('duration', {})
            enrollment = trial.get('enrollment', {})
            primary_outcomes = trial.get('primary_outcomes', [])
            secondary_outcomes = trial.get('secondary_outcomes', [])

            primary_outcome_text = primary_outcomes[0].get('measure', '') if primary_outcomes else ''
            secondary_count = len(secondary_outcomes)

            row_data = [
                trial.get('nct_id', ''),
                trial.get('brief_title', ''),
                trial.get('overall_status', ''),
                dates.get('start_date', ''),
                dates.get('completion_date', ''),
                str(duration.get('months', '')),
                duration.get('status', ''),
                ', '.join(trial.get('phases', [])),
                str(enrollment.get('count', '')),
                primary_outcome_text,
                f"{secondary_count} secondary outcomes",
                'Yes' if trial.get('has_results', False) else 'No',
                trial.get('sponsor', ''),
                trial.get('url', '')
            ]
            self._add_row(table, row_data)

        self.doc.spreadsheet.addElement(table)

    def _add_row(self, table: Table, data: List[str], is_header: bool = False) -> None:
        """
        Add a row to a table.

        Args:
            table: Table object
            data: List of cell values
            is_header: Whether this is a header row
        """
        row = TableRow()

        for value in data:
            cell = TableCell()
            if is_header:
                cell.setAttribute('stylename', self.bold_style)

            p = P(text=str(value))
            cell.addElement(p)
            row.addElement(cell)

        table.addElement(row)

    def _sanitize_sheet_name(self, name: str) -> str:
        """
        Sanitize sheet name to conform to ODS requirements.

        Args:
            name: Original name

        Returns:
            Sanitized name limited to 31 characters
        """
        invalid_chars = ['/', '\\', '?', '*', '[', ']', ':']
        sanitized = name
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')

        return sanitized[:31]
