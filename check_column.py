#!/usr/bin/env python3
"""Quick script to check column O in the ODS file."""

from ods_reader import ODSReader

reader = ODSReader('Copie_de_Benchmarks_Couts.ods')
data = reader.get_structured_data()

sheet1_name = list(data.keys())[0]
sheet1 = data[sheet1_name]
headers = sheet1['headers']

print(f"Sheet 1: {sheet1_name}")
print(f"Total columns: {len(headers)}")
print(f"\nColumn headers (first 20):")
for i, h in enumerate(headers[:20]):
    letter = chr(65 + i) if i < 26 else f"{chr(65 + i//26 - 1)}{chr(65 + i%26)}"
    print(f"  {letter}: {h}")

if len(headers) > 14:
    col_o_header = headers[14]
    print(f"\nColumn O (index 14): {col_o_header}")

    diseases = []
    for row in sheet1['rows']:
        value = row.get(col_o_header, '').strip()
        if value:
            diseases.append(value)

    unique_diseases = sorted(set(diseases))
    print(f"\nUnique values in column O: {len(unique_diseases)}")
    print(f"\nFirst 20 unique diseases:")
    for d in unique_diseases[:20]:
        print(f"  - {d}")

    print(f"\nLast 10 unique diseases:")
    for d in unique_diseases[-10:]:
        print(f"  - {d}")
