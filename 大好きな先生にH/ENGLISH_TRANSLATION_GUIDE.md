# Punipuni English Translation Guide

This guide explains how to translate Punipuni into English using the font integration tools present in this folder and the `CAGE_TOOL` directory.

## Overview

The translation process works by:
1. Preparing your English translation files in JSON format.
2. Using `HanziReplacer.py` to detect characters that cannot be encoded in Shift-JIS (SJIS) and create a temporary mapping.
3. Building a replacement font that maps temporary codepoints to English glyphs.
4. Updating the UniversalInjectorFramework (UFI) configuration to restore original English characters at runtime.
5. Deploying the new font and configuration to the game folder.
6. Testing the game with English text.

## Prerequisites

- **Windows (recommended)** or Linux with Wine (for `otfcc*.exe`) and Python 3.
- Python 3 (pure stdlib, no extra packages needed).
- Backup of the original game folder before making any changes.
- Game folder with `punipuni.exe` or `punipuni_CHS.exe` available.
- (Windows only) If the game fails to start, install the Visual C++ redistributable (x86):
  - https://aka.ms/vs/17/release/vc_redist.x86.exe

## Files You'll Use

- `HanziReplacer.py` — Main tool for character mapping and font modification.
- `Lib.py` — Helper functions for file I/O and font operations.
- `otfccdump.exe`, `otfccbuild.exe` — Font JSON dump/build utilities (Windows; use Wine on Linux or native Linux `otfcc` binaries).
- `WenQuanYi.ttf` — Source font containing extensive glyphs (used to build the replacement font).
- `release/` — Patch files to copy to the game (includes DLLs, configs, and the new font once built).
- `CAGE_TOOL/` — Contains injector setup and configuration instructions.

## Step-by-Step Instructions

### Step 1: Prepare Your English Translation Files

Create a folder for your English translations:
- **Linux/WSL:** `/workspaces/misc_game-chs/大好きな先生にH/trans/eng/`
- **Windows:** `C:\path\to\misc_game-chs\大好きな先生にH\trans\eng\`

Each translation file should be a JSON list of objects with at least a `"message"` field:

```json
[
  {
    "message": "Good morning, teacher."
  },
  {
    "message": "I would like to ask you something."
  },
  {
    "message": "Thank you for everything."
  }
]
```

**Note:** If you have translations in CSV format (like `release/trans/01kan.csv`), you will need to convert them to JSON format. A conversion script can be provided if needed.

### Step 2: Normalize Punctuation (Recommended)

Clean up any special punctuation in your English text:
- Replace em-dashes ("—") with hyphens ("-").
- Replace curly quotes (" ") with straight quotes ("") or Japanese-style brackets.
- Remove unusual whitespace or special Unicode characters that may not render properly.

The `HanziReplacer.py` includes helper functions:
- `fuhaotihuan(text)` — Replaces unsupported punctuation shapes with displayable equivalents.
- `Lib.replace_symbol_for_gbk(text)` — Can be adapted for normalization.

### Step 3: Generate Character Mapping

Create a Python script (e.g., `run_mapping.py`) in the `大好きな先生にH` folder:

```python
from HanziReplacer import HanziReplacer
import os

hr = HanziReplacer()

# Path to your English translation folder (relative to this script)
trans_folder = "./trans/eng"

# Read all English JSON files and build mapping
hr.ReadTransAndGetHanzidictFromFolder(trans_folder, otherfiles=[])

# Generate the mapping binary used by the injector
hr.gen_replace("./release/charmap.bin")

# Print mapping for verification
print("=" * 60)
print("CHARACTER MAPPING GENERATED")
print("=" * 60)
print(f"Source chars (temp, length={len(hr.source_chars)}): {hr.source_chars[:50]}...")
print(f"Target chars (English, length={len(hr.target_chars)}): {hr.target_chars[:50]}...")
print(f"Mapping binary saved to: ./release/charmap.bin")
print("=" * 60)
```

**Run the script:**

- **Windows CMD:**
  ```
  cd C:\path\to\misc_game-chs\大好きな先生にH
  python run_mapping.py
  ```

- **Linux/WSL bash:**
  ```bash
  cd /workspaces/misc_game-chs/大好きな先生にH
  python3 run_mapping.py
  ```

The script will:
- Detect all characters in your English text that cannot be encoded in Shift-JIS.
- Create a one-to-one mapping to temporary replacement characters (from `HanziReplacer.charlist`).
- Generate `charmap.bin` for the injector.
- Print `source_chars` and `target_chars` for verification.

### Step 4: Build the Replacement Font

Create another script (e.g., `build_font.py`) in the `大好きな先生にH` folder:

```python
from HanziReplacer import HanziReplacer

