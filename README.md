# notech-tools: Prominence II "No-Tech" edition

Python scripts that turn a **Prominence II: Hasturian Era** (Minecraft 1.20.1, Fabric) instance in
[Prism Launcher](https://prismlauncher.org/) into a **No-Tech** edition. The big tech mods (AE2, Tech Reborn,
Modern Industrialization, Powah) come out, Create stays as the automation path, and every recipe, tag and quest
that depended on the removed mods is repaired. A builder for the matching dedicated-server pack is included.

Built and tested against Prominence II **v4.1.4**.

> ⚠️ **Not played to completion.** The conversion was checked with automated server tests and static analysis, but nobody has played the pack from start to finish. Some quests, recipes or progression steps may still be broken. Back up your worlds, and report anything that blocks progress.

## Quick start
Needs **Python 3.9+** and Prism Launcher with Prominence II installed and launched once.

```powershell
git clone <this repo> notech-tools
cd notech-tools
python -X utf8 apply_notech.py      # copies the original instance to "(No Tech)" and converts the copy
python -X utf8 qvalidate.py         # optional: static questbook check
python -X utf8 make_serverpack.py   # optional: dedicated-server pack + Calagopus/Pterodactyl upload zip
```
Then launch `Prominence II - Hasturian Era (No Tech)` in Prism and **create a new world**.
The full walkthrough is in [Step by step](#step-by-step-apply_notechpy--make_serverpackpy).

## What's in this repo
| File | What it does |
|---|---|
| `apply_notech.py` | The conversion. It copies the original instance, then removes the tech mods, rewrites datapacks, configs and the questbook, and prints a summary of 14 checks |
| `make_serverpack.py` | Builds a dedicated-server folder (server-side mods only, Fabric launcher, start scripts) plus a panel upload zip |
| `qvalidate.py` | Checks that every quest's items, tags, entities, dimensions, structures, advancements and dependencies exist |
| `recipeverify.py` | Diffs recipe and tag health between the original and the converted instance |
| `find_pack.py` | Finds Prism and the Prominence instances, so no paths need typing |
| `snbt.py` | Minimal SNBT reader/writer for FTB Quests files |
| `boot.sh`, `battery.py`, `battery_rcon.py`, `furnace_test.py`, `logdiff.py` | Optional server boot and in-game test harness (see step 6 of the detailed section) |

## Conversion notes
- The original instance is never modified. The copy is set to `ManagedPack=false`, so Prism will not "update" it back to the full pack.
- Nothing is deleted. Every removed file is moved to `<instance>/removed_tech_mods/`, and `CHANGELOG.txt` there logs each change.

## Removed mods (13 jars)
| Mod | Why |
|---|---|
| Applied Energistics 2, ExtendedAE, MEGA Cells, AE2WTLib, ME Requester, Applied Botanics, Polymorphic Energistics, AE2-MouseTweaks-Fix, AE2 EMI Crafting | Digital storage, plus addons that hard-depend on AE2 |
| Tech Reborn, Reborn Core | Electric industrial machines; Reborn Core is its library |
| Modern Industrialization | Industrial machines and multiblocks |
| Powah | Power generation |

No retained mod loses a dependency. `team_reborn_energy` is still provided by Botarium, Create Crafts & Additions, Create New Age, Estrogen and FTB Quests. Shared libraries were all kept, including Architectury, Cloth Config, Botarium, Polymorph and Resourceful Lib.

## Retained Create mods
- Create
- Create Crafts & Additions
- Create: New Age
- Steam 'n' Rails
- Copycats+
- Create Questing
- Estrogen + Create: Estrogen
- Testosterone + Tweaks
- Integrated Villages / Integrated Stronghold (structure mods that require Create)

The electric addons were kept on purpose. Their power is Create rotation converted into power and back, so they stay inside the Create ecosystem.

**Ad Astra was kept** (along with Giselle Addon and Ad Astra Cable Fix). It adds 5 planets plus orbit dimensions and space structures, and the pack files it under *Exploration*. Its machines run on its own coal generator or solar panels, or on Create Crafts & Additions / New Age generators.

## Recipe, data and config changes
All new data is in the Paxi datapack `config/paxi/datapacks/prominence_notech_fixes.zip`.

| Problem found | Fix |
|---|---|
| `#c:salt` / `#c:salts` (in `alms_recipe_additions`) required MI salt. The tags would fail to load and break ~40 Croptopia food recipes | Removed the MI entry |
| Gun Scaling's `#c:weapons` / `#c:ranged_weapons` required `ae2:matter_cannon`, so both tags would fail | Replaced both with valid, empty tags |
| `#c:coal` only held MI lignite coal, so Derelict's Noctisteel Block and Smoldering Embers were uncraftable | `#c:coal` now contains `minecraft:coal` |
| Steel blasting (iron → Tech Reborn steel) | Now gives Ad Astra steel at the same cost |
| Pyrite (tier 2 reforging): the furnace route went glowstone dust → TR pyrite dust (4 dust → 1 chunk) | Smelt a Glowstone block → 1 Pyrite Chunk (same 4 dust). The Create Haunting route already existed |
| Silver no longer exists (it came only from TR/MI ores) | Draugr recipe uses a Zinc Ingot; new Zinc + Lost Soul + Gunpowder → 10 Silver Bullets; new Create Mixing (heated) Gold + Zinc → 2 Electrum |
| Artifact Vendor NPC (past and present eras): Charm of Sinking cost a TR lead block | Now costs a Create Zinc Block |
| Prominent AE2 storage-cell lottery (only the removed AE2 chapter used it) | Kept valid, now gives Create parts |
| Better Nether's unconditional TR grinder recipes | Gated so they are skipped silently |
| `alms_recipe_additions` | Dropped its TR/MI/Powah/AE2-only recipes. The original zip is in `removed_tech_mods/paxi_datapacks_original/` |
| `tierify-prominence-tweaks` | Dropped its AE2 Matter Cannon reforge entry |
| `create_applied_energistics_recipes_alts`, `alms_oil_compat` (tech-only datapacks) | Moved out |
| Block Swap config | Removed the MI→TR ore and Powah→TR cable swaps |
| Tech-only resource and translation packs | Moved out; `options.txt` pack list cleaned |

## Questbook (31 → 27 chapters, 1785 → 1314 quests)
- **Removed chapters:** Applied Energistics 2, Tech Reborn, Modern Industrialization, Powah.
- **Removed 5 Nether quests:** Cinnabar, Sphalerite, Lava via AE2 Quantum Ring, Magmators, MAXIMUM POWER. "Tap the Mantle" (Create hose pulley) now depends on "Enter the Nether" instead of the Powah quest.
- **Hasturian Era "Stage I: Material List":** 12 `#c:silver_ingots` → 12 Create Zinc Ingots. Without this the campaign could not be completed.
- **Pyrite quest:** asks for Pyrite Chunks, and its text explains the glowstone routes.
- **Planets & Space:**
  - TR/MI icons and rewards point to Ad Astra steel.
  - "Art of Compressing" accepts the Ad Astra Compressor or a Create Mechanical Press.
  - Power and cable advice now refers to Create generators and Ad Astra cables.
- **Icons only** (the tasks were never tech-dependent): Main Story "Null" (Powah icon → Void Scepter) and Hasturian Era "Our Weapon" (MI icon → Anvil).
- **Smaller edits:**
  - Guns quest: removed the optional Matter Cannon task.
  - Trash Can quest: TR scrap reward → 100 XP.
  - AE2 and UU-Matter mentions removed from quest text.
  - Images that used removed textures were dropped or replaced.
- **Pre-existing fixes:** two To-the-End quests pointed at a quest ID that did not exist; that dangling ID was removed (no behaviour change).
- **Cosmetic:** the "Tech" chapter group is now "Create & Automation", and Botania moved to "Magic".
- **Rewards moved to the Create chapter.** The removed quests paid out 36,325 XP, 339 levels, 3 Molten Remnants and 3 Infused Molten Remnants. All of it now sits on Create chapter quests:
  - XP and levels are split by how deep a quest sits in the chapter's progression. The first quests average ~32 XP; the last tier (trains, Tesla Coil, Alternator, Mechanical Roller…) averages ~600 XP and 5 levels. Info-only checkmark quests get nothing extra.
  - Infused Molten Remnants: Train Station, Tesla Coil, Mechanical Crafter.
  - Molten Remnants: Blaze Burner, Deployer, Precision Mechanism.
  - Book-wide XP, levels and remnant totals now match the original. XP is +100 because the Trash Can quest's TR scrap became 100 XP.
  - The ordinary item rewards of the removed quests (redstone, coal, a few diamonds, one nether star) were not moved.
- **Untouched chapters are byte-identical to the original.** The script always edits from pristine copies in `removed_tech_mods/quests_chapters_original/`, so re-running it never stacks rewards.

## Testing (v4.1.4)
**Tested for real:**
- Headless dedicated servers ran both the original and the modified pack, same seed:
  - **No new boot errors** (229 → 228). The only new warnings are 2 lines about Gun Scaling's optional AE2 mixin.
  - Paxi loaded the fixes datapack, and no tag failed to load.
- World generation passed in 13 dimensions: Overworld, Nether, End, Moon, Mars, Venus, Glacio, Vaaz (present), Cinderstone Depths, Bumblezone, Otherside, Maelstrom, Mine Cells Prison.
- Structures located: Integrated Villages, Integrated Stronghold, YUNG's fortress and desert temple, Moon dungeon, Lunarian village.
- Create machines worked: a creative motor drove a millstone, and an encased fan with soul fire turned Glowstone into Pyrite.
- New recipes produced real output in game: blast furnace iron → Ad Astra steel, furnace Glowstone block → Pyrite Chunk.
- Better Nether ore drops, `/reload` and `/ftbquests reload` all worked.
- **Client:** the real No-Tech client launched from Prism, joined the modified server, and synced config and registries.

**Static analysis only:**
- Every quest's items, tags, entities, dimensions, structures, advancements and dependencies resolve. There are no cycles. The only flag left is one BYG track inside an any-of filter, which was already in the original pack.
- Recipe obtainability was compared between the original and the modified pack (`recipe_verification.txt`).

**Not tested:** a full campaign playthrough, and visually opening the questbook.

## Existing worlds
**Start a new world with this pack.** If you ever load an old Prominence world in it:
- Every AE2, TR, MI or Powah block and item is deleted. That includes everything stored in ME drives.
- TR and MI ore in already-generated chunks becomes air.
- Progress on the removed chapters is dropped. All other quest IDs are unchanged, so their progress carries over.

Back the world up first.

## Known limits and notes
- There are no tin, lead, silver, nickel, platinum, uranium or similar ores any more. Alloy Forgery's bronze, electrum and invar recipes, and Create's compat processing for those metals, are unavailable (nothing in the quests needs them).
- There is no digital-storage replacement, by design. Create vaults, Iron Chests and Traveler's Backpack remain.
- **Dedicated servers:** build the server pack with `make_serverpack.py` (**Step by step**, step 5). It has 364 mods and was boot-tested.
  - It already leaves out `ftbquestsfreezefix` and `colorwheel_patcher`, which crash dedicated servers. This was already true of the original pack.
  - Players must use this No-Tech client instance.
  - **Calagopus / Pterodactyl panels:** upload `serverpack-calagopus-upload.zip`. It contains only `mods/`, `config/` and `defaultconfigs/`; the panel's Fabric egg supplies Minecraft and the loader.
    - Set the egg to **Minecraft 1.20.1, Fabric Loader 0.19.3, Java 17**.
    - Delete any mods the egg pre-installs (e.g. Fabric API) before extracting the zip.
    - Set `allow-flight=true` in `server.properties`.
- Some configs (Item Obliterator, Custom Item Attributes, Zenith names, Jade, Carry On, Almost Unified) still mention removed IDs. They were left alone and cause no errors.
- To redo the conversion after a pack update, see the next section.

## Step by step: apply_notech.py + make_serverpack.py
The tools find Prism and the pack on their own (see "Nothing is hard-coded to one PC" above), so they work after a reinstall or on another machine.

You need **Python 3.9+** (`python --version` in PowerShell; get it from python.org and tick "Add to PATH").

**1. Get the original pack into Prism.** Pick one:
- **Fresh PC:** install Prism Launcher → *Add Instance* → *CurseForge* → *Prominence II: Hasturian Era*.
- **You still have it:** update it to the newest version in Prism.
- **Restore an exact version from a backup** (a `.tar` of the instance folder):
  ```powershell
  python -c "import tarfile,sys; tarfile.open(sys.argv[1]).extractall(sys.argv[2], filter='data')" "<backup>.tar" "$env:APPDATA\PrismLauncher\instances"
  ```
  Use this Python command, not Windows `tar`. Windows `tar` breaks the `™` in the folder name.

Launch it once so it downloads Minecraft and generates its configs, then **close Prism**.

**2. Open a terminal in the `notech-tools` folder.** On Windows: open the folder in Explorer, click the address bar, type `powershell`, and press Enter.

**3. Convert** (about two minutes):
```powershell
python -X utf8 apply_notech.py
```
1. It shows the original it found and where the copy goes, then asks `Continue? [y/N]`. Type `y`.
2. It copies the original to `Prominence II - Hasturian Era (No Tech)` and sets `ManagedPack=false` on the copy, so Prism won't "update" it back. Then it converts the copy. **The original is never changed.**
3. It ends with a **SUMMARY**:
   - `DONE. All 14 checks passed.` means it worked.
   - `FINISHED WITH n WARNING(S)` means a fix was skipped, usually because a pack update renamed something. The `!!` lines say which; see "What can break after an update" below.
   - A Python traceback means it failed. Delete the `(No Tech)` folder, fix the cause, and run it again.

**4. Validate** (optional, about a minute each, no game launch):
```powershell
python -X utf8 qvalidate.py
python -X utf8 recipeverify.py > recipe_verification.txt
```
- On v4.1.4, `qvalidate` ends with `-- 27 chapters, 1314 quests, 1 problems`. The one problem is the harmless `railways:track_byg_cherry`.
- The detailed section's step 4 says what a healthy `recipe_verification.txt` looks like.

**5. Build the server pack** (a few minutes; needs internet for the Fabric launcher):
```powershell
python -X utf8 make_serverpack.py
```
It ends with `DONE.` and the paths of:
- `...\(No Tech)\serverpack\`: a complete server. Copy it to the server machine and run `start.bat` (Windows) or `start.sh` (Linux). Its `SERVER_README.txt` covers the EULA and memory settings.
- `...\(No Tech)\serverpack-calagopus-upload.zip`: the file to upload to Calagopus / Pterodactyl. Set the egg to Minecraft 1.20.1, Fabric Loader 0.19.3, Java 17. Delete any mods the egg pre-installed, extract the zip, and set `allow-flight=true` in `server.properties`.

If `serverpack` already exists the script stops. Delete it and the old zip first.

**6. Play.** Open Prism, launch `Prominence II - Hasturian Era (No Tech)`, and **create a new world**. Players joining the server must use this instance.

**If discovery picks wrong or finds nothing,** the script says so and stops without changing anything. You can always pass paths yourself, as in the detailed section below:
- `apply_notech.py <copy>` converts a copy you made by hand.
- `make_serverpack.py <instance> <output>`.
- `qvalidate.py <instance>\minecraft <client jar>`.
- `recipeverify.py <original>\minecraft <no-tech>\minecraft`.

## Re-applying the conversion after a Prominence II update (details)
The automatic steps above do all of this. This section is the manual version, for troubleshooting. Placeholders:

```powershell
$I     = "$env:APPDATA\PrismLauncher\instances"   # or your Prism data folder's instances
$TOOLS = "<path to this notech-tools checkout>"
$ORIG  = "$I\Prominence™ II- Hasturian Era"
$NEW   = "$I\Prominence II - Hasturian Era (No Tech)"
$MCJAR = "$env:APPDATA\PrismLauncher\libraries\com\mojang\minecraft\1.20.1\minecraft-1.20.1-client.jar"
```

### 1. Update the original and make a fresh copy
1. In Prism, update the **original** instance to the new pack version as usual. Launch it once, then close it, so its configs are generated.
2. Back it up. Right-click it → *Copy*, or zip the folder.
3. Right-click it → *Copy* → name the copy `Prominence II - Hasturian Era (No Tech)`. If an old No-Tech instance with that name exists, move its worlds out and delete it first.
   - Always start from a fresh copy of the updated original. **Never** run the script on an already converted No-Tech instance. Its `removed_tech_mods/quests_chapters_original/` holds the *old* questbook, and the script would rebuild from that.
4. Open the new copy's `instance.cfg` and set `ManagedPack=false`. Otherwise Prism may "update" it back to the full pack.

### 2. Apply
```powershell
python -X utf8 "$TOOLS\apply_notech.py" "$NEW"
```
- The script moves, never deletes. Everything it takes out goes to `$NEW\removed_tech_mods\`, with a log in `CHANGELOG.txt`.
- If it stops with a Python error, delete `$NEW` and go back to step 1.3 after fixing the cause. Don't re-run it on a half-converted copy.

### 3. Check the changelog for silently skipped fixes
Open `$NEW\removed_tech_mods\CHANGELOG.txt`. The script targets specific files and quest IDs, so if an update renamed or reworked them, that fix is **skipped without an error**. Each of these lines should still appear:
- 13 `moved ...mods\` lines, one per removed jar.
- `rewrote ...alms_recipe_additions...` and `rewrote ...tierify-prominence-tweaks...`.
- `created ...prominence_notech_fixes.zip with 13 files`.
- `edited quests chapter` lines for: botania, create, dplanets_and_space, eenchanting, einformation_7new_mechanics, elhasturian_era, gadgets, main_story, the_nether, to_the_end.
- `create: moved rewards of removed quests onto Create quests: ...`.

If one is missing, the matching item in the next list is the likely cause.

**What can break after an update:**
- **New tech mods or addons.** The jar list is `REMOVE_JARS` at the top of the script. A new tech addon will usually fail to load because its parent mod is gone. Add it there.
- **Renamed or rewritten datapacks.** The script matches `alms_recipe_additions*`, `tierify-prominence-tweaks*`, `create_applied_energistics_recipes_alts*` and `alms_oil_compat*` by name.
- **Quest IDs changed** (`edit_quest`, `REMOVED_QUESTS`, `CAPSTONES` in the script).
  - If the removed quests' remnant rewards changed, the script **stops** with an `AssertionError` mentioning `molten_remnant`. Update `CAPSTONES` to the new count.
- **Prominent changed the Artifact Vendor trade files.** The fixes datapack overrides them with a copy of the new jar's version, so new trades are kept automatically.

### 4. Validate (needs no game launch)
```powershell
# Questbook: every item, tag, entity, dimension, structure, advancement and prerequisite must exist
python -X utf8 "$TOOLS\qvalidate.py" "$NEW\minecraft" "$MCJAR"

# Recipes and tags: original vs. converted pack
python -X utf8 "$TOOLS\recipeverify.py" "$ORIG\minecraft" "$NEW\minecraft" > "$NEW\removed_tech_mods\recipe_verification.txt"
```
**Expected results** (as of v4.1.4):

| Tool | Healthy output | Investigate |
|---|---|---|
| `qvalidate.py` | Only `Train Tracks ... railways:track_byg_cherry` (harmless, already in the original pack) | Any `unknown item`, an empty `item tag filter`, `unknown dependency` or `dependency cycle`. Each line names the chapter and quest. |
| `recipeverify.py`: `broken_tags` | `0` | Any tag listed. It means a tag now requires a removed item, which breaks every recipe using that tag. Override it in the fixes datapack the way `c:weapons` is done. |
| `recipeverify.py`: `lost_items` | Only Better Nether `cincinnasite` / `lapis_pile` (still drop from their ores) and `create:crushed_raw_*` (metals that no longer exist) | Anything else is an item that became uncraftable. Decide whether it matters and add a recipe if so. |
| `recipeverify.py`: `newly_broken` | Alloy Forgery / Create processing for tin, lead, silver, nickel, platinum, uranium, iridium, tungsten, titanium, antimony; C&A electrum mixing; the silver bullet; Tierify `*_modded` | New entries with a real output |

### 5. Rebuild the server pack
```powershell
python -X utf8 "$TOOLS\make_serverpack.py" "$NEW" "$NEW\serverpack"
```
What the script does:
- Copies the server-side mods, `config` (Paxi datapacks and questbook included) and `defaultconfigs`.
- Downloads the Fabric server launcher and adds start scripts.
- Writes `serverpack-calagopus-upload.zip` next to the output folder (only `mods/`, `config/`, `defaultconfigs/`) for Calagopus / Pterodactyl panels.
- Leaves out:
  - client-only jars;
  - `ftbquestsfreezefix` and `colorwheel_patcher`, which crash dedicated servers;
  - any mod that depends on a jar that was left out (e.g. Colorwheel needs Iris, Forge Config Screens needs Mod Menu).

The output folder must not already exist. Boot it once (step 6) before handing it out.

### 6. Optional: server boot test
This is how the before/after server comparison was done:
1. Make two server folders, each with:
   - `mods`, `config` and `defaultconfigs` copied from the instance's `minecraft` folder;
   - [`fabric-server-launch.jar`](https://meta.fabricmc.net/v2/versions/loader/1.20.1/0.19.3/1.1.2/server/jar);
   - `eula.txt` containing `eula=true`;
   - a `server.properties` with `online-mode=false`, `enable-rcon=true`, `rcon.port=25575`, `rcon.password=notechtest` (or set `RCON_PORT` / `RCON_PASSWORD` to match yours).
2. Remove `ftbquestsfreezefix` and `colorwheel_patcher` from both `mods` folders. They crash dedicated servers.
3. In Git Bash, for each folder, run `bash boot.sh <server folder>`.
   - `boot.sh` uses the Java 17 that Prism downloaded, or `java` on PATH if there is none. The heap defaults to 6G; the v4.1.4 tests ran with `MEMORY=10G bash boot.sh <server folder>`.
4. When it prints `READY`, run `python battery.py <server folder>`. That does world generation in 13 dimensions, structure, loot and Create machine checks, then reloads and stops the server.
5. Compare the two boot logs with `python logdiff.py <original>\logs\latest.log <new>\logs\latest.log`. Healthy: no new `ERROR` lines.

Run one server at a time; both use ports 25565 and 25575.
