"""Compare two instances (original vs modified): recipes, tags, item obtainability via recipes.

usage: recipeverify.py [<orig_minecraft_dir> <new_minecraft_dir> [report.json]]   (no arguments: both found in Prism)
Each world = mod jars (incl. nested) + Paxi datapacks (zips), datapacks overriding same-path mod files.
Vanilla recipes are not indexed, so minecraft:* outputs are ignored.
"""
import io
import json
import os
import re
import sys
import zipfile
from collections import defaultdict

OUTKEYS = {'result', 'results', 'output', 'outputs', 'output_item'}
ALLOF = {'ingredients', 'inputs', 'input_items', 'items'}


def lenient(b):
    s = b.decode('utf-8', 'replace').lstrip('﻿')
    s = re.sub(r'(?m)^\s*//.*$', '', s)
    return json.loads(s)


class World:
    def __init__(self, mc):
        self.items = set()
        self.tags = defaultdict(list)
        self.recipes = {}          # path -> (source, json)
        self.loaded = set()
        mods = os.path.join(mc, 'mods')
        for f in sorted(os.listdir(mods)):
            if f.endswith('.jar'):
                try:
                    self.load(zipfile.ZipFile(os.path.join(mods, f)), f, False)
                except Exception as e:
                    print('ERR', f, e)
        dp = os.path.join(mc, 'config', 'paxi', 'datapacks')
        for f in sorted(os.listdir(dp)):
            p = os.path.join(dp, f)
            if f.endswith('.zip'):
                self.load(zipfile.ZipFile(p), 'dp:' + f, True)
        self.cache = {}

    def load(self, zf, src, is_dp):
        if not is_dp:
            try:
                self.loaded.add(json.loads(zf.read('fabric.mod.json').decode('utf-8', 'replace').replace('\n', ' '))['id'])
            except Exception:
                pass
        for n in zf.namelist():
            if n.startswith('META-INF/jars/') and n.endswith('.jar'):
                try:
                    self.load(zipfile.ZipFile(io.BytesIO(zf.read(n))), src, False)
                except Exception:
                    pass
                continue
            p = n.split('/')
            try:
                if n.startswith('assets/') and len(p) >= 5 and p[2] == 'models' and p[3] == 'item' and n.endswith('.json'):
                    self.items.add(p[1] + ':' + '/'.join(p[4:])[:-5])
                elif n.startswith('assets/') and n.endswith('/lang/en_us.json'):
                    for k in lenient(zf.read(n)):
                        kp = k.split('.')
                        if len(kp) == 3 and kp[0] in ('item', 'block'):
                            self.items.add(kp[1] + ':' + kp[2])
                elif n.startswith('data/') and len(p) >= 5 and p[2] == 'tags' and p[3] == 'items' and n.endswith('.json'):
                    j = lenient(zf.read(n))
                    tag = p[1] + ':' + '/'.join(p[4:])[:-5]
                    if j.get('replace'):
                        self.tags[tag] = []
                    for v in j.get('values', []):
                        self.tags[tag].append((v.get('id'), v.get('required', True)) if isinstance(v, dict) else (v, True))
                elif n.startswith('data/') and len(p) >= 4 and p[2] == 'recipes' and n.endswith('.json'):
                    if is_dp or n not in self.recipes or not self.recipes[n][0].startswith('dp:'):
                        self.recipes[n] = (src, lenient(zf.read(n)))
            except Exception:
                pass

    def has(self, i):
        return i in self.items or i.startswith('minecraft:')

    def tag(self, t, stack=()):
        if t in self.cache:
            return self.cache[t]
        if t in stack:
            return set()
        res, broken = set(), False
        for e, req in self.tags.get(t, []):
            if not e:
                continue
            if e.startswith('#'):
                sub = self.tag(e[1:], stack + (t,))
                if sub is None:
                    broken |= req
                else:
                    res |= sub
            elif self.has(e):
                res.add(e)
            elif req:
                broken = True
        self.cache[t] = None if broken else res
        return self.cache[t]

    def cond_ok(self, j):
        conds = j.get('fabric:load_conditions') or j.get('conditions') or []
        conds = [conds] if isinstance(conds, dict) else conds

        def ev(c):
            ty = c.get('condition') or c.get('type') or ''
            vals = c.get('values') or ([c['modid']] if 'modid' in c else [])
            if ty.endswith('all_mods_loaded') or ty.endswith('mod_loaded'):
                return all(v in self.loaded for v in vals)
            if ty.endswith('any_mods_loaded'):
                return any(v in self.loaded for v in vals)
            if ty.endswith(':not'):
                return not ev(c.get('value', {}))
            if ty.endswith(':and'):
                return all(ev(x) for x in c.get('values', []))
            if ty.endswith(':or'):
                return any(ev(x) for x in c.get('values', []))
            return True
        return all(ev(c) for c in conds if isinstance(c, dict))

    def sat(self, node, miss, parent=None):
        if isinstance(node, dict):
            if 'item' in node and isinstance(node['item'], str) and len(node) <= 4:
                ok = self.has(node['item'])
                if not ok:
                    miss.add(node['item'])
                return ok
            if 'tag' in node and isinstance(node['tag'], str):
                m = self.tag(node['tag'])
                ok = bool(m) or (node['tag'].startswith('minecraft:') and m is not None)
                if not ok:
                    miss.add('#' + node['tag'] + (' (broken)' if m is None else ' (empty)'))
                return ok
            if 'fluid' in node:
                return True
            return all(self.sat(v, miss, k) for k, v in node.items() if k not in OUTKEYS and k != 'fabric:load_conditions')
        if isinstance(node, list):
            if parent in ALLOF or parent == 'key':
                return all(self.sat(v, miss) for v in node)
            if node and not any(self.sat(v, set()) for v in node):
                self.sat(node[0], miss)
                return False
        return True

    def evaluate(self):
        res = {}
        for path, (src, j) in self.recipes.items():
            if not isinstance(j, dict) or not self.cond_ok(j):
                continue
            miss = set()
            ok = self.sat({k: v for k, v in j.items() if k not in OUTKEYS}, miss)
            rtype = str(j.get('type', ''))
            if ':' in rtype and rtype.split(':')[0] not in self.loaded | {'minecraft', 'c'}:
                ok = False
                miss.add('unknown recipe type ' + rtype)
            outs = []
            for k in OUTKEYS:
                v = j.get(k)
                for x in (v if isinstance(v, list) else [v]):
                    i = x if isinstance(x, str) else (x.get('item') or x.get('id')) if isinstance(x, dict) else None
                    if isinstance(i, str):
                        outs.append(i)
            res[path] = (ok, outs, sorted(miss), src)
        return res


