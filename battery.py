"""Functional test battery over RCON for a running test server.

usage: battery.py <server_dir>   (RCON settings: see battery_rcon.py)
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from battery_rcon import Rcon  # noqa: E402

SRV = sys.argv[1]
LOG = os.path.join(SRV, 'logs', 'latest.log')


r = Rcon()
results = {}


def check(name, cmd, expect):
    out = re.sub(r'§.', '', r.cmd(cmd))
    ok = bool(re.search(expect, out))
    results[name] = ('PASS' if ok else 'FAIL') + f' :: {out[:160]}'


# ---- worldgen: pregenerate around spawn in many dimensions
DIMS = {'minecraft:overworld': 160, 'minecraft:the_nether': 96, 'minecraft:the_end': 96,
        'ad_astra:moon': 64, 'ad_astra:mars': 64, 'ad_astra:venus': 64, 'ad_astra:glacio': 64,
        'prominent:vaaz_present': 64, 'prominent:cinderstone_depths': 64, 'the_bumblezone:the_bumblezone': 64,
        'deeperdarker:otherside': 64, 'aquamirae:the_maelstrom': 48, 'minecells:prison': 48}
r.cmd('chunky silent')
for d, rad in DIMS.items():
    r.cmd(f'chunky world {d}')
    r.cmd('chunky center 0 0')
    r.cmd(f'chunky radius {rad}')
    r.cmd('chunky start')
t0 = time.time()
while time.time() - t0 < 1500:
    log = open(LOG, encoding='utf-8', errors='replace').read()
    done = set(re.findall(r'Task finished for ([a-z0-9_:]+)', log))
    if all(d in done for d in DIMS):
        break
    time.sleep(10)
log = open(LOG, encoding='utf-8', errors='replace').read()
done = set(re.findall(r'Task finished for ([a-z0-9_:]+)', log))
for d in DIMS:
    results[f'worldgen {d}'] = 'PASS' if d in done else 'FAIL (not finished)'

# ---- structures
for s in ['integrated_villages:village_here', 'integrated_stronghold:stronghold', 'betterfortresses:fortress',
          'betterdeserttemples:desert_temple', 'ad_astra:moon_dungeon', 'ad_astra:lunarian_village']:
    dim = 'minecraft:the_nether' if s == 'betterfortresses:fortress' else 'ad_astra:moon' if s.startswith('ad_astra') else 'minecraft:overworld'
    check(f'locate {s}', f'execute in {dim} run locate structure {s}', r'nearest|is at')

# ---- loot tables still resolve (Better Nether ore drops replaced TR grinder routes)
r.cmd('forceload add 0 0')
r.cmd('fill -2 199 -2 12 199 12 minecraft:stone')
r.cmd('fill -2 200 -2 12 206 12 minecraft:air')
for b in ['betternether:cincinnasite_ore', 'betternether:nether_lapis_ore']:
    r.cmd(f'setblock 6 200 6 {b}')
    check(f'mine {b}', 'loot spawn 6 205 6 mine 6 200 6 minecraft:diamond_pickaxe', r'Dropped [1-9]')
check('loot minecraft:chests/simple_dungeon', 'loot spawn 6 205 6 loot minecraft:chests/simple_dungeon', r'Dropped [1-9]')
r.cmd('kill @e[type=item]')

# ---- Create kinetics: creative motor -> millstone, items thrown in
r.cmd('setblock 0 200 0 create:creative_motor[facing=up]')
r.cmd('setblock 0 201 0 create:millstone')
r.cmd('summon item 0.5 202.2 0.5 {Item:{id:"minecraft:wheat",Count:8b}}')
# ---- Create haunting: motor -> encased fan -> soul campfire -> glowstone item (NEW recipe -> pyrite chunk)
r.cmd('setblock 0 200 5 create:creative_motor[facing=east]')
r.cmd('setblock 1 200 5 create:encased_fan[facing=east]')
r.cmd('setblock 2 200 5 minecraft:soul_campfire')
r.cmd('summon item 4.5 200.1 5.5 {Item:{id:"minecraft:glowstone",Count:4b},NoGravity:0b}')
# ---- furnace recipes changed by the conversion
r.cmd('setblock 0 200 9 minecraft:blast_furnace{Items:[{Slot:0b,id:"minecraft:iron_ingot",Count:2b},{Slot:1b,id:"minecraft:coal_block",Count:1b}]}')
r.cmd('setblock 3 200 9 minecraft:furnace{Items:[{Slot:0b,id:"minecraft:glowstone",Count:1b},{Slot:1b,id:"minecraft:coal_block",Count:1b}]}')
time.sleep(45)
check('create millstone grinds wheat', 'data get block 0 201 0', r'create:wheat_flour|flour')
check('create fan haunting glowstone -> pyrite', 'execute if entity @e[type=item,nbt={Item:{id:"tiered:pyrite_chunk"}}]', r'Test passed')
check('blast furnace iron -> steel', 'data get block 0 200 9 Items', r'steel_ingot')
check('furnace glowstone -> pyrite chunk', 'data get block 3 200 9 Items', r'tiered:pyrite_chunk')
r.cmd('data get block 0 200 9')
r.cmd('data get block 3 200 9')

# ---- datapack + quest reload
check('reload', 'reload', r'.')
check('ftbquests reload', 'ftbquests reload', r'.')
r.cmd('save-all flush')
print('\n===== RESULTS')
for k, v in results.items():
    print(f'{k:<45} {v}')
r.cmd('stop')
