"""
Module for reading and parsing ODS spreadsheet files.
"""

import logging
from typing import Dict, List, Any
from odf import opendocument, table, text


class ODSReader:
    """
    Reads ODS files and extracts data from all sheets.
    """

    def __init__(self, file_path: str):
        """
        Initialize the ODS reader with a file path.

        Args:
            file_path: Path to the ODS file
        """
        self.file_path = file_path
        self.logger = logging.getLogger(__name__)

    def read_file(self) -> Dict[str, List[List[str]]]:
        """
        Read all sheets from the ODS file.

        Returns:
            Dictionary mapping sheet names to their data as 2D lists
        """
        self.logger.info(f"Reading ODS file: {self.file_path}")

        doc = opendocument.load(self.file_path)
        sheets_data = {}

        sheets = doc.spreadsheet.getElementsByType(table.Table)

        for sheet in sheets:
            sheet_name = sheet.getAttribute('name')
            self.logger.info(f"Processing sheet: {sheet_name}")

            sheet_data = self._extract_sheet_data(sheet)
            sheets_data[sheet_name] = sheet_data

            self.logger.info(f"Extracted {len(sheet_data)} rows from sheet: {sheet_name}")

        return sheets_data

    def _extract_sheet_data(self, sheet: table.Table) -> List[List[str]]:
        """
        Extract data from a single sheet.

        Args:
            sheet: ODF table object

        Returns:
            2D list of cell values
        """
        rows_data = []

        rows = sheet.getElementsByType(table.TableRow)

        for row in rows:
            row_data = []
            cells = row.getElementsByType(table.TableCell)

            for cell in cells:
                cell_value = self._get_cell_value(cell)

                repeat = cell.getAttribute('numbercolumnsrepeated')
                if repeat:
                    repeat_count = int(repeat)
                    row_data.extend([cell_value] * repeat_count)
                else:
                    row_data.append(cell_value)

            if any(cell for cell in row_data):
                rows_data.append(row_data)

        return rows_data

    def _get_cell_value(self, cell: table.TableCell) -> str:
        """
        Extract text value from a cell.

        Args:
            cell: ODF table cell object

        Returns:
            Cell value as string
        """
        text_elements = cell.getElementsByType(text.P)

        if not text_elements:
            return ""

        cell_text = []
        for element in text_elements:
            if element.firstChild:
                cell_text.append(str(element.firstChild))

        return " ".join(cell_text)

    def get_structured_data(self) -> Dict[str, Any]:
        """
        Read ODS file and return structured data with headers.

        Returns:
            Dictionary with sheet names as keys and structured data as values
        """
        sheets_raw = self.read_file()
        structured_data = {}

        for sheet_name, rows in sheets_raw.items():
            if not rows:
                continue

            headers = rows[0]
            data_rows = rows[1:]

            structured_rows = []
            for row in data_rows:
                row_dict = {}
                for i, header in enumerate(headers):
                    if i < len(row):
                        row_dict[header] = row[i]
                    else:
                        row_dict[header] = ""
                structured_rows.append(row_dict)

            structured_data[sheet_name] = {
                'headers': headers,
                'rows': structured_rows,
                'raw_rows': rows
            }

        return structured_data
