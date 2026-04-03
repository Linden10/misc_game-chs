# restore_ruby_xlsx.py Guide

This script rebuilds the processed ruby-restored XLSX files by combining:

- the original JP XLSX files
- the translated XLSX files
- the raw `.ss` script files

It restores the translations into the original 5-column workbook layout so the files stay convenient for reinsertion work.

## Requirements

- Python 3
- `openpyxl`

Install the dependency:

```bash
python3 -m pip install --user openpyxl
```

## Files used in this repository

- Original JP XLSX zip:
  `/home/runner/work/misc_game-chs/misc_game-chs/original_JP_xlsx.zip`
- Translated XLSX zip:
  `/home/runner/work/misc_game-chs/misc_game-chs/translated_proofreaded_xlsx.zip`
- Raw SS zip:
  `/home/runner/work/misc_game-chs/misc_game-chs/ss_20250511_111752.zip`
- Script:
  `/home/runner/work/misc_game-chs/misc_game-chs/闇色のスノードロップス/restore_ruby_xlsx.py`

## Command

Run:

```bash
python3 /home/runner/work/misc_game-chs/misc_game-chs/闇色のスノードロップス/restore_ruby_xlsx.py \
  --original /home/runner/work/misc_game-chs/misc_game-chs/original_JP_xlsx.zip \
  --translated /home/runner/work/misc_game-chs/misc_game-chs/translated_proofreaded_xlsx.zip \
  --ss /home/runner/work/misc_game-chs/misc_game-chs/ss_20250511_111752.zip \
  --output-dir /home/runner/work/misc_game-chs/misc_game-chs/processed_ruby_restored_xlsx \
  --output-zip /home/runner/work/misc_game-chs/misc_game-chs/processed_ruby_restored_xlsx.zip
```

## What the script does

- reads every original workbook from the JP XLSX input
- matches each workbook with the translated XLSX workbook of the same filename
- uses the raw `.ss` scripts to detect ruby text and ruby readings
- restores translations back into the original workbook template
- keeps the original sheet names and 5-column structure:
  - `Key`
  - `Value`
  - `Index`
  - `Text`
  - `Translation`
- writes the rebuilt files to the output directory
- optionally creates a zip from the rebuilt output directory

## Accepted input formats

For `--original`, `--translated`, and `--ss`, you can pass either:

- a directory
- or a `.zip` file

The script extracts zip inputs to a temporary directory automatically.

## Output

After a successful run, you will get:

- rebuilt XLSX files in:
  `/home/runner/work/misc_game-chs/misc_game-chs/processed_ruby_restored_xlsx`
- a zip bundle in:
  `/home/runner/work/misc_game-chs/misc_game-chs/processed_ruby_restored_xlsx.zip`

## Notes

- The translated proofread ZIP can contain the XLSX files inside a subfolder; the script searches recursively.
- The script wraps translated lines at 53 characters.
- If `openpyxl` is missing, the script exits with an install hint.
