#!/usr/bin/env python3
"""Recompress a PNG using the original PGX_Conv compressor and assemble a PGX
using a template's header/GMS. This may produce a packed_size closer to the
original and help test engine alignment issues.
"""
import struct
from pathlib import Path

def png_to_bgra(path):
    from PIL import Image
    img = Image.open(path).convert('RGBA')
    pdata = bytearray(img.tobytes())
    bgra = bytearray()
    for i in range(0, len(pdata), 4):
        bgra.extend([pdata[i+2], pdata[i+1], pdata[i], pdata[i+3]])
    return bytes(bgra), img.width, img.height

def main():
    import sys
    if len(sys.argv) != 4:
        print('Usage: recompress_with_orig.py <png> <template_pgx> <out_pgx>')
        return
    png_path = Path(sys.argv[1])
    template = Path(sys.argv[2])
    out = Path(sys.argv[3])

    bgra, w, h = png_to_bgra(png_path)

    # import original compressor
    import importlib.util, os
    conv_path = Path(__file__).resolve().parent / 'PGX_Conv.py'
    spec = importlib.util.spec_from_file_location('pgxconv', str(conv_path))
    pgxconv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pgxconv)

    compressed = pgxconv.custom_lzss_compress(bgra, len(bgra))
    print('compressed len', len(compressed))

    # copy header+gms from template up to data_start
    tdata = open(template,'rb').read()
    packed_size = struct.unpack('<I', tdata[20:24])[0]
    data_start = len(tdata) - packed_size
    header_and_gms = tdata[:data_start]

    outb = bytearray()
    outb.extend(header_and_gms)
    outb.extend(compressed)
    # write packed_size
    outb[20:24] = struct.pack('<I', len(compressed))
    out.write_bytes(outb)
    print('Wrote', out)

if __name__ == '__main__':
    main()
