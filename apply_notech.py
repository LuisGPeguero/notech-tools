"""Apply the 'No Tech' conversion to a COPY of the Prominence II instance.

usage: apply_notech.py                  find the original in Prism, copy it to "(No Tech)" and convert the copy
       apply_notech.py <instance_root>  convert this (already copied) instance
Everything removed is moved (never deleted) into <instance_root>/removed_tech_mods/.
"""
import io
import json
import os
import re
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import find_pack  # noqa: E402
import snbt  # noqa: E402

if len(sys.argv) > 1:
    ROOT = sys.argv[1]
else:
    ORIG = find_pack.pick('original', 'unconverted Prominence II instance')
    ROOT = os.path.join(os.path.dirname(ORIG), find_pack.NOTECH_NAME)
    if os.path.exists(ROOT):
        sys.exit(f'{ROOT} already exists. Move its worlds out, delete it, then run this again.')
    print(f'Original:  {ORIG}\nCopy to:   {ROOT}\nThe copy gets converted; the original is not touched.')
    if input('Continue? [y/N] ').strip().lower() != 'y':
        sys.exit('Cancelled, nothing changed.')
    print('Copying (about a minute)...')
    shutil.copytree(ORIG, ROOT)
    ic = os.path.join(ROOT, 'instance.cfg')
    txt = re.sub(r'(?m)^name=.*$', 'name=' + find_pack.NOTECH_NAME, open(ic, encoding='utf-8').read())
    txt = re.sub(r'(?m)^ManagedPack=.*$', 'ManagedPack=false', txt)  # else Prism "updates" it back to the full pack
    open(ic, 'w', encoding='utf-8', newline='\n').write(txt)
MC = os.path.join(ROOT, 'minecraft')
TRASH = os.path.join(ROOT, 'removed_tech_mods')
log = []


def move(src, sub):
    if not os.path.exists(src):
        return
    dst = os.path.join(TRASH, sub, os.path.basename(src))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    log.append(f'moved {os.path.relpath(src, ROOT)} -> removed_tech_mods/{sub}/')


# ---------------------------------------------------------------- 1. mods
REMOVE_JARS = re.compile(r'^(AE2-MouseTweaks-Fix|ExtendedAE|Modern-Industrialization|Powah|RebornCore|TechReborn|'
                         r'ae2-emi-crafting|ae2wtlib|applied-botanics|appliedenergistics2|megacells|merequester|polyeng)')
for f in sorted(os.listdir(os.path.join(MC, 'mods'))):
    if REMOVE_JARS.match(f):
        move(os.path.join(MC, 'mods', f), 'mods')

# ---------------------------------------------------------------- 2. configs of removed mods
for c in ['ae2', 'techreborn', 'reborncore', 'modern_industrialization.toml', 'powah.json5', 'extendedae.yaml',
          'megacells.json', 'merequester.json', 'ae2-emi-crafting.json', 'magna.json']:
    move(os.path.join(MC, 'config', c), 'config')

# ---------------------------------------------------------------- 3. resource packs for removed mods
RP_REMOVE = re.compile(r'^(Create_Applied_Energistics_2|create_applied_energistics_recipes_alts|HTP-Applied energistics 2|'
                       r'HTP-Extendedae|HTP-Megacells|HTP-Modern industralization|HTP-Industrial revolution|Powah-PT-BR|'
                       r'Megacells-PT-BR|Appbot-PT-BR|Merequester-Spanish|Ae2wtlib-Spanish).*\.zip$')
removed_rps = []
for f in sorted(os.listdir(os.path.join(MC, 'resourcepacks'))):
    if RP_REMOVE.match(f):
        move(os.path.join(MC, 'resourcepacks', f), 'resourcepacks')
        removed_rps.append(f)
