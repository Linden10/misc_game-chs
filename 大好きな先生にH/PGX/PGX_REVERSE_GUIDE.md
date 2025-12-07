# PGX Format Reverse Engineering & PNG → PGX Conversion Guide

## Overview

The **PGX format** is a proprietary image container used by the CAGE game engine (Punipuni). It's essentially a **ZIP-stored LZSS-compressed BGRA image format** with a 20-byte header and optional GMS metadata.

This guide explains the format structure and provides tools to convert PNG images back to PGX format.

## PGX File Structure

### Header (20 bytes, little-endian)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0-3 | 4 bytes | `magic` | Always `0x00000000` (or magic) |
| 4-7 | 4 bytes | `width` | Image width in pixels |
| 8-11 | 4 bytes | `height` | Image height in pixels |
| 12-13 | 2 bytes | `flags` | Bit 0: 32-bit (BGRA) if set, else 24-bit (BGR). Bit 12: GMS data present if set |
| 14-15 | 2 bytes | `reserved` | Unused, typically 0 |
| 16-19 | 4 bytes | `packed_size` | Size of compressed pixel data (bytes) |

### Data Layout

```
[20-byte header] [optional GMS data] [compressed pixel data]
```

### Pixel Data Format

- **Uncompressed size:** `width × height × 4` bytes (always 32-bit BGRA, regardless of `flags`)
- **Storage:** LZSS-compressed (custom variant used by CAGE)
- **Color format:** BGRA (Blue, Green, Red, Alpha) — **not** standard RGBA
- **Compression:** Custom LZSS with 4KB sliding dictionary at offset 0xFEE

### GMS Metadata (Optional)

- Present only if `flags & 0x1000` is true.
- Contains additional game-specific metadata (font info, animation data, etc.).
- Also LZSS-compressed and XOR'd with 0xFF.
- **For PNG ↔ PGX conversion, GMS data is usually copied as-is from a template file.**

## LZSS Compression Details

The compression algorithm is a custom LZSS variant:

- **Dictionary size:** 0x1000 (4096 bytes)
- **Initial position:** 0xFEE (4078 bytes)
- **Match length:** 3–18 bytes (encoded as `(repetitions - 3)`)
- **Match offset:** 12 bits (0–4095)

### Compression Format

Compressed data is a series of **control bytes** (8 control bits per byte) followed by either:
- **Literal byte** (1 bit = 1 in control byte): next byte is copied as-is
- **Reference** (1 bit = 0 in control byte): next 2 bytes encode offset and length

```
Control byte format (bit 0 = first, bit 7 = last):
  Bit = 1: next byte is literal
  Bit = 0: next 2 bytes are [lo_offset | (length_code << 4)] [hi_offset_nibble]

Reference encoding:
  byte1: low 8 bits of offset
  byte2: (high 4 bits of offset << 4) | (length - 3)
  
Offset is calculated: offset = ((byte2 >> 4) << 8) | byte1
Length = (~byte2 & 0xF) + 3
```

### Example Decompression (from provided script)

```python
def custom_lzss_decompress(input_bytes, output_size):
    dict_size = 0x1000
    dict_pos = 0xFEE
    dict = bytearray(dict_size)
    output_buffer = bytearray(output_size)
    output_ptr = 0
    control = 0
    input_pos = 0

    while output_ptr < output_size:
        control >>= 1
        if not (control & 0x100):
            control = input_bytes[input_pos] | 0xFF00
            input_pos += 1
        
        if control & 1:
            # Literal byte
            byte = input_bytes[input_pos]
            dict[dict_pos] = output_buffer[output_ptr] = byte
            output_ptr += 1
            dict_pos = (dict_pos + 1) % dict_size
            input_pos += 1
        else:
            # Reference
            tmp1 = input_bytes[input_pos]
            tmp2 = input_bytes[input_pos + 1]
            input_pos += 2
            look_behind_pos = (((tmp2 & 0xF0) << 4) | tmp1) % dict_size
            repetitions = (~tmp2 & 0xF) + 3
            for _ in range(repetitions):
                dict[dict_pos] = output_buffer[output_ptr] = dict[look_behind_pos]
                output_ptr += 1
                dict_pos = (dict_pos + 1) % dict_size
                look_behind_pos = (look_behind_pos + 1) % dict_size
    
    return output_buffer
```

## PNG → PGX Conversion Process

### Step 1: Prepare Your PNG Image

