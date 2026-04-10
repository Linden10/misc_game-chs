# Punipuni English Translation Guide v2

A step-by-step guide for translating Punipuni (大好きな先生にH) into English using the existing toolchain. This guide is written for an English-only workflow — no Chinese text required.

---

## Table of Contents

1. [How It Works](#how-it-works)
2. [Prerequisites](#prerequisites)
3. [Folder Layout](#folder-layout)
4. [Phase 1 — Extract Text](#phase-1--extract-text)
5. [Phase 2 — Translate](#phase-2--translate)
6. [Phase 3 — Prepare Name Dictionary](#phase-3--prepare-name-dictionary)
7. [Phase 4 — Inject Translations](#phase-4--inject-translations)
8. [Phase 5 — Rebuild Bitmap Fonts](#phase-5--rebuild-bitmap-fonts)
9. [Phase 6 — Translate EXE-Embedded Text](#phase-6--translate-exe-embedded-text)
10. [Phase 7 — Deploy & Test](#phase-7--deploy--test)
11. [Half-Width vs Full-Width Text](#half-width-vs-full-width-text)
12. [How HanziReplacer Works (and Why You Still Need It)](#how-hanzireplacer-works-and-why-you-still-need-it)
13. [Troubleshooting](#troubleshooting)
14. [File Reference](#file-reference)

---

## How It Works

The game engine (CAGE) stores dialogue scripts in **BCS** files, which are Shift-JIS (codepage 932) encoded. The translation pipeline is:

```
BCS (encrypted) ──► BCS (decrypted) ──► CSV ──► JSON (for translation) ──► translated JSON ──► inject back into CSV ──► game reads CSV
```

In parallel, the game's **bitmap fonts** (`.FT` files) and certain **EXE-embedded strings** also need updating.

A runtime DLL injector called **UniversalInjectorFramework (UFI)** handles character substitution at runtime. This is needed because some English characters (e.g., accented letters or special punctuation) cannot be encoded in Shift-JIS. The system maps them through rare SJIS kanji as intermediaries, then swaps them back at display time.

### Key Difference from Chinese Translation

The original Chinese workflow calls `replace_halfwidth_with_fullwidth()` on **all** translated text, converting ASCII `A-Z a-z 0-9` and punctuation to their fullwidth equivalents (e.g., `A` → `Ａ`). **For English, you must skip this conversion** to keep readable half-width text. The game engine supports half-width ASCII characters natively through Shift-JIS.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.8+ | With `Pillow` (`pip install Pillow`) |
| Windows (recommended) | Or Linux with Wine for `otfccdump.exe` / `otfccbuild.exe` |
| Original game files | Specifically `punipuni.exe` and the game data |
| `BcsDec.exe` or `BcsExtractor.exe` | For decrypting BCS scripts (included in this folder) |
| `otfccdump.exe` + `otfccbuild.exe` | Font manipulation tools (in `CAGE_TOOL/`) |
| A TTF font with English glyphs | e.g., `FZY1JW.TTF` (included) or any Latin font |
| VC++ x86 Redistributable | If game fails to start on Windows: https://aka.ms/vs/17/release/vc_redist.x86.exe |

---

## Folder Layout

After setup, your working directory should look like:

```
大好きな先生にH/
├── scr/              # Original encrypted BCS files
├── scr_dec/          # Decrypted BCS files (from BcsDec.exe)
├── scr_csv/          # CSV exports (from bcs2csv.py)
├── gt_input/         # Extracted JSON for translation (from dump.py)
├── gt_output/        # Your English translations go here
├── font/             # Original .FT bitmap font files
│   ├── DEFAULT.FT
│   └── MENU.FT
├── release/          # Output: patched files ready for deployment
│   └── trans/        # Translated CSVs + rebuilt fonts + data.bin
├── namedict.json     # Character name mapping
├── replace.json      # Generated glyph replacement map
├── exetext.bin       # Extracted EXE strings (binary)
├── HanziReplacer.py  # Character mapping engine
├── Lib.py            # Utilities (I/O, font helpers, text processing)
├── bcs2csv.py        # BCS ↔ CSV converter
├── dump.py           # Text extractor (BCS → JSON)
├── inject.py         # Text injector (JSON → CSV)
├── FT_FILE.py        # Bitmap font rebuilder
├── dump_exe_text.py  # EXE string extractor
└── gen_transdict.py  # Translation dictionary generator
```

---

## Phase 1 — Extract Text

### 1.1 Decrypt BCS Scripts

Place the original `.BCS` files into `scr/`, then run the decrypter:

```bash
# On Windows — run from the 大好きな先生にH folder
BcsExtractor.exe
# This reads scr/*.BCS and outputs decrypted files to scr_dec/
```

If `BcsExtractor.exe` doesn't work, try `BcsDec.exe` from `CAGE_TOOL/`.

### 1.2 Convert BCS to CSV (Optional Inspection)

```bash
python bcs2csv.py
# Creates scr_csv/ with one CSV per BCS file
# Useful for inspecting the script structure
```

### 1.3 Extract Translatable Text to JSON

```bash
python dump.py
# Creates gt_input/ with JSON files containing all dialogue
# Also generates namedict.json with character names
```

Each JSON file contains entries like:

```json
{
    "name": "かなみ",
    "name_pos": "11 9 name",
    "message": "え、先生……？",
    "pos": "11 13 text"
}
```

- `message` — the text to translate
- `name` — the speaking character's name (Japanese)
- `pos` / `name_pos` — internal position markers (do NOT modify)

### 1.4 Extract EXE-Embedded Text

```bash
python dump_exe_text.py
# Reads exetext.bin, outputs gt_input/exetext.json
# Contains UI strings, system messages, etc.
```

---

## Phase 2 — Translate

### 2.1 Create English Translations

1. Copy the `gt_input/` folder to `gt_output/`.
2. Edit each JSON file, replacing the Japanese `message` values with English.

**Important rules:**

- Keep the `pos`, `name_pos`, `name`, and `ori` fields unchanged.
- Only modify the `message` field.
- Use standard ASCII characters wherever possible (they work natively in SJIS).
- Avoid characters outside basic ASCII unless necessary (accented letters like `é` require the HanziReplacer mapping system — see [below](#how-hanzireplacer-works-and-why-you-still-need-it)).
- Use `...` or `…` for ellipsis. The inject script converts `...` → `…` automatically.
- Use straight quotes `"` — the inject script converts them to `「」` via `processQuote()`.

**Example translated entry:**

```json
{
    "name": "かなみ",
    "name_pos": "11 9 name",
    "message": "Huh, teacher...?",
    "pos": "11 13 text"
}
```

### 2.2 Translate the EXE Text

Edit `gt_output/exetext.json`:

```json
{
    "ori": "セーブしますか？",
    "message": "Save the game?"
}
```

### 2.3 Automated Translation (Optional)

The repo includes a `run_GalTransl_v5.9.1_gpt4-turbo.bat` for machine translation via GalTransl. You can adapt this for English output by configuring GalTransl's target language. The `transl_cache/` folder stores cached translations.

---

## Phase 3 — Prepare Name Dictionary

Edit `namedict.json` to map Japanese character names → English:

```json
{
    "隆行": "Takayuki",
    "かなみ": "Kanami",
    "ともか": "Tomoka",
    "りおん": "Rion",
    "なつゆ": "Natsuyu",
    "はるか": "Haruka",
    "けいと": "Keito",
    "ゆず": "Yuzu",
    "女の子": "Girl",
    "配達員": "Delivery person"
}
```

You can also update the dictionary generator `gen_transdict.py` with English names:

```python
a.addname(jp_name=["隆行"], chs_name=["Takayuki"], sex="man", role="teacher")
a.addname(jp_name=["鮎川 ともか"], chs_name=["Ayukawa Tomoka"], sex="woman")
# etc.
```

Then run `python gen_transdict.py` to regenerate `namedict.json` and the GPT dictionary.

---

## Phase 4 — Inject Translations

**Before running `inject.py`, you need to modify it for English output.**

### 4.1 Key Modification: Remove Full-Width Conversion

The original `inject.py` calls `replace_halfwidth_with_fullwidth()` on all text, which converts ASCII to fullwidth Japanese-width characters. **For English, you must remove or skip this call.**

In `bcs2csv.py`, inside the `trans()` method, find and comment out:

```python
# transtext = replace_halfwidth_with_fullwidth(transtext)  # REMOVE for English
```

Similarly in `inject.py`, for the EXE text handling:

```python
# trans = replace_halfwidth_with_fullwidth(trans)  # REMOVE for English
```

### 4.2 Run the Injector

```bash
python inject.py
```

This will:

1. Scan all English translations in `gt_output/` for non-SJIS characters.
2. Create `replace.json` (character mapping table).
3. Generate `release/trans/data.bin` (encrypted mapping for UFI runtime).
4. For each script file, inject translations into the BCS data and output CSV files to `release/trans/`.
5. For `exetext.json`, generate `replace.txt` with C++ `addSjisReplaceMap()` calls for EXE string patching.
6. Rebuild the bitmap fonts (calls `FT_FILE.main()` at the end).

### 4.3 Runtime Character Mapping (data.bin)

The `data.bin` file contains paired source→target characters, XOR-encrypted with the key `"yorimichi"`. At runtime, the UFI DLL (`punipuni.dll`) reads this file and swaps the rare SJIS kanji back to the intended English characters. For pure ASCII English text, this mapping will be minimal or empty.

---

## Phase 5 — Rebuild Bitmap Fonts

The game uses custom `.FT` bitmap font files (`DEFAULT.FT` and `MENU.FT`). These must be rebuilt to display the replacement characters correctly.

### 5.1 Choose a Source Font

The current script uses `FZY1JW.TTF` (a Chinese font included in the folder). For English, you can:

- **Keep `FZY1JW.TTF`** — it has Latin glyphs and works fine for English.
- **Use any TTF font** with good Latin coverage. Update the font path in `FT_FILE.py`:

```python
fonts = [0] + [ImageFont.truetype("YourFont.ttf", i) for i in range(1, 50)]
```

### 5.2 Run the Font Rebuilder

`inject.py` calls `FT_FILE.main()` at the end, which:

1. Reads `replace.json` (the character mapping).
2. For each character in the `.FT` file, redraws it using the source TTF font.
3. Outputs rebuilt fonts to `release/trans/`.

If you want to run it standalone:

```bash
python FT_FILE.py
# or
python test.py  # (which just calls FT_FILE.main())
```

The rebuilt fonts will appear in `release/trans/DEFAULT.FT` and `release/trans/MENU.FT`.

---

## Phase 6 — Translate EXE-Embedded Text

EXE-embedded strings (UI labels, system prompts) are handled specially:

1. `dump_exe_text.py` extracts strings from `exetext.bin` → `gt_input/exetext.json`.
2. You translate them in `gt_output/exetext.json`.
3. `inject.py` generates `replace.txt` with lines like:

```cpp
addSjisReplaceMap(L"セーブしますか？", L"Save the game?");
```

4. These replacement rules are compiled into the patched EXE (`punipuni_CHS.exe`).

**Note:** If you're not rebuilding the EXE yourself, the `replace.txt` entries must be integrated into the UFI injector's configuration or a custom DLL hook. Consult the `CAGE_TOOL/README.txt` for details on the injector setup.

---

## Phase 7 — Deploy & Test

### 7.1 Backup

**Always back up the original game folder before patching.**

### 7.2 Copy Patch Files

Copy the contents of `release/` to your game directory:

```
release/
├── punipuni_CHS.exe    # Patched executable
├── punipuni.dll        # UFI injector DLL
├── LoaderDll.dll       # DLL loader
├── LocaleEmulator.dll  # Locale emulator (for SJIS locale)
└── trans/
    ├── 01kan.csv       # Translated script files
    ├── 02tom.csv
    ├── ...
    ├── DEFAULT.FT      # Rebuilt bitmap fonts
    ├── MENU.FT
    └── data.bin        # Runtime character mapping
```

### 7.3 Launch

Run `punipuni_CHS.exe` from the game folder.

If it won't start on Windows, install the VC++ x86 redistributable:
https://aka.ms/vs/17/release/vc_redist.x86.exe

### 7.4 Verify

- Check that English dialogue appears correctly.
- Verify character names display as expected.
- Check menu items and UI strings.
- Look for boxes (□) or garbled text — these indicate missing font glyphs or encoding issues.

---

## Half-Width vs Full-Width Text

This is the most important difference between the Chinese and English workflows.

| Aspect | Chinese Workflow | English Workflow |
|---|---|---|
| ASCII characters | Converted to fullwidth (`A` → `Ａ`) | **Kept as half-width** (`A` stays `A`) |
| Function | `replace_halfwidth_with_fullwidth()` | **Skip / comment out this call** |
| Why | CJK text looks better with uniform-width chars | English is unreadable in fullwidth |
| SJIS compatibility | Fullwidth chars are valid SJIS | Half-width ASCII is valid SJIS (bytes 0x20–0x7E) |

### What `replace_halfwidth_with_fullwidth()` does

Located in `Lib.py`, it maps:

```
Half-width:  A B C ... Z a b c ... z 0 1 ... 9 , ? ! ~ _ : ( ) -
Full-width:  Ａ Ｂ Ｃ ... Ｚ ａ ｂ ｃ ... ｚ ０ １ ... ９ ， ？ ！ ～ ＿ ： （ ） —
```

**For English: do NOT call this function.** Remove or comment out the call in:

- `bcs2csv.py` → `trans()` method (line with `replace_halfwidth_with_fullwidth`)
- `inject.py` → EXE text loop (line with `replace_halfwidth_with_fullwidth`)

---

## How HanziReplacer Works (and Why You Still Need It)

Even for English, some characters may not encode in Shift-JIS. The `HanziReplacer` system handles this:

1. **Scans** all your translated text for characters that fail `char.encode('sjis')`.
2. **Maps** each such character to a rare SJIS kanji from a pre-built list (`charlist`).
3. **Generates** `data.bin` — a runtime mapping file read by the UFI DLL.
4. **At runtime**, the DLL swaps the rare kanji back to the original character on screen.

### When is this needed for English?

- **Pure ASCII English** (a-z, A-Z, 0-9, basic punctuation): No mapping needed. These encode directly in SJIS.
- **Extended characters** (é, ñ, ü, em-dash —, curly quotes " ", etc.): Require mapping through the HanziReplacer system.

### Recommendation

Stick to plain ASCII for maximum compatibility. If you must use special characters:

1. The `HanziReplacer` will automatically detect and map them.
2. The `ChangeFont()` method will remap the font glyphs accordingly.
3. The `data.bin` + UFI DLL will swap them back at runtime.

---

## Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| Text appears as fullwidth `Ｈｅｌｌｏ` | `replace_halfwidth_with_fullwidth()` still active | Comment out the call in `bcs2csv.py` and `inject.py` |
| Boxes (□) appear | Missing glyph in bitmap font | Check `not_found.json`; ensure your source TTF has the needed glyphs |
| `UnicodeEncodeError` during inject | Character can't encode in SJIS | HanziReplacer should handle this automatically; if not, simplify the character |
| Game crashes on start | Missing VC++ runtime | Install https://aka.ms/vs/17/release/vc_redist.x86.exe |
| `otfccdump.exe` not found | Running on Linux without Wine | Install `otfcc` natively or run via Wine |
| Text overflows dialogue box | English text is longer than Japanese | Shorten translations or add line breaks (`\n`) |
| `replace.json` is empty | No non-SJIS characters found | This is fine for pure ASCII English — no remapping needed |
| Font build fails with missing chars | Source TTF doesn't have required glyphs | Use a more complete font (e.g., one with full Latin Extended coverage) |

---

## File Reference

| File | Purpose |
|---|---|
| `BcsExtractor.exe` | Decrypts BCS script files |
| `bcs2csv.py` | BCS ↔ CSV conversion; contains the `trans()` injection method |
| `dump.py` | Extracts translatable text from BCS → JSON |
| `dump_exe_text.py` | Extracts SJIS strings from `exetext.bin` → JSON |
| `inject.py` | Main injection script: translations → CSV + fonts + data.bin |
| `HanziReplacer.py` | Detects non-SJIS chars, creates runtime mapping |
| `Lib.py` | I/O helpers, `replace_halfwidth_with_fullwidth()`, `BytesReader`, `OriJsonOutput` |
| `FT_FILE.py` | Bitmap font rebuilder (for `DEFAULT.FT` / `MENU.FT`) |
| `FT_FILE.py0` | Alternate font rebuilder (different FT format, uses LZSS-compressed char data) |
| `gen_transdict.py` | Generates GPT translation dictionary + updates `namedict.json` |
| `gen_transdict_LIB.py` | Helper library for `gen_transdict.py` |
| `test.py` | Quick runner for `FT_FILE.main()` |
| `namedict.json` | Japanese name → translated name mapping |
| `replace.json` | Generated: SJIS kanji → target character map (for font rebuild) |
| `replace.txt` | Generated: EXE string replacement rules (C++ format) |
| `exetext.bin` | Raw EXE text dump (binary, SJIS encoded) |

---

## Quick-Start Cheat Sheet

```bash
# 1. Decrypt scripts
./BcsExtractor.exe

# 2. Extract text
python dump.py
python dump_exe_text.py

# 3. Copy gt_input → gt_output, translate message fields to English

# 4. Update namedict.json with English names

# 5. IMPORTANT: Comment out replace_halfwidth_with_fullwidth() in bcs2csv.py and inject.py

# 6. Inject translations and rebuild fonts
python inject.py

# 7. Copy release/ contents to game folder, launch punipuni_CHS.exe
```

---

**Last updated:** April 2026
**Tools location:** `大好きな先生にH/`
**CAGE_TOOL location:** `CAGE_TOOL/`