opt = os.path.join(MC, 'options.txt')
lines = open(opt, encoding='utf-8').read().split('\n')
for i, line in enumerate(lines):
    if line.startswith('resourcePacks:') or line.startswith('incompatibleResourcePacks:'):
        k, v = line.split(':', 1)
        packs = [p for p in json.loads(v) if p.replace('file/', '') not in removed_rps]
        lines[i] = k + ':' + json.dumps(packs, ensure_ascii=False, separators=(',', ':'))
open(opt, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))

# ---------------------------------------------------------------- 4. Paxi datapacks
DP = os.path.join(MC, 'config', 'paxi', 'datapacks')
for f in os.listdir(DP):
    if f.startswith('create_applied_energistics_recipes_alts') or f.startswith('alms_oil_compat'):
        move(os.path.join(DP, f), 'paxi_datapacks')


def rewrite_zip(path, edit):
    """edit(name, bytes) -> bytes | None (None drops the entry)."""
    src = zipfile.ZipFile(io.BytesIO(open(path, 'rb').read()))
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for info in src.infolist():
            data = edit(info.filename, src.read(info.filename))
            if data is None:
                log.append(f'  - dropped {info.filename}')
                continue
            z.writestr(info, data)
    os.makedirs(os.path.join(TRASH, 'paxi_datapacks_original'), exist_ok=True)
    keep = os.path.join(TRASH, 'paxi_datapacks_original', os.path.basename(path))
    if not os.path.exists(keep):  # never overwrite the pristine copy on a re-run
        shutil.copy2(path, keep)
    open(path, 'wb').write(out.getvalue())
    log.append(f'rewrote {os.path.relpath(path, ROOT)} (original kept in removed_tech_mods/paxi_datapacks_original/)')


ALMS_DROP = re.compile(r'^data/(modern_industrialization|techreborn|powah|ae2)/|'
                       r'^data/create/recipes/milling/compat/ae2/|'
                       r'^data/create/recipes/sandpaper_polishing/stainless_steel_barrel\.json$|'
                       r'^data/create/recipes/haunting/pyrite_dust_from_glowstone_dust\.json$|'
                       r'^data/minecraft/recipes/smelting/(galena_dust_from_galena_ore|pyrite_dust_from_glowstone_dusts|'
                       r'pyrite_small_dust_from_glowstone_small_dust)\.json$')


def alms_edit(name, data):
    if ALMS_DROP.match(name):
        return None
    if name in ('data/minecraft/recipes/blasting/steel_from_iron_block.json',
                'data/minecraft/recipes/blasting/steel_from_iron_ingot.json'):
        log.append(f'  - {name}: result techreborn:steel_ingot -> ad_astra:steel_ingot')
        return data.replace(b'techreborn:steel_ingot', b'ad_astra:steel_ingot')
    if name in ('data/c/tags/items/salt.json', 'data/c/tags/items/salts.json'):
        log.append(f'  - {name}: removed required modern_industrialization:salt_dust entry')
        return json.dumps({'replace': False, 'values': ['expandeddelight:ground_salt']}, indent=2).encode()
    if name == 'data/soulsweapons/recipes/draugr.json':
        log.append(f'  - {name}: #c:silver_ingots -> create:zinc_ingot')
        return data.replace(b'"tag": "c:silver_ingots"', b'"item": "create:zinc_ingot"')
    return data


for f in os.listdir(DP):
    if f.startswith('alms_recipe_additions'):
        rewrite_zip(os.path.join(DP, f), alms_edit)
    if f.startswith('tierify-prominence-tweaks'):
        rewrite_zip(os.path.join(DP, f), lambda n, d: None if n == 'data/tiered/reforge_items/formation_core.json' else d)

# new fixes datapack (zip, Paxi loads zips)
fix = {}


def j(path, obj):
    fix[path] = json.dumps(obj, indent=2, ensure_ascii=False)