- **Dimensions:** Must match or be resized to match the original PGX file.
- **Color mode:** RGBA, RGB, or L (grayscale). The script will convert to BGRA automatically.
- **Transparency:** Preserved in BGRA format (alpha channel).

### Step 2: Get a Template PGX File

To convert PNG → PGX, you **must have a template PGX file** of the same dimensions:
- The template provides the correct header structure.
- GMS metadata (if present) is copied from the template.
- Only the pixel data is replaced.

**Why a template?**
- PGX headers contain image dimensions, flags, and metadata pointers.
- It's simpler and safer to preserve these from an original file than to guess correct values.

### Step 3: Run the Conversion Script

#### Using `PGX_Conv.py` (provided)

```bash
# Extract PGX to PNG (you likely already did this)
python PGX_Conv.py extract <input_pgx_folder> <output_png_folder>

# Convert PNG back to PGX (requires template)
python PGX_Conv.py convert <input_png_folder> <output_pgx_folder> <template_pgx_file>
```

#### Using the Enhanced `PGX_Reverse_Conv.py` (recommended)

The enhanced script (`PGX_Reverse_Conv.py`) includes:
- **Better error handling** and logging.
- **Batch mode** for converting multiple PNG files at once.
- **Smart template selection** if folder has multiple templates.
- **Validation** to ensure PNG dimensions match template.

```bash
# Convert a single PNG to PGX using one template
python PGX_Reverse_Conv.py convert_single <input_png> <output_pgx> <template_pgx>

# Convert all PNGs in a folder using templates from another folder
python PGX_Reverse_Conv.py convert_batch <png_folder> <pgx_output> <template_folder>

# Repack a zip archive containing converted PGX files
python PGX_Reverse_Conv.py repack_zip <pgx_folder> <output_zip>

# Extract AND convert in one go (roundtrip test)
python PGX_Reverse_Conv.py roundtrip <original_pgx_folder> <output_pgx_folder>
```

## Complete Workflow Example

### Scenario: Replace UI images in Punipuni

1. **Extract original PGX files:**
   ```bash
   unzip c08d1.g.zip -d c08d1_extracted
   python PGX_Conv.py extract c08d1_extracted/PT/FRM extracted_png
   ```

2. **Edit PNG images in an image editor** (Photoshop, GIMP, etc.)
   - **Important:** Keep the same dimensions as originals!
   - Save as PNG with transparency if original had alpha channel.

3. **Convert edited PNGs back to PGX:**
   ```bash
   python PGX_Reverse_Conv.py convert_batch edited_png pgx_output c08d1_extracted/PT/FRM
   ```

4. **Repack into zip:**
   ```bash
   python PGX_Reverse_Conv.py repack_zip pgx_output c08d1_modified.g.zip
   ```

5. **Test in game:**
   - Replace `c08d1.g` in the game folder with your modified zip.
   - Run `punipuni_CHS.exe` and verify the images display correctly.

## Detailed Tool Usage

### `PGX_Conv.py` (Original Tool)

**Extract (PGX → PNG):**
```bash
python PGX_Conv.py extract <input_folder_with_pgx> <output_folder>
```
- Reads all `.PGX` files from `input_folder`.
- Decompresses and converts to PNG.
- Outputs to `output_folder`.

**Convert (PNG → PGX):**
```bash
python PGX_Conv.py convert <input_folder_with_png> <output_folder> <template_pgx_file>
```
- Reads all `.PNG` files from `input_folder`.
- Uses `template_pgx_file` as a header/metadata source.
- Compresses and writes PGX files to `output_folder`.

**Important:** The template PGX **must have the same dimensions** as the PNG being converted!

### `PGX_Reverse_Conv.py` (Enhanced Tool, Recommended)

See section below for full details.

## Enhanced Reverse Conversion Script: `PGX_Reverse_Conv.py`

This improved script adds convenience features:

### Key Features

1. **Single File Conversion**
   ```bash
   python PGX_Reverse_Conv.py convert_single edited.png output.pgx template.pgx
   ```

2. **Batch Conversion**
   ```bash
   python PGX_Reverse_Conv.py convert_batch png_folder/ pgx_output/ pgx_templates/
   ```
   - Automatically matches PNG files to templates by name or dimension.
   - Converts all PNGs in a batch operation.

3. **Dimension Validation**
   - Checks if PNG matches template dimensions.
   - Warns if they don't match; allows override with `--resize` flag.
   - Prevents common errors from mismatched image sizes.

4. **Zip Repacking**
   ```bash
   python PGX_Reverse_Conv.py repack_zip pgx_folder/ output.zip
   ```
   - Automatically preserves directory structure.
   - Creates a new zip matching the original format.

