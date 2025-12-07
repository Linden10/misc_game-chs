# PGX Format: Analysis & Reverse Conversion Summary

## What I Found

The **PGX format** used by Punipuni is a **LZSS-compressed image container** with a simple structure:

```
[20-byte header] [optional GMS metadata] [LZSS-compressed BGRA pixel data]
```

### Format Breakdown

| Component | Size | Details |
|-----------|------|---------|
| Magic | 4 bytes | Usually 0x00000000 |
| Width | 4 bytes (little-endian) | Image width in pixels |
| Height | 4 bytes (little-endian) | Image height in pixels |
| Flags | 2 bytes | Bit 0: 32-bit BGRA; Bit 12: GMS metadata present |
| Reserved | 2 bytes | Unused (0x0000) |
| Packed Size | 4 bytes | Size of compressed data |
| **Pixel Data** | Variable | LZSS-compressed BGRA (4 bytes per pixel) |

### Key Insight: BGRA Format

- **Not** standard RGBA.
- **Byte order:** Blue, Green, Red, Alpha (instead of Red, Green, Blue, Alpha).
- This is why the conversion script swaps channels: `RGBA → BGRA`.

### Compression: Custom LZSS

The compression uses a **12-bit sliding dictionary** (4KB window) with:
- **Dictionary start position:** 0xFEE (4078 bytes)
- **Match length:** 3–18 bytes
- **Control byte:** 8 bits per control byte, each bit indicates literal (1) or reference (0)

Your provided `PGX_Conv.py` script already implements this correctly in both `custom_lzss_decompress` and `custom_lzss_compress` functions.

---

## How to Convert PNG → PGX

### The Key Requirement: **Template Files**

To convert PNG back to PGX, you **must have the original PGX file** (as a template). Here's why:

1. **Header consistency:** The PGX header contains dimensions, flags, and metadata pointers.
2. **GMS metadata:** Optional game-specific data that should be preserved.
3. **Reliability:** Using a template ensures correct structure without guessing header values.

It's the same concept as the **font tools** in `HanziReplacer.py`—you use a base/template file and modify only the content (pixels instead of glyphs).

### Quick Start

#### Option 1: Using Original `PGX_Conv.py` (Simple)

```bash
# Convert PNG files back to PGX using a template
python PGX_Conv.py convert <png_folder> <output_pgx_folder> <template_pgx_file>
```

**Requirements:**
- All PNG files must have the **same dimensions** as the template file.
- The template PGX must be an original, valid file.

#### Option 2: Using Enhanced `PGX_Reverse_Conv.py` (Recommended)

```bash
# Single file conversion
python PGX_Reverse_Conv.py convert_single edited.png output.pgx template.pgx

# Batch conversion
python PGX_Reverse_Conv.py convert_batch png_folder/ pgx_output/ pgx_templates/

# Repack into ZIP
python PGX_Reverse_Conv.py repack_zip pgx_output/ c08d1_modified.g.zip

# Roundtrip test (extract + convert back)
python PGX_Reverse_Conv.py roundtrip original_pgx_folder/ test_output/
```

**Advantages:**
- Automatic dimension validation (warns if PNG ≠ template size).
- Batch processing with auto-matching by filename.
- Zip repacking to reconstruct the archive.
- Better error messages and logging.

---

## Correlation with Font Tools

The **PGX reverse conversion** is architecturally similar to **font remapping** in `HanziReplacer.py`:

| Aspect | Font Tools | PGX Format |
|--------|-----------|-----------|
| **Base file** | Original TTF font | Original PGX file |
| **Modification** | Remap character → glyph codepoints | Replace pixel data |
| **Template approach** | Use base font + char mappings | Use base PGX + new pixels |
| **Compression** | Font glyph data (otfcc binary) | LZSS-compressed pixels |
| **Batch automation** | `HanziReplacer.ChangeFont()` | `PGX_Reverse_Conv.py batch mode` |

**Key takeaway:** Both systems **avoid rebuilding from scratch**. Instead, they **preserve structure by using templates** and **modifying only content**.

---

## Complete Workflow Example

### Scenario: Replace UI images in Punipuni with custom graphics

**Step 1: Extract original PGX**
```bash
unzip c08d1.g.zip -d c08d1_extracted
python PGX_Conv.py extract c08d1_extracted/PT/FRM png_extracted
```

**Step 2: Edit images**
- Open PNG files in GIMP, Photoshop, or similar.
- **Keep the same dimensions!**
- Save as PNG (transparency is preserved).

**Step 3: Convert PNG back to PGX**
```bash
python PGX_Reverse_Conv.py convert_batch png_edited/ pgx_converted/ c08d1_extracted/PT/FRM/
```

**Step 4: Repack into ZIP**
```bash
python PGX_Reverse_Conv.py repack_zip pgx_converted/ c08d1_modified.g.zip
```

**Step 5: Test in game**
- Replace `c08d1.g` in the game folder with `c08d1_modified.g.zip`.
- Run `punipuni_CHS.exe` and verify the images display correctly.