j('pack.mcmeta', {'pack': {'pack_format': 15, 'description': 'Prominence II No-Tech: recipe, tag and NPC-trade repairs'}})
# Derelict noctisteel/embers need #c:coal; only MI lignite coal filled it before.
j('data/c/tags/items/coal.json', {'replace': False, 'values': ['minecraft:coal']})
# gun-scaling lists ae2:matter_cannon as a REQUIRED entry; without AE2 both tags would fail to load.
for t in ('weapons', 'ranged_weapons'):
    j(f'data/c/tags/items/{t}.json', {'replace': True, 'values': []})
# Tier 2 reforging (Pyrite): the only furnace route was glowstone dust -smelt-> TR pyrite dust, 4 dust -> 1 chunk.
# Same cost via the glowstone block (= 4 dust). The Create haunting route already exists in alms_recipe_additions.
j('data/prominence_notech/recipes/pyrite_chunk_from_smelting_glowstone.json',
  {'type': 'minecraft:smelting', 'category': 'misc', 'ingredient': {'item': 'minecraft:glowstone'},
   'result': 'tiered:pyrite_chunk', 'experience': 0.4, 'cookingtime': 400})
# Silver no longer exists; zinc (Create) is the same tier of secondary ore metal.
j('data/prominence_notech/recipes/silver_bullet_from_zinc.json',
  {'type': 'minecraft:crafting_shapeless', 'category': 'equipment',
   'ingredients': [{'item': 'create:zinc_ingot'}, {'tag': 'c:lost_soul'}, {'item': 'minecraft:gunpowder'}],
   'result': {'item': 'soulsweapons:silver_bullet', 'count': 10}})
# Create Crafts & Additions only makes electrum from gold + silver (hidden when no silver exists);
# keep its Electrum Spool / Amulet obtainable with the same silver -> zinc substitution.
j('data/prominence_notech/recipes/electrum_from_mixing_zinc.json',
  {'type': 'create:mixing', 'ingredients': [{'tag': 'c:gold_ingots'}, {'item': 'create:zinc_ingot'}],
   'results': [{'item': 'createaddition:electrum_ingot', 'count': 2}], 'heatRequirement': 'heated'})
# Better Nether ships Tech Reborn grinder recipes without a load condition: gate them so they are skipped silently.
for r in ('cincinnasite_ore', 'nether_lapis_ore', 'nether_ruby_ore'):
    j(f'data/techreborn/recipes/grinder/{r}.json',
      {'fabric:load_conditions': [{'condition': 'fabric:all_mods_loaded', 'values': ['techreborn']}]})
# Prominent NPC data: Artifact Vendor's Charm of Sinking trade used a Tech Reborn lead block.
pj = zipfile.ZipFile(os.path.join(MC, 'mods', next(f for f in os.listdir(os.path.join(MC, 'mods'))
                                                     if f.startswith('Prominent-GLOBAL'))))
for era in ('past', 'present'):
    p = f'data/prominent/prominent/trade_data_list/{era}/artifact_vendor.json'
    fix[p] = pj.read(p).decode('utf-8').replace('techreborn:lead_storage_block', 'create:zinc_block')
# Unused AE2 storage-cell lottery (only the removed AE2 chapter rewarded it): keep it valid with Create parts.
j('data/prominent/prominent/lottery_data/ae2_storagecells_lottery.json', {'entries': [
    {'items': [{'id': 'create:andesite_alloy', 'Count': 16}], 'weight': 40, 'rarity': 'common'},
    {'items': [{'id': 'create:brass_ingot', 'Count': 8}], 'weight': 30, 'rarity': 'uncommon'},
    {'items': [{'id': 'create:precision_mechanism', 'Count': 2}], 'weight': 23, 'rarity': 'rare'},
    {'items': [{'id': 'create:sturdy_sheet', 'Count': 4}], 'weight': 6, 'rarity': 'epic'},
    {'items': [{'id': 'create:blaze_burner', 'Count': 1}], 'weight': 1, 'rarity': 'legendary'}]})
fz = os.path.join(DP, 'prominence_notech_fixes.zip')
with zipfile.ZipFile(fz, 'w', zipfile.ZIP_DEFLATED) as z:
    for k, v in fix.items():
        z.writestr(k, v)
