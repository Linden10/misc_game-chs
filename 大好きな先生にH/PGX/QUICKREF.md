# PGX Conversion Quick Reference Card

## TL;DR: Convert PNG → PGX

```bash
# Single file
python PGX_Reverse_Conv.py convert_single edited.png out.pgx template.pgx

# Multiple files (batch)
python PGX_Reverse_Conv.py convert_batch png_folder/ pgx_out/ pgx_templates/

# Repack to ZIP
python PGX_Reverse_Conv.py repack_zip pgx_out/ result.zip
```

## PGX File Structure (at a glance)

```
Header (20 bytes):
  Offset  Size  Field
  0–3     4     Magic (0x00000000)
  4–7     4     Width (little-endian)
  8–11    4     Height (little-endian)
  12–13   2     Flags (bit 0 = 32-bit, bit 12 = GMS present)
  14–15   2     Reserved
  16–19   4     Packed size (compressed data length)

Data:
  [Compressed pixels in LZSS format]
  
Pixel format: BGRA (4 bytes per pixel)
Compression: Custom LZSS (4KB sliding dictionary)
```

## One-Command Workflow

```bash
# 1. Extract PGX → PNG
python PGX_Conv.py extract original_pgx_folder/ extracted_png/

# 2. Edit PNG files in GIMP/Photoshop
# (Keep same dimensions!)

# 3. Convert back PNG → PGX
python PGX_Reverse_Conv.py convert_batch edited_png/ pgx_out/ original_pgx_folder/

# 4. Repack to ZIP
python PGX_Reverse_Conv.py repack_zip pgx_out/ result.zip

# 5. Replace in game + test
# Copy result.zip over game's c08d1.g and run punipuni_CHS.exe
```

## Key Points

✓ **Always use a template PGX file** of the same dimensions  
✓ **BGRA format** (not RGBA) — script handles conversion automatically  
✓ **LZSS compression** is not deterministic — different sizes are OK  
✓ **Dimensions must match** between PNG and template PGX  
✓ **Transparency preserved** in alpha channel  

## Correlation with Font Tools

| Concept | Font Tools (`HanziReplacer.py`) | PGX Tools (`PGX_Reverse_Conv.py`) |
|---------|--------|----------|
| Base file | Original TTF | Original PGX |
| Modification | Remap glyphs | Replace pixels |
| Template | Use base font | Use base PGX |
| Batch mode | `ChangeFont()` | `convert_batch()` |
| Compression | otfcc binary | LZSS compressed |

## Error Checklist

| Error | Fix |
|-------|-----|
| Dimension mismatch | Resize PNG or use matching template |
| PNG too large | Crop/resize to match template dimensions |
| Converted PGX corrupted | Verify template is valid; try different template |
| Game shows wrong images | Ensure ZIP was repacked correctly; verify dimensions |
| "packed_size" mismatch | Header may be corrupted; use different template |

## Command Reference

```bash
# Extract: PGX → PNG
python PGX_Conv.py extract <pgx_folder> <png_output>

# Convert: PNG → PGX (single file)
python PGX_Conv.py convert <png_folder> <pgx_output> <template_pgx>

# Convert: PNG → PGX (enhanced, batch)
python PGX_Reverse_Conv.py convert_single <png> <out> <template>
python PGX_Reverse_Conv.py convert_batch <png_dir> <out_dir> <template_dir>

# Repack: PGX → ZIP
python PGX_Reverse_Conv.py repack_zip <pgx_folder> <output.zip>

# Roundtrip test: PGX → PNG → PGX → ZIP
python PGX_Reverse_Conv.py roundtrip <pgx_folder> <test_output>
```

## File Locations

- **Converters:** `/大好きな先生にH/PGX/PGX_Conv.py`, `PGX_Reverse_Conv.py`
- **Full docs:** `/大好きな先生にH/PGX/PGX_REVERSE_GUIDE.md`
- **This guide:** `/大好きな先生にH/PGX/PGX_ANALYSIS_SUMMARY.md`
- **Sample data:** `/大好きな先生にH/PGX/c08d1.g.zip` (original PGX files)
- **Extracted examples:** `/大好きな先生にH/PGX/converted pgx files/` (PNG examples)

---

**Last updated:** December 2025  
**For full technical details, see:** `PGX_REVERSE_GUIDE.md`
