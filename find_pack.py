"""Find Prism Launcher and the Prominence II instances, so the tools run without typing paths (e.g. after a reinstall)."""
import glob
import os
import sys

NOTECH_NAME = 'Prominence II - Hasturian Era (No Tech)'


def prism_dir():
    candidates = [os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # tools kept inside the Prism folder
                  os.path.join(os.environ.get('APPDATA', ''), 'PrismLauncher'),
                  os.path.expanduser('~/.local/share/PrismLauncher'),
                  os.path.expanduser('~/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher'),
                  os.path.expanduser('~/Library/Application Support/PrismLauncher')]
    for d in candidates:
        if os.path.isdir(os.path.join(d, 'instances')):
            return d
    sys.exit('Prism Launcher not found. Install it, add the Prominence II pack from CurseForge, launch it once, '
             'then run this again (or pass the paths yourself).')


def cfg(inst):
    try:
        return dict(line.split('=', 1) for line in open(os.path.join(inst, 'instance.cfg'), encoding='utf-8').read().splitlines()
                    if '=' in line)
    except OSError:
        return {}


def instances(kind):
    """kind 'original': Prominence II with its tech mods still in. kind 'notech': already converted."""
    out = []
    for inst in sorted(glob.glob(os.path.join(prism_dir(), 'instances', '*'))):
        if 'prominence' not in cfg(inst).get('name', '').lower():
            continue
        converted = os.path.exists(os.path.join(inst, 'removed_tech_mods', 'CHANGELOG.txt'))
        has_tech = bool(glob.glob(os.path.join(inst, 'minecraft', 'mods', 'TechReborn*.jar')))
        if (kind == 'notech' and converted) or (kind == 'original' and has_tech and not converted):
            out.append(inst)
    return out


def pick(kind, what):
    found = instances(kind)
    if len(found) == 1:
        return found[0]
    print(f'{"Several" if found else "No"} {what} found in {os.path.join(prism_dir(), "instances")}')
    for f in found:
        print('  ', f)
    sys.exit('Pass the instance folder as an argument instead.')


def mc_jar():
    return os.path.join(prism_dir(), 'libraries', 'com', 'mojang', 'minecraft', '1.20.1', 'minecraft-1.20.1-client.jar')
