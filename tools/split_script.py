#!/usr/bin/env python3
import csv
import os
import sys
from pathlib import Path

try:
    import pandas as pd
except Exception:
    pd = None

GAME_DIR = Path('/workspaces/misc_game-chs/[FuriKuru] Teikan no Eve Bethel (諦観のイヴ・ベセル)')
INPUT_CSV = GAME_DIR / 'script.csv'
OUT_DIR = GAME_DIR / 'translatorpp_output'
OUT_DIR.mkdir(parents=True, exist_ok=True)

manifest_rows = []
errors = []

def is_command_or_comment(line: str) -> bool:
    s = line.lstrip()
    return not s or s.startswith(';') or s.startswith('[')

def process_record(index, orig_filename, shortname, content):
    # Normalize line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    lines = content.split('\n')
    out_rows = []
    # Header rows required by Translator++
    out_rows.append(['Original Text','Initial','Machine translation','Better translation','Best translation'])
    out_rows.append(['Key','Value','','',''])

    current_speaker = '#'
    for line in lines:
        if line is None:
            continue
        raw = line.rstrip('\n')
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith('#'):
            # speaker line
            if stripped == '#':
                current_speaker = '#'
            else:
                current_speaker = stripped
            # do not emit immediately, will be emitted with next text line
            continue
        if is_command_or_comment(stripped):
            continue
        # Visible text line: first a speaker row, then the line row
        out_rows.append([current_speaker,'','','',''])
        out_rows.append([raw,'','','',''])
    return out_rows


def main():
    if not INPUT_CSV.exists():
        print('Input script.csv not found at', INPUT_CSV)
        sys.exit(1)
    total = 0
    processed = 0
    # Try multiple encodings commonly used for Japanese text exports
    encodings_to_try = ['utf-8', 'utf-8-sig', 'cp932', 'shift_jis', 'euc_jp', 'utf-16', 'utf-16-le', 'utf-16-be']
    reader = None
    used_encoding = None
    for enc in encodings_to_try:
        try:
            f = open(INPUT_CSV, 'r', encoding=enc, newline='')
            reader = csv.reader(f)
            # attempt to read the first row to ensure encoding works
            first = next(reader, None)
            if first is None:
                # empty file
                f.seek(0)
                reader = csv.reader(f)
            else:
                # reset reader by reopening with same encoding
                f.close()
                f = open(INPUT_CSV, 'r', encoding=enc, newline='')
                reader = csv.reader(f)
            used_encoding = enc
            break
        except Exception:
            # try next encoding
            try:
                f.close()
            except Exception:
                pass
            reader = None
            used_encoding = None
            continue
    if reader is None:
        print('Failed to open script.csv with tried encodings:', encodings_to_try)
        sys.exit(1)
    print('Opened script.csv with encoding:', used_encoding)
    for i, row in enumerate(reader, start=1):
            total += 1
            if len(row) < 4:
                errors.append(f'Row {i} has <4 fields: {len(row)}')
                continue
            index = row[0]
            orig_filename = row[1]
            shortname = row[2]
            # The 4th field may contain newlines already parsed by csv.reader
            content = row[3]
            try:
                out_rows = process_record(index, orig_filename, shortname, content)
            except Exception as e:
                errors.append(f'Error processing record {index} ({shortname}): {e}')
                continue
            if not out_rows or len(out_rows) <= 2:
                # no translatable lines; still create small file with header
                out_rows = [['Original Text','Initial','Machine translation','Better translation','Best translation'],['Key','Value','','','']]
            # Write CSV
            csv_path = OUT_DIR / f"{shortname}.csv"
            try:
                with open(csv_path, 'w', encoding='utf-8', newline='') as outcsv:
                    writer = csv.writer(outcsv, quoting=csv.QUOTE_MINIMAL)
                    for r in out_rows:
                        writer.writerow(r)
            except Exception as e:
                errors.append(f'Failed writing CSV {csv_path}: {e}')
                continue
            # Write XLSX via pandas if available
            xlsx_path = OUT_DIR / f"{shortname}.xlsx"
            if pd is not None:
                try:
                    df = pd.DataFrame(out_rows, columns=None)
                    # Ensure column names: will set to header row values for readability
                    # But keep the exact structure by writing without header and index
                    df.to_excel(xlsx_path, index=False, header=False)
                except Exception as e:
                    errors.append(f'Failed writing XLSX {xlsx_path}: {e}')
            manifest_rows.append([index, orig_filename, shortname, str(csv_path.relative_to(GAME_DIR)), str(xlsx_path.relative_to(GAME_DIR))])
            processed += 1
    # Write manifest
    man_path = OUT_DIR / 'manifest.csv'
    with open(man_path, 'w', encoding='utf-8', newline='') as mf:
        w = csv.writer(mf)
        w.writerow(['index','original_filename','shortname','csv_path','xlsx_path'])
        for r in manifest_rows:
            w.writerow(r)
    # Write errors log
    if errors:
        err_path = OUT_DIR / 'errors.log'
        with open(err_path, 'w', encoding='utf-8') as ef:
            for e in errors:
                ef.write(e + '\n')
    print(f'Done. Total rows read: {total}. Scenes processed: {processed}. Outputs in: {OUT_DIR}')
    if errors:
        print('There were errors; see', OUT_DIR / 'errors.log')

if __name__ == '__main__':
    main()