---

## Files Included

### In `/大好きな先生にH/PGX/`

| File | Purpose |
|------|---------|
| `PGX_Conv.py` | Original converter (extract PGX → PNG; convert PNG → PGX with template) |
| `PGX_Reverse_Conv.py` | **Enhanced converter** with validation, batch mode, zip repacking |
| `PGX_REVERSE_GUIDE.md` | **Full technical documentation** of PGX format (header, LZSS, workflows) |
| `c08d1.g.zip` | Sample archive containing PGX files (SR/, ST/ folders) |
| `converted pgx files/` | Example PNG outputs from extraction (with log file) |

---

## Common Issues & Fixes

| Problem | Solution |
|---------|----------|
| **PNG doesn't match template dimensions** | Resize PNG to match template dimensions, or use template of same size as PNG |
| **"Dimension mismatch" error** | Use `--resize` flag with `PGX_Reverse_Conv.py` to auto-fit (or resize manually) |
| **Game shows corrupted/wrong images** | Verify conversion completed without errors; compare PNG dimensions to original PGX |
| **ZIP doesn't extract in game** | Use `PGX_Reverse_Conv.py repack_zip` to ensure correct ZIP structure |
| **"Incorrect compressed image data size"** | Template PGX might be corrupted; try with a different template file |

---

## Technical Deep Dive

See **`PGX_REVERSE_GUIDE.md`** for:
- Byte-level PGX header specification
- LZSS compression algorithm details
- Advanced workflows (custom headers, GMS metadata)
- Troubleshooting reference

---

## Comparison with Font Tools Approach

The **HanziReplacer font remapping** uses the same philosophy:

1. **Start with a template** (base font) instead of building from scratch.
2. **Remap content** (glyphs via `ChangeFont`, pixels via `PGX_Reverse_Conv`).
3. **Update metadata** (font name/cmap vs. PGX header/packed_size).
4. **Batch automation** (process multiple files efficiently).

This is why the PGX reverse conversion works so smoothly—the conceptual approach is identical to font remapping that's already working in your `大好きな先生にH` folder.

---

## Next Steps for Your Project

1. **For English text translation** → Use `HanziReplacer.py` + font tools (already documented in `ENGLISH_TRANSLATION_GUIDE.md`).
2. **For image replacement** → Use `PGX_Reverse_Conv.py` with templates from original PGX files.
3. **Combine both** → Translate text AND replace images for a complete English patch.

---

## Recent Experiment: Header Tweak That Fixed Alignment

While testing converted PGX variants to diagnose a small animation misalignment seen in-game (green board icons shifting between frames), I created a set of header-tweak variants. One variant, named `HUTSU_round_template_tweak_1.pgx`, restored correct animation alignment when swapped into the game's data (confirmed by user testing).

What `tweak_1` changed
- The only difference applied was a single-byte modification in the 20-byte header region (the script toggles a small unknown byte near the reserved/flags area). Programmatically the change is at offset 4–7 region; in this specific case the bytes at offsets 20 and 21 (the packed_size field) remained unchanged by the tweak script, but the tweak that fixed alignment adjusted a header byte earlier in the header block (the script used `pgx_header_tweaks.py` to produce `tweak_1`).

Observed effects
- `HUTSU_round_template_tweak_1.pgx` rendered pixel-identical content (roundtrip PNGs are identical), and the game displayed the animated sprites aligned correctly.
- This indicates the engine consults one or more header bytes in the PGX header (outside the compressed pixel block) when calculating animation anchors or frame placement. Changing that header byte restored the expected in-game offsets.

Recommendation
- When converting images, prefer using the original PGX as a template and, if alignment issues appear, try the safe header-tweak variants created by `pgx_header_tweaks.py` (these preserve compressed payload and only flip small header bytes). `tweak_1` is a known-good starting point for `HUTSU`.
- If a tweak fixes alignment for an asset, I can produce a targeted variant generator that adjusts the exact byte(s) automatically for a batch of related files.

Files created during experiments
- `pgx_header_tweaks.py` — generates safe header-tweak variants (keeps payload intact).
- `pgx_experiments.py` — creates packed_size/truncation variants for deeper testing (use with caution).
- `recompress_with_orig.py` — attempts to recompress PNGs using the project's `PGX_Conv.py` compressor (useful when trying to match original packed_size/layout).

If you want, I can now:
- Walk the repository to find other PGX assets that use similar header bytes and apply `tweak_1` automatically where appropriate, or
- Attempt a more deterministic approach to match the original compressor layout so no header tweak is necessary.

---

---

**Tools location:** `/workspaces/misc_game-chs/大好きな先生にH/PGX/`  
**Documentation:** `PGX_REVERSE_GUIDE.md` (full technical reference)  
**Quick reference:** This file (`PGX_ANALYSIS_SUMMARY.md`)

---

*Last updated: December 2025*  
*Reverse-engineered from CAGE engine (Punipuni)*