# Run the mapping script first to generate hr data
# For this example, we'll re-initialize and load the mapping
hr = HanziReplacer()
trans_folder = "./trans/eng"
hr.ReadTransAndGetHanzidictFromFolder(trans_folder, otherfiles=[])

# Build the replacement font
ori_font = "WenQuanYi.ttf"  # Source font with extensive glyphs
out_font = "./release/punipuni_eng.ttf"  # Output font path
font_name = "PunipuniEnglish"  # Friendly font name

print("Building replacement font...")
try:
    hr.ChangeFont(ori_font, out_font, font_name)
    print(f"✓ Font built successfully: {out_font}")
except RuntimeError as e:
    print(f"✗ Font build failed: {e}")
    print("  Try removing unsupported characters from your English text.")
```

**Run the script:**

- **Windows CMD:**
  ```
  cd C:\path\to\misc_game-chs\大好きな先生にH
  python build_font.py
  ```

- **Linux/WSL bash:**
  ```bash
  cd /workspaces/misc_game-chs/大好きな先生にH
  python3 build_font.py
  ```

**Important Notes:**

- `ChangeFont` internally calls `otfccdump.exe` and `otfccbuild.exe` (Windows binaries).
- **On Windows:** These executables should work directly if present in the same folder.
- **On Linux/WSL:** Either:
  - Install native `otfcc` binaries via your package manager, or
  - Run the script under Wine to invoke the `.exe` files.
- If you see errors like "字体中不存在:" (character not in font), either:
  - Remove those characters from your English text, or
  - Add more replacement characters to `HanziReplacer.charlist` in `HanziReplacer.py`.

### Step 5: Update the Injector Configuration

The `HanziReplacer.ChangeUFIConfig` method updates the UniversalInjectorFramework (UFI) configuration with your character mappings.

**Option A: Automatic (via script)**

Add this to your `run_mapping.py` or create a new script:

```python
from HanziReplacer import HanziReplacer
import json
import os

hr = HanziReplacer()
trans_folder = "./trans/eng"
hr.ReadTransAndGetHanzidictFromFolder(trans_folder, otherfiles=[])

# Locate and update UFI config
ufi_config_paths = [
    "./release/UniversalInjectorFramework/config.json",
    "./config.json",
]

for ufi_config in ufi_config_paths:
    if os.path.exists(ufi_config):
        print(f"Updating: {ufi_config}")
        hr.ChangeUFIConfig(ufi_config)
        print("✓ UFI config updated successfully")
        break
else:
    print("⚠ UFI config not found. Update manually (see Option B below).")