log.append(f'created {os.path.relpath(fz, ROOT)} with {len(fix)} files')

# ---------------------------------------------------------------- 5. Block Swap config
bs = os.path.join(MC, 'config', 'blockswap', 'block_swap.json5')
txt = open(bs, encoding='utf-8').read()
new = '\n'.join(line for line in txt.split('\n')
                if not re.search(r'"(modern_industrialization|techreborn|powah):', line))
open(bs, 'w', encoding='utf-8', newline='\n').write(new)
log.append('config/blockswap/block_swap.json5: removed MI/TR/Powah swapper entries')

# ---------------------------------------------------------------- 6. questbook
QD = os.path.join(MC, 'config', 'ftbquests', 'quests')
REMOVED_CHAPTERS = ['applied_energistics_2', 'tech_reborn', 'modern_industrialization', 'powah']
REMOVED_QUESTS = {  # quests whose whole point is a removed mod
    '2BC22D85AC835C6D': 'the_nether: Cinnabar (TR dust)',
    '16DB148BA3164A6C': 'the_nether: Sphalerite (TR dust)',
    '42C1B494F003A1A4': 'the_nether: Getting Lava into the overworld (AE2 quantum ring)',
    '37471F11BB69BA89': 'the_nether: MAXIMUM POWER (Powah magmator)',
    '7E1C1CEE751827EF': 'the_nether: Magmators (Powah)',
}
ITEM_MAP = {
    'techreborn:steel_plate': 'ad_astra:steel_plate',
    'techreborn:steel_ingot': 'ad_astra:steel_ingot',
    'techreborn:steel_storage_block': 'ad_astra:steel_block',
    'techreborn:oil_bucket': 'ad_astra:oil_bucket',
    'modern_industrialization:steel_rod': 'ad_astra:steel_rod',
    'modern_industrialization:stainless_steel_rod': 'ad_astra:iron_rod',
    'techreborn:pyrite_dust': 'tiered:pyrite_chunk',
    'ae2:fluix_sword': 'minecraft:iron_sword',
    'powah:ender_core': 'archon:void_scepter',
    'modern_industrialization:forge_hammer': 'minecraft:anvil',
}
REMOVED_NS = re.compile(r'^(ae2|extendedae|ae2wtlib|megacells|merequester|appbot|polyeng|techreborn|reborncore|'
                        r'modern_industrialization|powah):')

# Always edit from a pristine copy, so re-running never stacks changes (e.g. XP added twice).
PRISTINE = os.path.join(TRASH, 'quests_chapters_original')
os.makedirs(PRISTINE, exist_ok=True)
chapters = {}
for f in os.listdir(os.path.join(QD, 'chapters')):
    p = os.path.join(PRISTINE, f)
    if not os.path.exists(p):
        shutil.copy2(os.path.join(QD, 'chapters', f), p)
    chapters[f[:-5]] = snbt.loads(open(p, encoding='utf-8').read())
for cn in REMOVED_CHAPTERS:  # re-run: chapter already moved out
    moved = os.path.join(TRASH, 'quests_chapters', cn + '.snbt')
    if cn not in chapters and os.path.exists(moved):
        chapters[cn] = snbt.loads(open(moved, encoding='utf-8').read())
all_quests = {q['id']: q for ch in chapters.values() for q in ch.get('quests', [])}
gone = set(REMOVED_QUESTS)
for cn in REMOVED_CHAPTERS:
    gone |= {q['id'] for q in chapters[cn].get('quests', [])}


def resolve(dep, seen=()):
    """A removed prerequisite is replaced by its own surviving prerequisites (keeps gating intact)."""
    if dep not in all_quests:  # pre-existing dangling id in the original book (FTB ignores it): drop it
        return []
    if dep not in gone:
        return [dep]
    if dep in seen or dep not in all_quests:
        return []
    out = []
    for d in all_quests[dep].get('dependencies', []):
        out += resolve(d, seen + (dep,))
    return out