5. **Roundtrip Testing**
   ```bash
   python PGX_Reverse_Conv.py roundtrip original_pgx/ test_output/
   ```
   - Extract PGX → PNG → PGX in one command.
   - Useful for validating that compression/decompression is lossless.

## Troubleshooting

### Error: "Incorrect compressed image data size"

**Cause:** The template PGX header's `packed_size` field doesn't match actual compressed data.

**Solution:**
- Use a different, verified template PGX file.
- Manually check the template file structure.

### PNG Dimensions Don't Match Template

**Error:** "Image dimensions mismatch: template is X×Y, PNG is A×B"

**Solution:**
- Resize your PNG to match the template dimensions.
- OR use a template file with matching dimensions.
- OR use `PGX_Reverse_Conv.py convert_single --resize` to auto-resize (not recommended; may distort image).

### Game Shows Corrupted Images After Replacement

**Possible causes:**
1. Compression/decompression mismatch (LZSS algorithm differences).
2. Header not correctly updated with new `packed_size`.
3. GMS metadata corrupted or misaligned.

**Solutions:**
1. Verify the converted PGX file is roughly the same size as original.
2. Try extracting the converted PGX and comparing decompressed data.
3. Ensure no GMS metadata is present if converting from a template without GMS.

### LZSS Compression Produces Different Size Than Original

**Cause:** LZSS compression is **not deterministic**. Different compressions of the same data can produce different sizes.

**Is this a problem?** No! As long as:
- Decompressed data is identical.
- The `packed_size` header field is correctly updated.
- The file structure is correct.

The game will read and display the image correctly.

## File Correlations: PGX ↔ Font Tools

Interestingly, the **PGX format parallels the font tool approach** used in `HanziReplacer.py`:

| Aspect | Font Tools | PGX Format |
|--------|-----------|-----------|
| **Binary compression** | Font glyph data (otfcc) | LZSS-compressed pixels |
| **Header metadata** | Font name, metrics | Image dimensions, flags |
| **Template approach** | Base font + char mappings | Base PGX + pixel replacement |
| **Character remapping** | Source → Target codepoint mapping | Source → Compressed data |
| **Batch automation** | `gen_transdict.py`, `HanziReplacer.ChangeFont()` | `PGX_Reverse_Conv.py` batch mode |

**Key insight:** Both systems use a **template + replacement strategy** rather than rebuilding from scratch. This is why you need a template PGX file for conversion—just as font tools use a base font to build custom glyphs.

## Advanced: Building PGX Files Without a Template

If you need to create a PGX file **without a template**, you must manually construct the header:

```python
import struct

def create_pgx_header(width, height, has_alpha=True, has_gms=False):
    header = bytearray(20)
    struct.pack_into('<I', header, 0, 0)  # Magic (usually 0)
    struct.pack_into('<I', header, 4, width)
    struct.pack_into('<I', header, 8, height)
    flags = 0x0001 if has_alpha else 0x0000  # Bit 0 for 32-bit
    if has_gms:
        flags |= 0x1000
    struct.pack_into('<H', header, 12, flags)
    struct.pack_into('<H', header, 14, 0)  # Reserved
    # packed_size will be updated after compression
    struct.pack_into('<I', header, 16, 0)  # Placeholder
    return header
```

Then:
1. Create the header with `create_pgx_header()`.
2. Compress pixel data using `custom_lzss_compress()`.
3. Write header + compressed data to file.
4. Update `packed_size` in the header with the actual compressed size.

**However**, this is error-prone. **Using a template is strongly recommended.**

## Tools Summary

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `PGX_Conv.py extract` | PGX → PNG | PGX files | PNG files |
| `PGX_Conv.py convert` | PNG → PGX (template-based) | PNG + template PGX | PGX files |
| `PGX_Reverse_Conv.py` | Enhanced reverse conversion | PNG + templates or batch ops | PGX files / ZIP |

## References

- **LZSS Compression:** https://en.wikipedia.org/wiki/Lempel%E2%80%93Ziv%E2%80%93Storer%E2%80%93Szymanski
- **PGX Converter Source:** `PGX_Conv.py` (provided)
- **Font Integration Tools:** `HanziReplacer.py`, `otfccdump.exe`, `otfccbuild.exe`

---

**Last updated:** December 2025  
**Format reverse-engineered from:** CAGE engine (Punipuni / 大好きな先生にH)  
**Related tools:** `HanziReplacer.py` (font remapping using similar template-replacement approach)
