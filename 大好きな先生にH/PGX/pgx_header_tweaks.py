#!/usr/bin/env python3
"""Create small header-tweak variants that flip/modify a few unknown header bytes
while preserving width/height and packed_size. Then attempt extraction to verify
the file still decompresses. Use this to experiment with which header bytes affect
in-game alignment.
"""
import struct
from pathlib import Path
from shutil import copyfile


def tweak_bytes(src, dst, changes):
    data = bytearray(open(src,'rb').read())
    for off, new in changes.items():
        data[off] = new & 0xFF
    open(dst,'wb').write(data)


def read_packed_size(path):
    data = open(path,'rb').read()
    return struct.unpack('<I', data[20:24])[0]


def main():
    import sys
    if len(sys.argv) != 2:
        print('Usage: pgx_header_tweaks.py <pgx_path>')
        return
    src = Path(sys.argv[1])
    if not src.exists():
        print('File not found')
        return
    out_dir = src.parent
    base = src.stem

    orig_packed = read_packed_size(src)
    print('orig packed', orig_packed)

    # Define a set of tweaks to try (offset: new_byte)
    tweaks = [
        {4: 0x00},
        {4: 0xFF},
        {5: 0x00},
        {5: 0xFF},
        {6: 0x00},
        {6: 0xFF},
        {7: 0x00},
        {7: 0xFF},
        # small flag tweak at offset 16 (part of flags area)
        {16: 0x00},
        {16: 0xFF},
    ]

    created = []
    for i,chg in enumerate(tweaks):
        dst = out_dir / f"{base}_tweak_{i}.pgx"
        tweak_bytes(src, dst, chg)
        created.append(dst)
        print('Wrote', dst, 'changes', chg)

    print('\nCreated variants:')
    for p in created:
        print('  ', p)

if __name__ == '__main__':
    main()
