# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A **client-only web tool** that merges Minecraft Java resource packs from Modrinth / CurseForge / PlanetMinecraft links and uploaded ZIPs into one pack, and can wrap the merged pack into a **self-extracting Windows installer EXE**. Deployed via GitHub Pages (branch `main`) at `giamat13/resource-packs-minecraft-manager`. UI is Hebrew/RTL.

There is **no build step** and **no server**. `package.json` is vestigial (its `main: server.js` / `start` script refer to a server that was removed during the pivot to a pure static app). `npm install` exists only to provide `jszip` for Node-based tests; the app itself uses the committed `vendor/jszip.min.js`.

## Layout

- `index.html` — the entire web app: HTML + inline CSS + one big inline `<script>` (the last `<script>` block) holding all logic. Loads `vendor/jszip.min.js`.
- `installer/mc_pack_installer.py` — Python/tkinter GUI installer (detection + install + self-extract reader). Also the source PyInstaller compiles into the stub.
- `installer/MC-Pack-Installer-stub.exe` — **committed prebuilt** PyInstaller stub the browser fetches and turns into a custom installer. Must be rebuilt and re-committed whenever `mc_pack_installer.py` changes.
- `installer/build_installer_icon.py` — generates `installer_icon.ico` (a single fixed-size **256×256, 32-bit, uncompressed** icon) used when building the stub. The fixed uncompressed slot is what makes in-browser icon replacement possible; do not build the stub with a multi-size or PNG-compressed `.ico`.
- `.github/workflows/build-installer.yml` — manual (`workflow_dispatch`) job that rebuilds the stub as a downloadable artifact. No Releases are used.
- `research-resource-packs.md`, `README.md` — reference docs (README is the authoritative feature spec, in Hebrew).

## Commands

```bash
# Run the app (required for the "build EXE" feature — it fetches the stub same-origin,
# which is blocked on file://). Plain ZIP builds also work by opening index.html directly.
python -m http.server 8000        # then open http://localhost:8000

# Syntax-check the app script (extract the last <script> block, node --check it)
node -e 'const fs=require("fs");const h=fs.readFileSync("index.html","utf8");const m=[...h.matchAll(/<script>([\s\S]*?)<\/script>/g)];fs.writeFileSync("/tmp/app.js",m[m.length-1][1]);' && node --check /tmp/app.js

# Installer debug (no GUI)
python installer/mc_pack_installer.py --list         # print detected Minecraft instances
python installer/mc_pack_installer.py --check-embed  # report embedded payload if any

# Rebuild the stub after editing mc_pack_installer.py, then commit the new .exe
pip install pyinstaller pillow
python installer/build_installer_icon.py
pyinstaller --onefile --windowed --name "MC-Pack-Installer-stub" --icon installer/installer_icon.ico installer/mc_pack_installer.py
cp dist/MC-Pack-Installer-stub.exe installer/MC-Pack-Installer-stub.exe
```

Note the environment is Windows; the Bash tool runs Git Bash. Use the scratchpad dir (not `/tmp`) for temp files — `/tmp` resolves to `C:\tmp` and often fails.

## Testing pattern (there is no test framework)

Logic is verified by pulling individual functions out of `index.html` with a regex and `eval`-ing them in a **Node CommonJS** (`.cjs`) file with a mock `DB`, then asserting. Use `.cjs`, not `.mjs`: ESM is strict-mode, so `eval`'d `function` declarations don't leak into scope. JSZip is available via `node_modules`. Python logic (instance detection, self-extract, base64 round-trips) is tested against temp directories / the real machine. Always `node --check` the extracted script after editing the web app.

## Web app architecture (all in index.html)

**Storage split — this is central:**
- Project configs (array) live in `localStorage` under `rpm.projects.v1` (+ `rpm.selected.v1`). Keep these small — only metadata and references.
- All binary blobs live in `IndexedDB` (db `rpm-blobs`, store `blobs`), keyed by convention: uploaded source ZIPs by the source's `id`; project icon under `icon:<projectId>`; per-item-texture images under `cit:<projectId>:<ruleId>`; per-block-texture images under `blk:<projectId>:<ruleId>:<face>` (`face` is `all` for uniform mode or one of `up/down/north/south/east/west`); per-sound audio under `snd:<projectId>:<ruleId>`. The `DB` helper wraps put/get/del.
- A project is `{id, name, targetVersion, packFormat, description, sources[], hasIcon, cit:{rules[]}, blocks:{rules[]}, sounds:{rules[]}, locks:{rules[]}}`. Sources are ordered; **index 0 = highest priority (top of the stack, wins conflicts)**.

