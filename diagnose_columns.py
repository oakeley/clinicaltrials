"""
Diagnostic tool to identify which column contains disease data.
"""

import argparse
import sys
from pathlib import Path
from ods_reader import ODSReader


def diagnose_columns(ods_file: str, sheet_index: int = 0, num_samples: int = 20):
    """
    Show all columns and sample data to identify disease column.

    Args:
        ods_file: Path to ODS file
        sheet_index: Index of sheet to analyze
        num_samples: Number of sample rows to show
    """
    reader = ODSReader(ods_file)
    structured_data = reader.get_structured_data()

    if not structured_data:
        print("ERROR: No data found in ODS file")
        return

    sheet_names = list(structured_data.keys())

    if sheet_index >= len(sheet_names):
        print(f"ERROR: Sheet index {sheet_index} out of range. File has {len(sheet_names)} sheets.")
        return

    sheet_name = sheet_names[sheet_index]
    sheet_data = structured_data[sheet_name]

    print(f"\n{'=' * 80}")
    print(f"COLUMN DIAGNOSIS FOR: {ods_file}")
    print(f"Sheet: {sheet_name} (index {sheet_index})")
    print(f"{'=' * 80}\n")

    headers = sheet_data.get('headers', [])
    rows = sheet_data.get('rows', [])

    print(f"Total headers: {len(headers)}")
    print(f"Total rows: {len(rows)}\n")

    print("HEADERS WITH COLUMN LETTERS:")
    print("-" * 80)
    for i, header in enumerate(headers):
        col_letter = chr(ord('A') + i) if i < 26 else f"Column_{i}"
        header_display = f"'{header}'" if header else "(empty)"
        print(f"  {col_letter:3s} (index {i:2d}): {header_display}")

    print(f"\n{'=' * 80}")
    print(f"SAMPLE DATA FROM FIRST {num_samples} ROWS:")
    print(f"{'=' * 80}\n")

    for row_idx, row in enumerate(rows[:num_samples], 1):
        print(f"Row {row_idx}:")
        for header_name, value in row.items():
            if value and str(value).strip():
                col_index = headers.index(header_name) if header_name in headers else -1
                col_letter = chr(ord('A') + col_index) if 0 <= col_index < 26 else "?"
                header_display = f"'{header_name}'" if header_name else "(empty)"
                print(f"  [{col_letter}] {header_display:30s}: {str(value)[:70]}")
        print()

    print(f"{'=' * 80}")
    print("SEARCHING FOR DISEASE PATTERNS:")
    print(f"{'=' * 80}\n")

    disease_keywords = [
        'SYNDROME', 'STROKE', 'MYOCARDIAL', 'INFARCTION', 'ANGINA',
        'ATHEROSCLEROSIS', 'FIBRILLATION', 'TRANSPLANT', 'CANCER',
        'DISEASE', 'DISORDER', 'ISCHEMIC', 'CORONARY'
    ]

    disease_columns = {}

    for row in rows[:100]:
        for header_name, value in row.items():
            if not value or not isinstance(value, str):
                continue

            value_upper = value.upper()
            for keyword in disease_keywords:
                if keyword in value_upper:
                    if header_name not in disease_columns:
                        disease_columns[header_name] = []
                    if value not in disease_columns[header_name]:
                        disease_columns[header_name].append(value)
                    break

    if disease_columns:
        print("Found potential disease columns:")
        for header_name, samples in disease_columns.items():
            col_index = headers.index(header_name) if header_name in headers else -1
            col_letter = chr(ord('A') + col_index) if 0 <= col_index < 26 else "?"
            header_display = f"'{header_name}'" if header_name else "(empty header)"
            print(f"\n  Column [{col_letter}] {header_display}:")
            print(f"    Found {len(samples)} unique disease-like entries")
            print(f"    Samples:")
            for sample in samples[:10]:
                print(f"      - {sample}")
    else:
        print("No columns with disease keywords found in first 100 rows.")

    print(f"\n{'=' * 80}")


def main():
    parser = argparse.ArgumentParser(
        description='Diagnose ODS file structure to identify disease column'
    )
    parser.add_argument(
        'ods_file',
        type=str,
        help='Path to the ODS file'
    )
    parser.add_argument(
        '--sheet',
        type=int,
        default=0,
        help='Sheet index to analyze (default: 0 = first sheet)'
    )
    parser.add_argument(
        '--samples',
        type=int,
        default=20,
        help='Number of sample rows to display (default: 20)'
    )

    args = parser.parse_args()

    if not Path(args.ods_file).exists():
        print(f"ERROR: File not found: {args.ods_file}")
        sys.exit(1)

    diagnose_columns(args.ods_file, args.sheet, args.samples)


if __name__ == '__main__':
    main()
