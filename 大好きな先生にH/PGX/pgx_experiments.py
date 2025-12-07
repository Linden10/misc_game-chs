#!/usr/bin/env python3
"""PGX experimentation helper

Creates variants of a converted PGX by altering header fields so you can
test how the game responds (packed_size, truncation, etc.).

Usage (examples):
  python pgx_experiments.py --orig HUTSU_output.pgx --conv test_roundtrip/HUTSU_round_template.pgx

This will produce a few files in the same folder named with suffixes:
  *_packed_orig.pgx    -> sets packed_size to the original PGX's packed_size
  *_trunc_to_orig.pgx  -> truncates the compressed payload to the original packed_size

Be careful: truncation may make the file unreadable by the extractor. Use the game to test alignment.
"""

import argparse
import struct
from pathlib import Path


def read_packed_size(pgx_path):
    data = open(pgx_path, 'rb').read()
    return struct.unpack('<I', data[20:24])[0]


def write_packed_size_to_copy(src_path, dst_path, new_packed):
    data = bytearray(open(src_path, 'rb').read())
    data[20:24] = struct.pack('<I', new_packed)
    open(dst_path, 'wb').write(data)


def truncate_compressed_to(src_path, dst_path, new_packed):
    data = open(src_path, 'rb').read()
    orig_packed = struct.unpack('<I', data[20:24])[0]
    data_start = len(data) - orig_packed
    header = data[:data_start]
    comp = data[data_start:]
    if new_packed > len(comp):
        raise ValueError('new_packed larger than current compressed length')
    new_comp = comp[:new_packed]
    out = bytearray()
    out.extend(header)
    out.extend(new_comp)
    # update packed_size in header (offset 20)
    out[20:24] = struct.pack('<I', new_packed)
    open(dst_path, 'wb').write(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--orig', required=True, help='Path to original working PGX (to copy packed_size)')
    p.add_argument('--conv', required=True, help='Path to converted PGX to mutate')
    args = p.parse_args()

    orig = Path(args.orig)
    conv = Path(args.conv)
    if not orig.exists() or not conv.exists():
        print('orig or conv file not found')
        return

    orig_packed = read_packed_size(orig)
    conv_packed = read_packed_size(conv)
    print('orig_packed=', orig_packed, 'conv_packed=', conv_packed)

    out_dir = conv.parent
    name = conv.stem

    # 1) copy conv and set packed_size to original packed
    dst1 = out_dir / f"{name}_packed_orig.pgx"
    write_packed_size_to_copy(conv, dst1, orig_packed)
    print('Wrote', dst1)

    # 2) truncate compressed payload to original packed size
    dst2 = out_dir / f"{name}_trunc_to_orig.pgx"
    try:
        truncate_compressed_to(conv, dst2, orig_packed)
        print('Wrote', dst2)
    except Exception as e:
        print('Could not truncate:', e)

    # 3) produce a file that sets packed_size to 0 (edge test)
    dst3 = out_dir / f"{name}_packed_zero.pgx"
    write_packed_size_to_copy(conv, dst3, 0)
    print('Wrote', dst3)


if __name__ == '__main__':
    main()
