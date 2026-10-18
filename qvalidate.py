"""Validate an FTB Quests book against the content actually present in an instance.

usage: qvalidate.py [<instance_minecraft_dir> <vanilla_client_jar>]   (no arguments: the No-Tech instance found in Prism)
Prints one line per problem: <chapter> <quest-id> <title> :: <problem>
"""
import io
import json
import os
import re
import sys
import zipfile
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import find_pack  # noqa: E402
import snbt  # noqa: E402

if len(sys.argv) > 2:
    MC, VANILLA = sys.argv[1], sys.argv[2]
else:
    MC, VANILLA = os.path.join(find_pack.pick('notech', 'converted No-Tech instance'), 'minecraft'), find_pack.mc_jar()
reg = defaultdict(set)   # kind -> ids
tags = defaultdict(list)


def lenient(b):
    return json.loads(re.sub(r'(?m)^\s*//.*$', '', b.decode('utf-8', 'replace').lstrip('﻿')))


def rid(p, start, ext):
    """data/<ns>/<a>/<b>/x/y.json -> ns:x/y (start = index of path after the kind dirs)."""
    return p[1] + ':' + '/'.join(p[start:])[:-len(ext)]


def load(zf):
    for n in zf.namelist():
        if n.startswith('META-INF/jars/') and n.endswith('.jar'):
            try:
                load(zipfile.ZipFile(io.BytesIO(zf.read(n))))
            except Exception:
                pass
            continue
        p = n.split('/')
        if len(p) < 4:
            continue
        try:
            if p[0] == 'assets':
                if p[2] == 'models' and p[3] == 'item' and n.endswith('.json'):
                    reg['item'].add(rid(p, 4, '.json'))
                elif p[2] == 'textures' and n.endswith('.png'):
                    reg['texture'].add(rid(p, 3, '.png'))
                elif p[2] == 'lang' and p[3] == 'en_us.json':
                    for k in lenient(zf.read(n)):
                        kp = k.split('.')
                        if len(kp) == 3 and kp[0] in ('item', 'block', 'entity'):
                            reg['entity' if kp[0] == 'entity' else 'item'].add(kp[1] + ':' + kp[2])
            elif p[0] == 'data' and n.endswith('.json'):
                if p[2] == 'tags' and p[3] == 'items':
                    j = lenient(zf.read(n))
                    t = rid(p, 4, '.json')
                    if j.get('replace'):
                        tags[t] = []
                    tags[t] += [v['id'] if isinstance(v, dict) else v for v in j.get('values', [])]
                elif p[2] == 'advancements':
                    reg['advancement'].add(rid(p, 3, '.json'))
                elif p[2] == 'dimension':
                    reg['dimension'].add(rid(p, 3, '.json'))
                elif p[2] == 'worldgen' and p[3] in ('structure', 'biome'):
                    reg[p[3]].add(rid(p, 4, '.json'))
                elif p[2] == 'tags' and p[3] == 'worldgen' and len(p) > 5 and p[4] in ('structure', 'biome'):
                    reg[p[4] + '_tag'].add(rid(p, 5, '.json'))
        except Exception:
            pass


load(zipfile.ZipFile(VANILLA))
for f in os.listdir(os.path.join(MC, 'mods')):
    if f.endswith('.jar'):
        try:
            load(zipfile.ZipFile(os.path.join(MC, 'mods', f)))
        except Exception as e:
            print('ERR', f, e)
for d in ('config/paxi/datapacks', 'config/paxi/resourcepacks', 'resourcepacks'):
    for f in os.listdir(os.path.join(MC, d)):
        if f.endswith('.zip'):
            try:
                load(zipfile.ZipFile(os.path.join(MC, d, f)))
            except Exception:
                pass
reg['dimension'] |= {'minecraft:overworld', 'minecraft:the_nether', 'minecraft:the_end'}
reg['entity'].add('minecraft:player')
# ftbquests / itemfilters register their own items (custom_icon, tag filters, loot crates, ...)
VIRTUAL = re.compile(r'^(ftbquests|itemfilters|ftblibrary):')


def tag_items(t, seen=()):
    out = set()
    for e in tags.get(t, []):
        if e.startswith('#'):
            if e[1:] not in seen:
                out |= tag_items(e[1:], seen + (t,))
        elif e in reg['item'] or e.startswith('minecraft:'):
            out.add(e)
    return out


QD = os.path.join(MC, 'config', 'ftbquests', 'quests')
chapters = {f[:-5]: snbt.loads(open(os.path.join(QD, 'chapters', f), encoding='utf-8').read())
            for f in os.listdir(os.path.join(QD, 'chapters'))}
groups = {g['id'] for g in snbt.loads(open(os.path.join(QD, 'chapter_groups.snbt'), encoding='utf-8').read())['chapter_groups']}
reward_tables = set()
for f in os.listdir(os.path.join(QD, 'reward_tables')):
    rt = snbt.loads(open(os.path.join(QD, 'reward_tables', f), encoding='utf-8').read())
    reward_tables.add(rt.get('id'))
