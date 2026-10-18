"""Diff ERROR/WARN signatures between two server logs. usage: logdiff.py <orig.log> <new.log>"""
import re
import sys
from collections import Counter

KEY = re.compile(r'(Couldn.t load tag|Parsing error loading recipe|Unknown registry|Missing|missing|not found|Failed|'
                 r'Exception|Unknown|Invalid|Error|error)')


def sigs(path, level):
    c = Counter()
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^\[[0-9:]+\] \[([^\]]+)/(ERROR|WARN)\]: (.*)', line)
        if not m or m.group(2) != level:
            continue
        msg = m.group(3)
        if level == 'WARN' and not KEY.search(msg):
            continue
        msg = re.sub(r'jar:file:[^ ]+', 'JAR', msg)
        msg = re.sub(r'@[0-9a-f]{5,}', '@X', msg)
        msg = re.sub(r'\b\d+(\.\d+)?\b', 'N', msg)
        c[msg[:220]] += 1
    return c


for level in ('ERROR', 'WARN'):
    a, b = sigs(sys.argv[1], level), sigs(sys.argv[2], level)
    print(f'===== {level}: original {sum(a.values())} lines / modified {sum(b.values())} lines')
    print(f'--- only in MODIFIED ({len(set(b) - set(a))}):')
    for k in sorted(set(b) - set(a)):
        print(f'  [{b[k]}] {k}')
    print(f'--- only in ORIGINAL ({len(set(a) - set(b))}):')
    for k in sorted(set(a) - set(b))[:60]:
        print(f'  [{a[k]}] {k}')