```

**Option B: Manual Update**

1. Locate the UFI configuration file (typically `config.json` in the patch folder or in `CAGE_TOOL`).
2. Open it in a text editor.
3. Find or create the `text_processor.rules[0]` section:
   ```json
   {
     "text_processor": {
       "rules": [
         {
           "source_chars": "䌀䌁䌂…",
           "target_chars": "Hello…"
         }
       ]
     }
   }
   ```
4. Replace:
   - `source_chars` with the value of `hr.source_chars` (printed by `run_mapping.py`).
   - `target_chars` with the value of `hr.target_chars` (printed by `run_mapping.py`).
5. Ensure `source_chars` and `target_chars` have the same length.
6. Save the file.

### Step 6: Deploy Patch Files to the Game Folder

1. **Backup the original game folder** (critical!).

2. Copy the generated files to the game directory:
   - Copy `release/punipuni_eng.ttf` to the game's font folder (or replace the original font).
   - Copy `release/charmap.bin` to the patch/injector folder.
   - Copy the updated `config.json` to the patch/injector folder.
   - Copy other patch files from `release/` (e.g., `JYXJYX1234.dll`, `setdll.exe`) only if you trust them. **Keep backups of originals.**

3. Consult `CAGE_TOOL/README` or instructions for exact file placement—the injector may have a specific structure.

### Step 7: Run and Test

1. Launch `punipuni_CHS.exe` from the game folder.
2. Check if English text appears correctly.

**If you see boxes, gibberish, or wrong glyphs:**
- Confirm the game uses the new font (check game settings or injector logs).
- Verify `source_chars` and `target_chars` lengths match exactly.
- Re-run `build_font.py` if you changed the mapping.
- Check injector logs for errors.

**If the game fails to start on Windows:**
- Install the Visual C++ x86 redistributable: https://aka.ms/vs/17/release/vc_redist.x86.exe
- Restart your computer.
- Try launching again.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Mapping lengths don't match | Ensure `len(source_chars) == len(target_chars)`. Run `run_mapping.py` again. |
| Font build fails with missing glyphs | Use a larger source font (e.g., a Unicode-complete font) or add more glyphs to `HanziReplacer.charlist`. |
| `otfcc*.exe` not found on Linux | Install native `otfcc` binaries or run the script under Wine. |
| Game shows boxes or wrong characters | Verify the game loads the correct font; confirm source/target char mapping; check injector config. |
| Game crashes on startup (Windows) | Install Visual C++ x86 redistributable and restart. |
| UFI config not found | Check `CAGE_TOOL` README for the correct config file location. |

## Optional: Combined Automation Script

If you want to automate the entire process in one script, create `full_build.py`:

```python
from HanziReplacer import HanziReplacer
import os

print("=" * 60)
print("PUNIPUNI ENGLISH TRANSLATION BUILD")
print("=" * 60)

hr = HanziReplacer()
trans_folder = "./trans/eng"

print("\n[1/3] Scanning English translation files...")
hr.ReadTransAndGetHanzidictFromFolder(trans_folder, otherfiles=[])
print(f"✓ Detected {len(hr.source_chars)} non-SJIS characters")

print("\n[2/3] Generating character mapping...")
hr.gen_replace("./release/charmap.bin")
print("✓ Mapping binary saved to: ./release/charmap.bin")

print("\n[3/3] Building replacement font...")
try:
    hr.ChangeFont("WenQuanYi.ttf", "./release/punipuni_eng.ttf", "PunipuniEnglish")
    print("✓ Font built: ./release/punipuni_eng.ttf")
except RuntimeError as e:
    print(f"✗ Font build failed: {e}")
    exit(1)

print("\n[4/4] Updating UFI configuration...")
ufi_config = "./release/UniversalInjectorFramework/config.json"
if os.path.exists(ufi_config):
    hr.ChangeUFIConfig(ufi_config)
    print(f"✓ UFI config updated: {ufi_config}")
else:
    print(f"⚠ UFI config not found at {ufi_config}")
    print(f"   Manually set source_chars={hr.source_chars}")
    print(f"   Manually set target_chars={hr.target_chars}")

print("\n" + "=" * 60)
print("BUILD COMPLETE")
print("=" * 60)
print("\nNext steps:")
print("1. Backup your original game folder.")
print("2. Copy release/punipuni_eng.ttf to the game's font folder.")
print("3. Copy release/charmap.bin and updated config.json to the patch folder.")
print("4. Run punipuni_CHS.exe and test.")
```

Run it with:
```bash
python full_build.py
```

## Tips and Tricks

- **Different source font:** If you prefer a different glyph source (e.g., a Latin-heavy TTF), replace `WenQuanYi.ttf` with your font in `ChangeFont()`.
- **Large translations:** If you have many translation files, the tool will automatically scan all JSON files in the `trans/eng` folder.
- **Verify mappings:** After `run_mapping.py`, review the printed `source_chars` and `target_chars` to ensure they are reasonable.
- **Incremental updates:** If you modify your English text later, re-run `run_mapping.py` and `build_font.py` to regenerate the mapping and font.

## Support

For detailed information on the tools:
- See `HanziReplacer.py` docstrings and comments.
- Check `CAGE_TOOL/README` for injector-specific configuration.
- Review the Chinese translation examples in `release/trans/` for reference.

---

**Last updated:** December 2025  
**Tools location:** `/workspaces/misc_game-chs/大好きな先生にH/`  
**CAGE_TOOL location:** `/workspaces/misc_game-chs/CAGE_TOOL/`
