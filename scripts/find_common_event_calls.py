#!/usr/bin/env python3
import json, os, sys

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'Moonflower Princess Debug', 'data')

def walk(obj, path=[]):
    if isinstance(obj, dict):
        yield (path, obj)
        for k,v in obj.items():
            yield from walk(v, path+[str(k)])
    elif isinstance(obj, list):
        for i,v in enumerate(obj):
            yield from walk(v, path+[str(i)])

def scan_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR loading {path}: {e}")
        return
    results = []
    for p, node in walk(data):
        if isinstance(node, dict) and node.get('code') == 117:
            params = node.get('parameters', [])
            if params and isinstance(params, list):
                for v in params:
                    if v == 243 or v == 244:
                        results.append((p, node))
    # also look for switch set commands (code 121 usually sets switches in MZ)
    switch_hits = []
    for p,node in walk(data):
        if isinstance(node, dict) and node.get('code') == 121:
            params = node.get('parameters', [])
            # parameters for code 121 in many exports are [switchId, switchId, value]
            if isinstance(params, list) and len(params) >= 3:
                sid = params[0]
                if sid in (241,):
                    switch_hits.append((p,node))
    if results or switch_hits:
        print(f"File: {path}")
        for p,n in results:
            print('  CALL_COMMON_EVENT at', '->'.join(p), 'params=', n.get('parameters'))
        for p,n in switch_hits:
            print('  SWITCH_CMD at', '->'.join(p), 'code=', n.get('code'), 'params=', n.get('parameters'))

def main():
    for root,_,files in os.walk(DATA_DIR):
        for fn in files:
            if not fn.endswith('.json'): continue
            scan_file(os.path.join(root, fn))

if __name__ == '__main__':
    main()
