#!/usr/bin/env python3
"""Extract JSON-like fragments containing a session id from a large NDJSON file.

Usage: python3 scripts/extract_session_fragments.py <ndjson_file> <session_id>

Writes results to `matches/recovered_fragments/`:
 - raw_N.json : raw extracted substring
 - parsed.json : list of successfully parsed JSON objects
"""
import sys
import os
import json


def extract_json_at(text, idx, max_back=2000, max_forward=200000):
    # Find a '{' before idx within max_back
    start = None
    s = max(0, idx - max_back)
    for i in range(idx, s - 1, -1):
        if text[i] == '{':
            start = i
            break
    if start is None:
        return None

    # Scan forward balanced braces, aware of strings/escapes
    depth = 0
    in_str = False
    esc = False
    for j in range(start, min(len(text), start + max_forward)):
        ch = text[j]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:j+1]
    return None


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    ndjson_path = sys.argv[1]
    session_id = sys.argv[2]

    out_dir = os.path.join('matches', 'recovered_fragments')
    os.makedirs(out_dir, exist_ok=True)

    text = None
    with open(ndjson_path, 'r', errors='replace') as f:
        text = f.read()

    hits = []
    idx = 0
    while True:
        idx = text.find(session_id, idx)
        if idx == -1:
            break
        hits.append(idx)
        idx += len(session_id)

    print(f"Found {len(hits)} occurrences of session id")

    parsed = []
    raw_count = 0
    for k, pos in enumerate(hits):
        frag = extract_json_at(text, pos)
        if not frag:
            continue
        raw_path = os.path.join(out_dir, f"raw_{k}.json")
        with open(raw_path, 'w', encoding='utf8') as rf:
            rf.write(frag)
        raw_count += 1
        try:
            obj = json.loads(frag)
            parsed.append(obj)
        except Exception:
            # Try a tolerant fix: replace lone \x with \u00 (best-effort)
            try:
                fixed = frag.replace('\\x', '\\u00')
                obj = json.loads(fixed)
                parsed.append(obj)
            except Exception:
                # Save as unparsed raw
                pass

    parsed_path = os.path.join(out_dir, 'parsed.json')
    with open(parsed_path, 'w', encoding='utf8') as pf:
        json.dump(parsed, pf, ensure_ascii=False, indent=2)

    print(f"Wrote {raw_count} raw fragments and {len(parsed)} parsed objects to {out_dir}")


if __name__ == '__main__':
    main()