def remap(v):
    if isinstance(v, dict):
        return {k: remap(x) for k, x in v.items()}
    if isinstance(v, list):
        return type(v)(v.t, [remap(x) for x in v]) if isinstance(v, snbt.TypedList) else [remap(x) for x in v]
    if isinstance(v, str) and not isinstance(v, snbt.Raw) and v in ITEM_MAP:
        return ITEM_MAP[v]
    return v


def edit_quest(cn, q):
    qid = q['id']
    title = q.get('title', '')
    if qid == '106CC409603CF580':  # Pyrite
        q['description'] = [
            '&ePyrite&r &7is one of the most important materials in Prominence. You will need Pyrite to reforge your items to a better Tier.',
            '',
            '&7Pyrite Chunks are made from &eGlowstone&7: smelt a &eGlowstone block&7 for one chunk, or &6haunt&7 it with a Create Encased Fan over soul fire for a chance at a second one. Ancient Debris in a Stonecutter also yields 4 chunks.']
    if qid == '4C291EE69F12BEE7':  # The Art of Compressing
        q['tasks'] = [t for t in q['tasks'] if not REMOVED_NS.match(str(t.get('item', {}).get('id') if isinstance(t.get('item'), dict) else t.get('item', '')))]
        if not any(t.get('id') == '6E0C7A11D3B54F21' for t in q['tasks']):
            q['tasks'].append({'id': '6E0C7A11D3B54F21', 'item': 'create:mechanical_press', 'optional_task': snbt.Raw('true'), 'type': 'item'})
        q['description'] = ["&7There are many ways of getting Iron and Steel compressed. Ad Astra's Compressor works on its own power, while a Create Mechanical Press presses Iron into sheets with nothing but rotation."]
    if qid == '52DA21D7B8633C9F':  # Powering Ad Astra Machines
        q['description'] = ["&7Ad Astra Machines accept power from any mod. Besides Ad Astra's own Coal Generator and Solar Panels, Create Crafts & Additions' Alternator or Create: New Age generators turn your Create rotation into power. Ad Astra's Steel and Desh Cables carry it to your machines."]
    if qid == '1702057B5F68995F':  # Netherite
        q['description'] = q['description'][:5]
    if qid == '01683B1B161E67AB':  # enchanting storage block
        q['description'][0] = re.sub(r', even compatible with AE2!.*?Curses!',
            '! What more could you want? Every favorite Enchant and Curse in one place!', q['description'][0])
    if qid == '6C01A4BB169520D8':  # guns: optional AE2 Matter Cannon task
        q['tasks'] = [t for t in q['tasks'] if not (isinstance(t.get('item'), dict) and t['item'].get('id') == 'ae2:matter_cannon')]
    if qid == '42D4036B51BBB3F1':  # Hasturian Era "Stage I: Material List": silver came only from TR/MI ores
        for t in q['tasks']:
            if isinstance(t.get('item'), dict) and t['item'].get('tag', {}).get('value') == 'c:silver_ingots':
                t['item'] = 'create:zinc_ingot'
                t.pop('title', None)
    if qid == '32C20FDE9BB4F43C':  # trash can: TR scrap reward
        q['rewards'] = [{'id': r['id'], 'type': 'xp', 'xp': snbt.Raw('100')} if r.get('item') == 'techreborn:scrap' else r for r in q['rewards']]
    if qid == '48E5D56C47DF6642':  # Train Tracks: upstream filter lists a BYG track that Steam 'n' Rails never registers
        def drop(v):
            if isinstance(v, dict):
                for x in v.values():
                    drop(x)
            elif isinstance(v, list):
                v[:] = [x for x in v if not (isinstance(x, dict) and x.get('id') == 'railways:track_byg_cherry')]
                for x in v:
                    drop(x)
        drop(q['tasks'])
    deps = q.get('dependencies')
    if deps:
        nd = []
        for d in deps:
            for r in resolve(d):
                if r not in nd:
                    nd.append(r)
        if nd != deps:
            log.append(f'  - {cn}:{qid} {title!r}: dependencies {deps} -> {nd}')
        if nd:
            q['dependencies'] = nd
        else:
            del q['dependencies']
    return remap(q)