def main():
    if len(sys.argv) > 2:
        a, b = World(sys.argv[1]), World(sys.argv[2])
    else:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import find_pack
        a = World(os.path.join(find_pack.pick('original', 'unconverted Prominence II instance'), 'minecraft'))
        b = World(os.path.join(find_pack.pick('notech', 'converted No-Tech instance'), 'minecraft'))
    ra, rb = a.evaluate(), b.evaluate()
    craft_b = defaultdict(int)
    for ok, outs, _, _ in rb.values():
        if ok:
            for o in outs:
                craft_b[o] += 1
    report = {'lost_items': [], 'newly_broken': [], 'broken_tags': [], 'new_recipes': []}
    print('recipes OK: original', sum(v[0] for v in ra.values()), '| modified', sum(v[0] for v in rb.values()))
    seen = set()
    for path, (ok, outs, _, src) in ra.items():
        if not ok:
            continue
        for o in outs:
            if o in seen or o.startswith('minecraft:') or not b.has(o) or craft_b.get(o):
                continue
            seen.add(o)
            report['lost_items'].append((o, path, src))
    for path, (ok, outs, miss, src) in rb.items():
        if not ok and ra.get(path, (False,))[0]:
            report['newly_broken'].append((path, src, outs, miss))
        if path not in ra and ok:
            report['new_recipes'].append((path, src, outs))
    for t in sorted(set(b.tags)):
        if b.tag(t) is None and a.tag(t) is not None:
            report['broken_tags'].append(t)
    for k, v in report.items():
        print(f'\n== {k}: {len(v)}')
        for x in v:
            print('  ', x)
    if len(sys.argv) > 3:
        json.dump(report, open(sys.argv[3], 'w'), indent=1)


if __name__ == '__main__':
    main()
