"""Furnace + structure checks with properly initialised furnaces (CookTimeTotal set)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from battery_rcon import Rcon  # noqa: E402

r = Rcon()
r.cmd('forceload add 0 0')
r.cmd('fill -2 199 -2 12 199 12 minecraft:stone')
r.cmd('fill -2 200 -2 12 206 12 minecraft:air')
r.cmd('setblock 0 200 9 minecraft:blast_furnace{CookTimeTotal:100s,Items:[{Slot:0b,id:"minecraft:iron_ingot",Count:2b},{Slot:1b,id:"minecraft:coal_block",Count:1b}]}')
r.cmd('setblock 3 200 9 minecraft:furnace{CookTimeTotal:400s,Items:[{Slot:0b,id:"minecraft:glowstone",Count:1b},{Slot:1b,id:"minecraft:coal_block",Count:1b}]}')
time.sleep(30)
out1 = r.cmd('data get block 0 200 9 Items')
out2 = r.cmd('data get block 3 200 9 Items')
out3 = r.cmd('execute in minecraft:overworld run locate structure #integrated_villages:villages')
print('RESULT blast furnace iron -> ad_astra steel:', 'PASS' if 'ad_astra:steel_ingot' in out1 else 'FAIL')
print('RESULT furnace glowstone block -> pyrite chunk:', 'PASS' if 'tiered:pyrite_chunk' in out2 else 'FAIL')
print('RESULT locate integrated villages:', 'PASS' if 'nearest' in out3 else 'FAIL')