def num(v):
    return int(str(v).rstrip('Lbsd'))


# Rewards that disappear with the removed quests are moved onto the Create chapter (the tech replacement).
lost = {'xp': 0, 'xp_levels': 0, 'prominent:molten_remnant': 0, 'prominent:infused_molten_remnant': 0}
for qid in gone:
    for r in all_quests.get(qid, {}).get('rewards', []):
        if r.get('type') in ('xp', 'xp_levels'):
            lost[r['type']] += num(r[r['type']])
        elif r.get('type') == 'item':
            it = r.get('item')
            iid = it if isinstance(it, str) else it.get('id')
            if iid in lost:
                lost[iid] += num(r.get('count', 1 if isinstance(it, str) else it.get('Count', 1)))
CAPSTONES = {  # milestone Create machines that receive the Prominent reforging currency
    'prominent:infused_molten_remnant': ['0138F3EB263D1721', '3C67BDE80F43FF9E', '67CE399D0A9C0F57'],  # Train Station, Tesla Coil, Mechanical Crafter
    'prominent:molten_remnant': ['2C8EF8E65133D178', '408D9361AF8AA499', '2E10D93D926631F6'],  # Blaze Burner, Deployer, Precision Mechanism
}


def rid(qid, kind):
    import hashlib
    return hashlib.md5((qid + kind).encode()).hexdigest()[:16].upper()