all_ids = {q['id'] for ch in chapters.values() for q in ch.get('quests', [])}
problems = []


def item_ok(stack, where):
    if isinstance(stack, str):
        iid, tag = stack, {}
    elif isinstance(stack, dict):
        iid, tag = stack.get('id', ''), stack.get('tag', {})
    else:
        return
    if not iid or iid == 'minecraft:air':
        return
    if iid == 'itemfilters:tag':
        t = tag.get('value', '')
        if not tag_items(t):
            problems.append((where, f'item tag filter #{t} matches no existing item'))
        return
    if iid in ('itemfilters:or', 'itemfilters:and'):
        for s in tag.get('items', []):
            item_ok(s, where)
        return
    if VIRTUAL.match(iid):
        return
    if iid not in reg['item'] and not (iid.startswith('minecraft:') and iid in reg['item']):
        problems.append((where, f'unknown item {iid}'))


for cn, ch in chapters.items():
    if ch.get('group') and ch['group'] not in groups:
        problems.append((f'{cn} (chapter)', f'unknown chapter group {ch["group"]}'))
    if ch.get('icon'):
        item_ok(ch['icon'], f'{cn} (chapter icon)')
    for im in ch.get('images', []):
        img = im.get('image', '')
        if img.endswith('.png'):  # "ns:textures/x.png" and "ns:x" both name the same texture
            img = img.split(':')[0] + ':' + img.split(':', 1)[1][:-4].removeprefix('textures/')
        if ':' in img and img not in reg['texture'] and not img.startswith('ftbquests:'):
            problems.append((f'{cn} (image)', f'missing texture {img}'))
        if im.get('dependency') and im['dependency'] not in all_ids:
            problems.append((f'{cn} (image)', f'image depends on unknown quest {im["dependency"]}'))
    for ql in ch.get('quest_links', []):
        if ql.get('linked_quest') not in all_ids:
            problems.append((f'{cn} (quest link)', f'links to unknown quest {ql.get("linked_quest")}'))
    for q in ch.get('quests', []):
        w = f'{cn} {q["id"]} {q.get("title", "")!r}'
        for d in q.get('dependencies', []):
            if d not in all_ids:
                problems.append((w, f'unknown dependency {d}'))
        if 'icon' in q:
            item_ok(q['icon'], w + ' [icon]')
        if not q.get('tasks'):
            problems.append((w, 'quest has no tasks'))
        for t in q.get('tasks', []):
            ty = t.get('type')
            if 'icon' in t:
                item_ok(t['icon'], w + ' [task icon]')
            if ty == 'item':
                item_ok(t.get('item'), w + ' [task]')
            elif ty == 'kill' and t.get('entity') not in reg['entity']:
                problems.append((w, f'unknown entity {t.get("entity")}'))
            elif ty == 'dimension' and t.get('dimension') not in reg['dimension']:
                problems.append((w, f'unknown dimension {t.get("dimension")}'))
            elif ty == 'structure':
                s = t.get('structure', '')
                if (s[1:] not in reg['structure_tag']) if s.startswith('#') else (s not in reg['structure']):
                    problems.append((w, f'unknown structure {s}'))
            elif ty == 'biome':
                b = t.get('biome', '')
                if (b[1:] not in reg['biome_tag']) if b.startswith('#') else (b not in reg['biome']):
                    problems.append((w, f'unknown biome {b}'))
            elif ty == 'advancement' and t.get('advancement') not in reg['advancement']:
                problems.append((w, f'unknown advancement {t.get("advancement")}'))
        for r in q.get('rewards', []):
            ty = r.get('type')
            if ty == 'item':
                item_ok(r.get('item'), w + ' [reward]')
            elif ty in ('loot', 'random', 'choice') and r.get('table_id') is not None:
                pass
            elif ty == 'command':
                for tok in re.findall(r'\b([a-z0-9_.\-]+:[a-z0-9_./\-]+)', r.get('command', '')):
                    if tok.split(':')[0] not in ('minecraft',) and tok not in reg['item'] and tok not in reg['entity'] \
                            and tok not in reg['advancement'] and tok not in reg['dimension']:
                        problems.append((w, f'command reward references unknown id {tok}'))
# dependency cycles
graph = {q['id']: q.get('dependencies', []) for ch in chapters.values() for q in ch.get('quests', [])}
state = {}


def dfs(n, path):
    state[n] = 1
    for d in graph.get(n, []):
        if state.get(d) == 1:
            problems.append((n, f'dependency cycle via {d}'))
        elif d in graph and not state.get(d):
            dfs(d, path + [d])
    state[n] = 2


for n in graph:
    if not state.get(n):
        dfs(n, [n])
for w, p in sorted(set(problems)):
    print(f'{w} :: {p}')
print(f'-- {len(chapters)} chapters, {len(all_ids)} quests, {len(set(problems))} problems')
