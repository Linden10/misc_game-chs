#!/usr/bin/env python3
"""
Enhanced PGX Reverse Converter
Converts PNG images back to PGX format with template support.

Features:
- Single file conversion
- Batch mode with auto-matching
- Dimension validation
- Zip repacking
- Roundtrip testing (extract → convert back)

Usage:
    python PGX_Reverse_Conv.py convert_single <png> <output_pgx> <template_pgx>
    python PGX_Reverse_Conv.py convert_batch <png_folder> <pgx_output> <template_folder>
    python PGX_Reverse_Conv.py repack_zip <pgx_folder> <output_zip>
    python PGX_Reverse_Conv.py roundtrip <original_pgx_folder> <output_pgx_folder>
    
Options:
    --resize                          Auto-resize PNG to template dimensions when needed
    --anim                             Apply the known "animation" header tweak: copy template's byte at offset 4 (fallback 0xFF)
        --auto-anim                        Auto-detect animation header from template when batch-converting
    --tweak=<offset>:<val>            Apply a single-byte tweak to header at <offset> (decimal or 0xHEX)
"""

import os
import sys
import struct
import zipfile
import shutil
from pathlib import Path
from PIL import Image

class PGXConverter:
    """Enhanced PGX format converter with validation and batch processing."""
    
    @staticmethod
    def custom_lzss_decompress(input_bytes, output_size):
        """Decompress LZSS-compressed data (CAGE engine format)."""
        dict_size = 0x1000
        dict_pos = 0xFEE
        dict_data = bytearray(dict_size)
        output_buffer = bytearray(output_size)
        output_ptr = 0
        
        control = 0
        input_pos = 0
        
        try:
            while output_ptr < output_size:
                control >>= 1
                if not (control & 0x100):
                    control = input_bytes[input_pos] | 0xFF00
                    input_pos += 1
                
                if control & 1:
                    # Literal byte
                    byte = input_bytes[input_pos]
                    dict_data[dict_pos] = output_buffer[output_ptr] = byte
                    output_ptr += 1
                    dict_pos = (dict_pos + 1) % dict_size
                    input_pos += 1
                else:
                    # Reference (offset, length)
                    tmp1 = input_bytes[input_pos]
                    tmp2 = input_bytes[input_pos + 1]
                    input_pos += 2
                    look_behind_pos = (((tmp2 & 0xF0) << 4) | tmp1) % dict_size
                    repetitions = (~tmp2 & 0xF) + 3
                    
                    while repetitions > 0 and output_ptr < output_size:
                        dict_data[dict_pos] = output_buffer[output_ptr] = dict_data[look_behind_pos]
                        output_ptr += 1
                        dict_pos = (dict_pos + 1) % dict_size
                        look_behind_pos = (look_behind_pos + 1) % dict_size
                        repetitions -= 1
        except IndexError:
            raise EOFError("Unexpected end of compressed data")
        
        return output_buffer
    
    @staticmethod
    def custom_lzss_compress(input_bytes):
        """Compress data using LZSS (CAGE engine format) - matching the decompressor's control byte handling."""
        dict_size = 0x1000
        dict_pos = 0xFEE
        dict_data = bytearray(dict_size)
        dict_written = 0  # number of bytes written into the dict (grows until wrap)
        output_buffer = bytearray()

        input_pos = 0
        input_end = len(input_bytes)

        while input_pos < input_end:
            control_byte = 0x00
            operations = bytearray()

            for bit_pos in range(8):
                if input_pos >= input_end:
                    break

                # Find best match only among dictionary bytes that have been written
                best_match_pos = -1
                best_match_len = 0

                if dict_written > 0:
                    # iterate over valid written positions
                    max_check = min(dict_written, dict_size)
                    start_pos = (0xFEE) % dict_size
                    for k in range(max_check):
                        check_pos = (start_pos + k) % dict_size
                        match_len = 0
                        max_match = min(18, input_end - input_pos)
                        for i in range(max_match):
                            if input_bytes[input_pos + i] == dict_data[(check_pos + i) % dict_size]:
                                match_len += 1
                            else:
                                break
                        if match_len > best_match_len:
                            best_match_len = match_len
                            best_match_pos = check_pos

                if best_match_len >= 3:
                    # reference (bit = 0)
                    encoded_len = (18 - best_match_len) & 0x0F
                    byte1 = best_match_pos & 0xFF
                    byte2 = ((best_match_pos >> 8) << 4) | (encoded_len & 0x0F)
                    operations.append(byte1)
                    operations.append(byte2)

                    for _ in range(best_match_len):
                        dict_data[dict_pos] = input_bytes[input_pos]
                        dict_pos = (dict_pos + 1) % dict_size
                        dict_written = min(dict_written + 1, dict_size)
                        input_pos += 1
                else:
                    # literal (bit = 1)
                    control_byte |= (1 << bit_pos)
                    operations.append(input_bytes[input_pos])

                    dict_data[dict_pos] = input_bytes[input_pos]
                    dict_pos = (dict_pos + 1) % dict_size
                    dict_written = min(dict_written + 1, dict_size)
                    input_pos += 1

            output_buffer.append(control_byte)
            output_buffer.extend(operations)

        return output_buffer

    @staticmethod
    def fake_lzss_compress(input_bytes):
        """Simple 'fake' LZSS compressor: emit a control byte followed by up to
        8 literal bytes. This produces streams the game's decompressor accepts
        and acts as a reliable compatibility fallback (larger but safe).
        """
        output = bytearray()
        n = len(input_bytes)
        pos = 0
        while pos < n:
            chunk = input_bytes[pos:pos+8]
            # control: bit set to 1 => literal for that sub-slot
            control = 0
            for i in range(len(chunk)):
                control |= (1 << i)
            output.append(control)
            output.extend(chunk)
            pos += len(chunk)
        return output
    
    @staticmethod
    def read_pgx_header(pgx_path):
        """Read and return PGX header information."""
        try:
            with open(pgx_path, 'rb') as f:
                # Read first 20 bytes (magic + width/height + flags + packed_size info)
                f.seek(0)
                header_20 = f.read(20)
                
                # Parse header: skip first 8 bytes (magic + unknown), read width/height
                width = struct.unpack('<I', header_20[8:12])[0]
                height = struct.unpack('<I', header_20[12:16])[0]
                flags = struct.unpack('<H', header_20[16:18])[0]
                
                # Read packed_size from offset 20
                f.seek(20)
                packed_size = struct.unpack('<I', f.read(4))[0]
                
                # Get file size to check format
                f.seek(0, 2)  # Seek to end
                file_size = f.tell()
                
                return {
                    'width': width,
                    'height': height,
                    'flags': flags,
                    'packed_size': packed_size,
                    'header_20': header_20,
                    'file_size': file_size
                }
        except Exception as e:
            print(f"✗ Error reading PGX header from {pgx_path}: {e}")
            raise
    
    @staticmethod
    def png_to_bgra(png_path):
        """Convert PNG to BGRA pixel data (4 bytes per pixel)."""
        try:
            img = Image.open(png_path)
            
            # Convert to RGBA if needed
            if img.mode == 'RGB':
                img = img.convert('RGBA')
            elif img.mode not in ('RGBA', 'L', 'P'):
                img = img.convert('RGBA')
            
            if img.mode == 'L':
                # Grayscale to RGBA
                img = img.convert('RGBA')
            elif img.mode == 'P':
                # Palette to RGBA
                img = img.convert('RGBA')
            
            pixel_data = bytearray(img.tobytes())
            
            # Convert RGBA to BGRA
            bgra_data = bytearray()
            for i in range(0, len(pixel_data), 4):
                bgra_data.extend([
                    pixel_data[i+2],  # B (from R)
                    pixel_data[i+1],  # G
                    pixel_data[i+0],  # R (from B)
                    pixel_data[i+3]   # A
                ])
            
            return bgra_data, (img.width, img.height)
        except Exception as e:
            print(f"✗ Error converting PNG {png_path} to BGRA: {e}")
            raise
    
    @staticmethod
    def convert_png_to_pgx(png_path, template_pgx_path, output_pgx_path, allow_resize=False):
        """Convert PNG to PGX using a template file."""
        try:
            # Read template header
            template_info = PGXConverter.read_pgx_header(template_pgx_path)
            template_width = template_info['width']
            template_height = template_info['height']
            template_packed_size = template_info['packed_size']
            
            # Read and convert PNG
            bgra_data, (png_width, png_height) = PGXConverter.png_to_bgra(png_path)
            
            # Check dimensions
            if png_width != template_width or png_height != template_height:
                if not allow_resize:
                    raise ValueError(
                        f"Dimension mismatch: PNG is {png_width}×{png_height}, "
                        f"template is {template_width}×{template_height}. "
                        f"Use --resize to auto-resize."
                    )
                else:
                    print(f"  ⚠ Resizing PNG from {png_width}×{png_height} to {template_width}×{template_height}")
                    img = Image.open(png_path).convert('RGBA')
                    img = img.resize((template_width, template_height), Image.Resampling.LANCZOS)
                    bgra_data, _ = PGXConverter.png_to_bgra_from_image(img)
            
            # Ensure data is exactly width * height * 4
            expected_size = template_width * template_height * 4
            if len(bgra_data) != expected_size:
                raise ValueError(
                    f"Pixel data size mismatch: expected {expected_size}, got {len(bgra_data)}"
                )
            
            # Compress pixel data. Use the "fake" LZSS compressor by default
            # because it reliably produces streams the game recognizes. If it
            # somehow fails, fall back to original compressors.
            try:
                compressed_data = PGXConverter.fake_lzss_compress(bytes(bgra_data))
                print("  ⚑ Using fake LZSS compressor (compatible fallback)")
            except Exception:
                try:
                    from PGX_Conv import custom_lzss_compress as orig_compress
                    compressed_data = orig_compress(bytes(bgra_data), len(bgra_data))
                except Exception:
                    compressed_data = PGXConverter.custom_lzss_compress(bytes(bgra_data))
            
            # Copy everything from template up to (but not including) compressed data
            # Find where compressed data starts in template
            with open(template_pgx_path, 'rb') as f:
                # Read up to where packed data should start
                # packed_size is at offset 20, so header + any GMS = file_size - packed_size
                f.seek(0, 2)
                file_size = f.tell()
                data_start = file_size - template_packed_size
                
                f.seek(0)
                header_and_gms = f.read(data_start)
            
            # Write new PGX file
            with open(output_pgx_path, 'wb+') as f:
                # Write header and GMS data (copy from template)
                f.seek(0)
                f.write(header_and_gms)

                # Write compressed pixel data
                f.write(compressed_data)

                # Update packed_size in header (at offset 20, 4 bytes)
                f.seek(20)
                f.write(struct.pack('<I', len(compressed_data)))

                # Apply any header tweaks specified (no-op if none).
                # Tweaks are written after packed_size so they overwrite header bytes
                # without disturbing the packed_size update.
                tweaks = []
                if hasattr(PGXConverter, '_pending_tweaks') and isinstance(PGXConverter._pending_tweaks, list):
                    tweaks = PGXConverter._pending_tweaks
                applied_anim = False
                for off, val in tweaks:
                    try:
                        f.seek(off)
                        f.write(bytes([val & 0xFF]))
                        # if this looks like the known anim tweak, record it
                        if off == 4 and (val & 0xFF) == 0xFF:
                            applied_anim = True
                    except Exception:
                        # ignore invalid offsets
                        pass
            
                # Final status - include anim note when applicable
                if 'applied_anim' in locals() and applied_anim:
                  print(f"  ✓ Converted (anim): {png_path} → {output_pgx_path} "
                      f"(compressed: {len(compressed_data)} bytes)")
                else:
                  print(f"  ✓ Converted: {png_path} → {output_pgx_path} "
                      f"(compressed: {len(compressed_data)} bytes)")

                # If we applied an offset-4 tweak (template copy), validate the
                # resulting PGX by attempting to extract it. If extraction
                # fails, try safe fallbacks (0x04 then 0xFF) to increase the
                # chance the engine will accept the file.
                if any(off == 4 for off, _ in tweaks):
                    try:
                        import subprocess, tempfile
                        def try_validate_and_set(byte_val):
                            # overwrite offset 4 with candidate and test extraction
                            f.seek(4)
                            f.write(bytes([byte_val & 0xFF]))
                            f.flush()
                            # attempt extraction via PGX_Conv.py if available
                            tmpd = tempfile.mkdtemp(prefix='pgx_check_')
                            prog = os.path.join(os.path.dirname(__file__), 'PGX_Conv.py')
                            ok = False
                            if os.path.isfile(prog):
                                try:
                                    subprocess.run(['python3', prog, 'extract', output_pgx_path, tmpd], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                    # success if any png produced
                                    ok = any(p.lower().endswith('.png') for p in os.listdir(tmpd))
                                except Exception:
                                    ok = False
                            else:
                                # If PGX_Conv not available, assume ok (cannot validate)
                                ok = True
                            try:
                                shutil.rmtree(tmpd)
                            except Exception:
                                pass
                            return ok

                        # Read back what we wrote earlier to determine initial candidate
                        f.flush()
                        f.seek(4)
                        orig_b = f.read(1)
                        initial = orig_b[0] if orig_b else 0xFF

                        valid = try_validate_and_set(initial)
                        if not valid:
                            # try a small set of fallbacks known to have worked
                            for cand in (0x04, 0xFF):
                                if cand == initial:
                                    continue
                                if try_validate_and_set(cand):
                                    print(f"  ⚑ Anim-tweak fallback: wrote 0x{cand:02X} after validation")
                                    valid = True
                                    break

                        if not valid:
                            print("  ⚠ Warning: anim header tweak caused invalid PGX; kept template value but file may be rejected by the game")
                    except Exception:
                        # best-effort validation — ignore failures in validation
                        pass
        except Exception as e:
            print(f"✗ Error converting {png_path} to {output_pgx_path}: {e}")
            raise
    
    @staticmethod
    def png_to_bgra_from_image(img):
        """Convert PIL Image object to BGRA pixel data."""
        if img.mode == 'RGB':
            img = img.convert('RGBA')
        elif img.mode not in ('RGBA', 'L', 'P'):
            img = img.convert('RGBA')
        
        pixel_data = bytearray(img.tobytes())
        
        # Convert RGBA to BGRA
        bgra_data = bytearray()
        for i in range(0, len(pixel_data), 4):
            bgra_data.extend([
                pixel_data[i+2],  # B (from R)
                pixel_data[i+1],  # G
                pixel_data[i+0],  # R (from B)
                pixel_data[i+3]   # A
            ])
        
        return bgra_data, (img.width, img.height)
    
    @staticmethod
    def convert_batch(png_folder, output_folder, template_folder, auto_anim=False, apply_anim=False):
        """Batch convert PNG files to PGX using templates."""
        try:
            os.makedirs(output_folder, exist_ok=True)
            
            png_files = list(Path(png_folder).rglob('*.png'))
            print(f"\nFound {len(png_files)} PNG files to convert.")
            
            if not png_files:
                print("⚠ No PNG files found in input folder.")
                return
            
            for png_path in png_files:
                # Find matching template
                template_path = Path(template_folder) / f"{png_path.stem}.pgx"
                
                if not template_path.exists():
                    # Try searching by dimensions
                    matching_templates = list(Path(template_folder).glob('*.pgx'))
                    if not matching_templates:
                        print(f"⚠ No template found for {png_path.name}")
                        continue
                    template_path = matching_templates[0]
                
                output_path = Path(output_folder) / f"{png_path.stem}.pgx"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    # If requested, auto-detect whether this template uses the
                    # animation header byte and set the corresponding tweak.
                    # Detection is conservative: only apply the anim tweak when
                    # the template's byte at offset 4 equals 0xFF.
                    # If user requested applying the anim tweak for all
                    # converted files, copy the template's offset-4 byte into
                    # the output (fallback to 0xFF if the template can't be read).
                    if apply_anim:
                        try:
                            with open(template_path, 'rb') as tf:
                                tf.seek(4)
                                b = tf.read(1)
                                val = 0xFF if not b else b[0]
                                PGXConverter._pending_tweaks = [(4, val)]
                        except Exception:
                            PGXConverter._pending_tweaks = [(4, 0xFF)]
                    else:
                        # Auto-detect mode: apply anim only when template byte == 0xFF
                        if auto_anim:
                            tweaks = []
                            try:
                                with open(template_path, 'rb') as tf:
                                    tf.seek(4)
                                    b = tf.read(1)
                                    if b and b[0] == 0xFF:
                                        tweaks.append((4, 0xFF))
                            except Exception:
                                tweaks = []
                            PGXConverter._pending_tweaks = tweaks

                    PGXConverter.convert_png_to_pgx(
                        str(png_path),
                        str(template_path),
                        str(output_path)
                    )

                    # Clear any per-file pending tweaks so they don't bleed
                    # into subsequent conversions.
                    if hasattr(PGXConverter, '_pending_tweaks'):
                        PGXConverter._pending_tweaks = []
                except Exception as e:
                    print(f"  ✗ Skipped: {e}")
            
            print(f"\n✓ Batch conversion complete. Output in: {output_folder}")
        except Exception as e:
            print(f"✗ Batch conversion failed: {e}")
            raise
    
    @staticmethod
    def repack_zip(pgx_folder, output_zip_path):
        """Repack PGX files back into a ZIP archive, preserving structure."""
        try:
            print(f"\nRepacking PGX files into {output_zip_path}...")
            
            with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_STORED) as zf:
                for root, dirs, files in os.walk(pgx_folder):
                    for file in files:
                        if file.lower().endswith('.pgx'):
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, pgx_folder)
                            zf.write(file_path, arcname)
                            print(f"  + {arcname}")
            
            print(f"✓ ZIP created: {output_zip_path}")
        except Exception as e:
            print(f"✗ ZIP repacking failed: {e}")
            raise

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == 'convert_single':
            if len(sys.argv) < 5:
                print("Usage: convert_single <png> <output_pgx> <template_pgx> [--resize] [--apply-tweak1] [--tweak=OFF:VAL]")
                sys.exit(1)
            png_path = sys.argv[2]
            output_pgx = sys.argv[3]
            template_pgx = sys.argv[4]
            allow_resize = '--resize' in sys.argv

            # Parse tweak flags
            tweaks = []
            # convenience flag to apply the animation tweak: copy template's
            # offset-4 byte (fallback to 0xFF)
            if '--anim' in sys.argv or '--apply-anim-tweak' in sys.argv or '--apply-tweak1' in sys.argv:
                try:
                    with open(template_pgx, 'rb') as tf:
                        tf.seek(4)
                        b = tf.read(1)
                        val = 0xFF if not b else b[0]
                        tweaks.append((4, val))
                except Exception:
                    tweaks.append((4, 0xFF))

            # --tweak=offset:val (can be repeated)
            for arg in sys.argv:
                if arg.startswith('--tweak='):
                    spec = arg.split('=', 1)[1]
                    if ':' in spec:
                        off_s, val_s = spec.split(':', 1)
                        try:
                            off = int(off_s, 0)
                            val = int(val_s, 0)
                            tweaks.append((off, val))
                        except Exception:
                            pass

            # attach tweaks to the class so convert function can apply them when writing
            PGXConverter._pending_tweaks = tweaks
            PGXConverter.convert_png_to_pgx(png_path, template_pgx, output_pgx, allow_resize)
            # clear pending tweaks
            PGXConverter._pending_tweaks = []
        
        elif command == 'convert_batch':
            if len(sys.argv) < 5:
                print("Usage: convert_batch <png_folder> <pgx_output> <template_folder> [--auto-anim] [--anim]")
                sys.exit(1)
            png_folder = sys.argv[2]
            output_folder = sys.argv[3]
            template_folder = sys.argv[4]
            auto_anim = '--auto-anim' in sys.argv
            apply_anim = '--anim' in sys.argv
            PGXConverter.convert_batch(png_folder, output_folder, template_folder, auto_anim, apply_anim)
        
        elif command == 'repack_zip':
            if len(sys.argv) < 4:
                print("Usage: repack_zip <pgx_folder> <output_zip>")
                sys.exit(1)
            pgx_folder = sys.argv[2]
            output_zip = sys.argv[3]
            PGXConverter.repack_zip(pgx_folder, output_zip)
        
        elif command == 'roundtrip':
            if len(sys.argv) < 4:
                print("Usage: roundtrip <original_pgx_folder> <output_pgx_folder>")
                sys.exit(1)
            original_folder = sys.argv[2]
            output_folder = sys.argv[3]
            
            # Extract to PNG
            temp_png = os.path.join(output_folder, "_temp_png")
            print(f"Phase 1: Extracting PGX → PNG to {temp_png}")
            os.makedirs(temp_png, exist_ok=True)
            
            from PGX_Conv import extract_pgx_files
            extract_pgx_files(original_folder, temp_png)
            
            # Convert back to PGX
            temp_pgx = os.path.join(output_folder, "_temp_pgx")
            print(f"\nPhase 2: Converting PNG → PGX to {temp_pgx}")
            PGXConverter.convert_batch(temp_png, temp_pgx, original_folder)
            
            # Repack to ZIP
            output_zip = os.path.join(output_folder, "roundtrip_result.zip")
            PGXConverter.repack_zip(temp_pgx, output_zip)
            
            print(f"\n✓ Roundtrip complete. Result: {output_zip}")
        
        else:
            print(f"Unknown command: {command}")
            print(__doc__)
            sys.exit(1)
    
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
