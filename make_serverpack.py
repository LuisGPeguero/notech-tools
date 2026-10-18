"""Build a dedicated-server pack from a (No-Tech) Prism instance.

usage: make_serverpack.py [<instance_root> [<output_dir>]]
With no arguments it finds the converted No-Tech instance in Prism and writes <instance_root>/serverpack.
Copies server-side mods (drops jars whose fabric.mod.json says environment "client", plus known server crashers),
config/ (incl. Paxi datapacks and the questbook) and defaultconfigs/, then adds the Fabric launcher and start scripts.
Also writes <output_dir>-calagopus-upload.zip (mods/config/defaultconfigs only) for Calagopus/Pterodactyl panels.
"""
import io
import json
import os
import shutil
import sys
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import find_pack  # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else find_pack.pick('notech', 'converted No-Tech instance')
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'serverpack')
MC = os.path.join(ROOT, 'minecraft')
# environment "*" but crash a dedicated server (empty lang file / client-only class in the main entrypoint)
SERVER_CRASHERS = ('ftbquestsfreezefix', 'colorwheel_patcher')
LAUNCHER = 'https://meta.fabricmc.net/v2/versions/loader/1.20.1/0.19.3/1.1.2/server/jar'
MEMORY = '6G'


def metadata(z):
    """(environment, depends, ids provided) of a jar, including its nested jars' ids."""
    try:
        j = json.loads(z.read('fabric.mod.json').decode('utf-8', 'replace').replace('\n', ' '))
    except Exception:
        return '*', set(), set()
    ids = {j.get('id')} | set(j.get('provides', []))
    for n in j.get('jars', []):
        try:
            ids |= metadata(zipfile.ZipFile(io.BytesIO(z.read(n['file']))))[2]
        except Exception:
            pass
    return j.get('environment', '*'), set(j.get('depends', {})), ids


if os.path.exists(OUT):
    sys.exit(f'{OUT} already exists, remove it first')
print(f'Building server pack from {ROOT} (a few minutes)...')
jars = {}
for f in sorted(os.listdir(os.path.join(MC, 'mods'))):
    if f.endswith('.jar'):
        with zipfile.ZipFile(os.path.join(MC, 'mods', f)) as z:
            jars[f] = metadata(z)
kept = {f for f, (env, _, _) in jars.items() if env != 'client' and not f.startswith(SERVER_CRASHERS)}
# a server mod that depends on a client-only mod (e.g. colorwheel -> iris) must go too; repeat until stable
BUILTIN = {'minecraft', 'java', 'fabricloader'}
while True:
    provided = BUILTIN | {i for f in kept for i in jars[f][2]}
    drop = {f for f in kept if not jars[f][1] <= provided}
    if not drop:
        break
    kept -= drop
kept, skipped = sorted(kept), sorted(set(jars) - kept)
os.makedirs(os.path.join(OUT, 'mods'))
for f in kept:
    shutil.copy2(os.path.join(MC, 'mods', f), os.path.join(OUT, 'mods', f))
for d in ('config', 'defaultconfigs'):
    shutil.copytree(os.path.join(MC, d), os.path.join(OUT, d))
urllib.request.urlretrieve(LAUNCHER, os.path.join(OUT, 'fabric-server-launch.jar'))

open(os.path.join(OUT, 'server.properties'), 'w', newline='\n').write(
    'motd=Prominence II: Hasturian Era (No Tech)\n'
    'allow-flight=true\n'        # flight/dash/mount mods otherwise get players kicked for "flying"
    'max-tick-time=180000\n'     # heavy modded worldgen can exceed the vanilla 60s watchdog
    'difficulty=normal\n'
    'view-distance=8\n'
    'simulation-distance=6\n')
open(os.path.join(OUT, 'start.bat'), 'w', newline='\r\n').write(
    '@echo off\n'
    f'java -Xms{MEMORY} -Xmx{MEMORY} -jar fabric-server-launch.jar nogui\n'
    'pause\n')
open(os.path.join(OUT, 'start.sh'), 'w', newline='\n').write(
    '#!/bin/sh\n'
    f'java -Xms{MEMORY} -Xmx{MEMORY} -jar fabric-server-launch.jar nogui\n')
open(os.path.join(OUT, 'SERVER_README.txt'), 'w', newline='\n').write(f"""Prominence II: Hasturian Era (No Tech) - server pack
Minecraft 1.20.1, Fabric Loader 0.19.3. Players must use the matching "No Tech" client instance.

1. Install Java 17 (64-bit).
2. Run start.bat (Windows) or start.sh (Linux/macOS). The first run downloads the Minecraft server and
   Fabric libraries, then stops and asks you to accept the Minecraft EULA.
3. Read https://aka.ms/MinecraftEULA, set eula=true in eula.txt, and run the start script again.
4. Memory is set to {MEMORY} in the start scripts; 6-8G is recommended for this pack.

Do not add ftbquestsfreezefix or colorwheel_patcher to mods/: they crash dedicated servers.
Start a NEW world: worlds from the full Prominence II pack lose all AE2/Tech Reborn/MI/Powah blocks and items.

{len(kept)} mods included; {len(skipped)} client-only/server-crashing jars left out.
""")
# Calagopus/Pterodactyl upload: only mods/config/defaultconfigs, the panel's Fabric egg supplies the rest
UPLOAD = OUT.rstrip('\\/') + '-calagopus-upload.zip'
with zipfile.ZipFile(UPLOAD, 'w', zipfile.ZIP_DEFLATED) as z:
    for d in ('mods', 'config', 'defaultconfigs'):
        for base, _, files in os.walk(os.path.join(OUT, d)):
            for f in files:
                z.write(os.path.join(base, f), os.path.relpath(os.path.join(base, f), OUT))
print(f'kept {len(kept)} mods, skipped {len(skipped)}:')
for f in skipped:
    print('  -', f)
print(f'\nDONE.\n  Server folder:    {OUT}  (run start.bat / start.sh)\n  Calagopus upload: {UPLOAD}')