def split(total, weights):
    """Largest-remainder split: shares proportional to weights, summing exactly to total."""
    tw = sum(weights.values())
    raw = {k: total * w / tw for k, w in weights.items()}
    out = {k: int(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[:total - sum(out.values())]:
        out[k] += 1
    return out


def rebalance_create(ch):
    qs = {q['id']: q for q in ch['quests']}
    memo = {}

    def depth(i, st=()):
        if i not in memo:
            memo[i] = max([depth(d, st + (i,)) + 1 for d in qs[i].get('dependencies', []) if d in qs and d not in st] or [0])
        return memo[i]
    # deeper quests get more; info-only checkmark quests get nothing
    weights = {i: depth(i) + 1 for i, q in qs.items() if any(t.get('type') != 'checkmark' for t in q.get('tasks', []))}
    xp, lv = split(lost['xp'], weights), split(lost['xp_levels'], weights)
    for i, q in qs.items():
        rewards = q.setdefault('rewards', [])
        if xp.get(i):
            cur = next((r for r in rewards if r.get('type') == 'xp'), None)
            if cur:
                cur['xp'] = snbt.Raw(str(num(cur['xp']) + xp[i]))
            else:
                rewards.append({'id': rid(i, 'xp'), 'type': 'xp', 'xp': snbt.Raw(str(xp[i]))})
        if lv.get(i):
            rewards.append({'id': rid(i, 'lv'), 'type': 'xp_levels', 'xp_levels': snbt.Raw(str(lv[i]))})
    for item, ids in CAPSTONES.items():
        assert lost[item] == len(ids), (item, lost[item])
        for i in ids:
            qs[i]['rewards'].append({'id': rid(i, item), 'item': item, 'type': 'item'})
    log.append(f'create: moved rewards of removed quests onto Create quests: {lost} '
               f'(xp max {max(xp.values())}/quest, levels max {max(lv.values())}/quest)')


for cn in REMOVED_CHAPTERS:
    move(os.path.join(QD, 'chapters', cn + '.snbt'), 'quests_chapters')
for cn, ch in chapters.items():
    if cn in REMOVED_CHAPTERS:
        continue
    before = snbt.dumps(ch)
    qs = []
    for q in ch.get('quests', []):
        if q['id'] in gone:
            log.append(f'  - removed quest {q["id"]} ({REMOVED_QUESTS.get(q["id"], cn)})')
            continue
        qs.append(edit_quest(cn, q))
    if 'quests' in ch:
        ch['quests'] = qs
    if 'images' in ch:
        imgs = []
        for im in ch['images']:
            if im.get('dependency') in gone or re.match(r'(powah|modern_industrialization|techreborn|ae2):', im.get('image', '')) and im.get('dependency') != '106CC409603CF580':
                continue
            if im.get('image', '').startswith('techreborn:block/ore/pyrite_ore'):
                im['image'] = 'minecraft:block/glowstone'
            imgs.append(im)
        ch['images'] = imgs
    if 'quest_links' in ch:
        ch['quest_links'] = [ql for ql in ch['quest_links'] if ql.get('linked_quest') not in gone]
    if cn == 'botania':  # Botania is magic, not tech
        ch['group'] = '244F516C4853FD2F'
    if cn == 'create':
        rebalance_create(ch)
    after = snbt.dumps(ch)
    target = os.path.join(QD, 'chapters', cn + '.snbt')
    if after != before:
        open(target, 'w', encoding='utf-8', newline='\n').write(after + '\n')
        log.append(f'edited quests chapter {cn}')
    else:  # untouched chapter: keep the original bytes
        shutil.copy2(os.path.join(PRISTINE, cn + '.snbt'), target)

BSL = chr(92)
cg = os.path.join(QD, 'chapter_groups.snbt')
txt = open(cg, encoding='utf-8').read().replace('title: "&6Tech"', 'title: "&6Create ' + BSL * 2 + '& Automation"')
open(cg, 'w', encoding='utf-8', newline='\n').write(txt)
log.append('chapter group "Tech" renamed to "Create & Automation"; Botania chapter moved to Magic')

open(os.path.join(TRASH, 'CHANGELOG.txt'), 'w', encoding='utf-8').write('\n'.join(log) + '\n')
print('\n'.join(log))

# ---------------------------------------------------------------- 7. summary: fixes that target named files/ids skip silently
jars = sum('-> removed_tech_mods/mods/' in line for line in log)
quests = sum(line.startswith('  - removed quest ') for line in log)
checks = [(f'{jars}/13 tech mod jars removed', jars == 13),
          (f'{quests}/{len(REMOVED_QUESTS)} tech quests removed from The Nether', quests == len(REMOVED_QUESTS))]
checks += [(f'{dp} datapack rewritten', any(line.startswith('rewrote') and dp in line for line in log))
           for dp in ('alms_recipe_additions', 'tierify-prominence-tweaks')]
checks += [(f'quest chapter {cn} edited', f'edited quests chapter {cn}' in log)
           for cn in ('botania', 'create', 'dplanets_and_space', 'eenchanting', 'einformation_7new_mechanics',
                      'elhasturian_era', 'gadgets', 'main_story', 'the_nether', 'to_the_end')]
print('\n==================== SUMMARY ====================')
for label, ok in checks:
    print(f'  [{"OK" if ok else "!!"}] {label}')
failed = sum(not ok for _, ok in checks)
if failed:
    print(f'\nFINISHED WITH {failed} WARNING(S) (marked !!). The pack probably changed in an update: see '
          f'"What can break after an update" in README.md. Full log: {os.path.join(TRASH, "CHANGELOG.txt")}')
    sys.exit(1)
print(f'\nDONE. All {len(checks)} checks passed. {ROOT} is now the No-Tech pack.\n'
      f'Next: build the server pack with   python -X utf8 "{os.path.join(os.path.dirname(os.path.abspath(__file__)), "make_serverpack.py")}"\n'
      f'Then restart Prism, launch "{find_pack.cfg(ROOT).get("name", ROOT)}" and create a NEW world.')