**Merge engine** — `buildMergedPack()` is the shared core; `buildProject()` (download ZIP) and `buildInstallerExe()` (stitch into EXE) both call it. It:
- iterates enabled sources top→bottom, "first writer wins" via a `claimed` map;
- lowercases every path and normalizes `models/`, `blockstates/`, `items/` JSON references (`walkModelRefs`) to prevent magenta/black missing-texture from case mismatches;
- strips a wrapper folder inside a ZIP (`findRootPrefix`);
- drops a texture's `.png.mcmeta` when it and its `.png` came from different sources (prevents corrupted animations);
- generates a fresh `pack.mcmeta` from `packFormat`;
- injects the custom `pack.png`, item-texture files, block-texture files, and sound overrides (these **override** sources — explicit user choice), then applies lock/block rules **last** (they override everything, including the user's own custom-texture rules);
- runs a validator that flags broken texture/model/sound references in **non-`minecraft`** namespaces.

**Version gating:** the `VERSIONS` table maps Minecraft versions → `pack_format`. `citIsModern(p)` returns `packFormat >= CIT_MODERN_MIN_PF` (55, i.e. **1.21.5+**) and switches feature behavior. Verified byte-for-byte against a real, working, downloaded Modrinth pack ("Totem's Renamed", 1.21.5+ only) — do not lower this threshold without re-verifying against a real pack.

**Custom item/block/sound card is unified in the UI, not in storage** — `renderCustomAssetsSection(p)` renders ONE card ("🎨 טקסטורות ואודיו מותאמים אישית") with one combined, ordered list, but the underlying data stays as three separate arrays (`p.cit.rules`, `p.blocks.rules`, `p.sounds.rules`) so `buildItemFiles`/`buildBlockFiles`/`applySoundOverrides` and export/import didn't need to change shape. Ordering across the three is tracked by a `seq` field on each rule (`nextSeq(p)` increments `p.customAssetsSeq`); the combined render sorts by `seq`. Changing a row's "kind" dropdown calls `changeRuleKind()`, which deletes that rule's old IndexedDB blob(s), removes it from its old array, and creates a fresh rule of the target kind's shape in the right array (same `seq`, new `id` — the upload is lost on a kind switch since the shapes are incompatible, which is expected).

**Per-item custom textures** — `buildItemFiles(p)` groups rules by item. Blank rule name → replace `assets/<ns>/textures/item/<item>.png` directly (works everywhere). Named rule → on **1.21.5+**, a vanilla item model at `assets/<ns>/items/<item>.json` using `select` on the `minecraft:custom_name` component (no mods, works with Sodium); on older targets (including 1.21.4), OptiFine **CIT** `.properties` (needs OptiFine / CIT Resewn). Multiple names for one item are merged into one `items` definition with multiple `cases`.

**Per-block custom textures** — `buildBlockFiles(p)` handles uniform ("all faces") or per-face rules. Unlike items, blocks have **no** anvil-rename/`custom_name` mechanism (that only affects the item form, never the placed block in the world — confirmed via research, not just assumed), so this is always a direct override: generates a custom block model (`minecraft:block/cube_all` or `minecraft:block/cube` parent) plus a blockstate that replaces **all** variants with a single one, plus a matching item model override so the inventory icon matches. Only correct for simple full-cube blocks with one blockstate variant (not stairs/slabs/logs/anything directional). Unfilled faces in per-face mode fall back to `<ns>:block/<block_id>` (assumes vanilla's texture filename matches the block id, true for most simple blocks).

**Custom sounds** — `applySoundOverrides(p, out)` writes uploaded OGG files directly into the in-progress `out` zip and merges `replace:true` entries into that namespace's `sounds.json` (reads whatever the main merge loop already wrote there, so source-provided sounds.json entries are preserved except the overridden keys).

**Item/block/entity/sound locks** — `applyLocks(p, out)` lets a rule force a specific `item`/`block`/`entity`/`sound` asset to always be vanilla (removes the known candidate file paths — see `lockCandidatePaths()` — from `out`) or always come from one specific chosen source regardless of priority order (pulls the raw bytes for those paths straight from that source's ZIP via `getSourceFileBytes()`). `entity` only has a texture candidate (`textures/entity/<path>.png`) — vanilla has no resource-pack-level entity model/shape override. The `assetId` field accepts a `*` glob (e.g. `*_bed`, `cow/*`); `expandLockPattern()` resolves it to concrete `{ns,path}` hits by scanning `getSourceIndex()` (all sources for `vanilla` mode, just the chosen one for `source` mode) — a pattern with zero matches is reported as a failure, not silently swallowed. Runs after all other injection steps since it's meant to be the final, most explicit override.

**Entity assets in search/locks** — `KIND_FOLDER`/`ASSET_RE` include `textures/entity` → `entity_texture`; this is deliberately texture-only (no `models/entity` or blockstate-like classification exists for entities in vanilla — their shape is hardcoded in the game's Java code, not resource-pack data).

**Sound events in "who's responsible" search** — unlike item/block/entity rows (existence check of one exact file path via `idx.files.has()`), a sound event isn't a standalone file — it's a key inside `assets/<ns>/sounds.json`. `searchItem()` fetches and parses each enabled source's `sounds.json` (in priority order) and checks for the queried key directly, appending a `sound_event` row that `renderItemSearchResults()` handles generically like any other row.

**Modrinth** is fully automated in-browser (its API + CDN send permissive CORS). **CurseForge / PlanetMinecraft** cannot be fetched from the browser (no CORS / no API), so those sources are manual ZIP uploads.

## Self-extracting EXE (the tricky part)

The browser turns `installer/MC-Pack-Installer-stub.exe` into a per-pack installer entirely client-side:
1. `findRtIcon()` parses the PE to locate the single `RT_ICON` resource (the stub is built with one fixed 256×256 uncompressed slot), and the custom pack icon (resized to a 256×256 BGRA DIB via canvas) overwrites those bytes **in place** — same length, so the PE stays valid.
2. The merged pack ZIP is appended as `[block][footer]`, where `block = uint16 name_len + name + zip` and `footer = "MCPKZIP1" + uint64 block_len` (all little-endian) at the very end of the file. PyInstaller ignores trailing overlay data, so the EXE still runs.
3. At runtime, `read_embedded_payload()` in the Python app reads its own file tail, extracts the pack, and installs it. `install_pack` / `detect_all` handle Vanilla `.minecraft`, CurseForge, Modrinth App, Prism/MultiMC, ATLauncher, GDLauncher.

If you change the payload byte layout, change it in **both** `buildInstallerExe()` (JS) and `read_embedded_payload()` (Python) and re-verify.
