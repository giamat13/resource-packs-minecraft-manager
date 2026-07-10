#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MC Pack Installer — מתקין חבילת משאבים ממוזגת לכל ה-instances שבחרת.

מזהה אוטומטית instances של:
  • Minecraft רגיל (.minecraft)
  • CurseForge
  • Modrinth App
  • Prism Launcher / ATLauncher / GDLauncher (מאמץ מיטבי)

בוחרים instances (יש "בחר הכל"), בוחרים קובץ ZIP של החבילה, ומתקינים
בבת אחת לכל תיקיות ה-resourcepacks הנבחרות.

הלוגיקה של הזיהוי/ההתקנה מופרדת מה-GUI כדי שתהיה ניתנת לבדיקה אוטומטית.
"""

import os
import sys
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ============================================================
# חבילה מוטמעת בתוך ה-EXE (self-extracting)
# הכלי בדפדפן מדביק לזנב ה-EXE: [block][footer]
#   block  = name_len(2 LE) + name(utf-8) + zip_bytes
#   footer = MAGIC(8) + block_len(8 LE)   ← בסוף הקובץ ממש
# ============================================================
EMBED_MAGIC = b"MCPKZIP1"


def read_embedded_payload():
    """אם ה-EXE מכיל חבילה מוטמעת בזנב — מחזיר (filename, zip_bytes), אחרת None."""
    try:
        if not getattr(sys, "frozen", False):
            return None
        exe = sys.executable
        size = os.path.getsize(exe)
        if size < 16:
            return None
        with open(exe, "rb") as f:
            f.seek(size - 16)
            footer = f.read(16)
            if footer[:8] != EMBED_MAGIC:
                return None
            block_len = int.from_bytes(footer[8:16], "little")
            if block_len <= 2 or block_len > size - 16:
                return None
            f.seek(size - 16 - block_len)
            block = f.read(block_len)
        name_len = int.from_bytes(block[:2], "little")
        name = block[2:2 + name_len].decode("utf-8", "replace") or "pack.zip"
        zip_bytes = block[2 + name_len:]
        if not zip_bytes:
            return None
        return name, zip_bytes
    except Exception:
        return None


# ============================================================
# מודל נתונים
# ============================================================
@dataclass
class Instance:
    launcher: str            # "Vanilla" / "CurseForge" / "Modrinth" / ...
    name: str                # שם ה-instance להצגה
    resourcepacks: Path      # תיקיית היעד להתקנת החבילה
    exists: bool = False     # האם תיקיית ה-instance כבר קיימת בפועל
    note: str = ""

    def key(self) -> str:
        return f"{self.launcher}|{self.resourcepacks}".lower()


# ============================================================
# עזרים לגילוי נתיבים
# ============================================================
def _first_existing(paths):
    for p in paths:
        if p and Path(p).is_dir():
            return Path(p)
    return None


def _documents_candidates(home: Path):
    """Documents יכול להיות מופנה ל-OneDrive."""
    return [
        home / "Documents",
        home / "OneDrive" / "Documents",
        home / "OneDrive" / "Documents",
    ]


def _minecraft_subdir(instance_dir: Path) -> Path:
    """Prism/MultiMC שמים את קבצי המשחק תחת .minecraft או minecraft."""
    if (instance_dir / ".minecraft").is_dir():
        return instance_dir / ".minecraft"
    if (instance_dir / "minecraft").is_dir():
        return instance_dir / "minecraft"
    # ברירת מחדל ל-Prism
    return instance_dir / ".minecraft"


# ============================================================
# גלאים לכל לאנצ'ר (מקבלים home/appdata כדי שיהיו ניתנים לבדיקה)
# ============================================================
def detect_vanilla(home: Path, appdata: Path):
    out = []
    mc = _first_existing([
        appdata / ".minecraft",
        home / "AppData" / "Roaming" / ".minecraft",
        home / ".minecraft",
    ])
    if mc:
        out.append(Instance(
            launcher="Vanilla",
            name=".minecraft",
            resourcepacks=mc / "resourcepacks",
            exists=True,
        ))
    return out


def detect_curseforge(home: Path, appdata: Path):
    out = []
    roots = []
    # מיקומים נפוצים (ה-CurseForge app מאפשר לשנות, לכן בודקים כמה)
    roots.append(home / "curseforge" / "minecraft" / "Instances")
    for docs in _documents_candidates(home):
        roots.append(docs / "Curseforge" / "Minecraft" / "Instances")
        roots.append(docs / "curseforge" / "minecraft" / "Instances")
    seen = set()
    for root in roots:
        rp = str(root).lower()
        if rp in seen:
            continue
        seen.add(rp)
        if not root.is_dir():
            continue
        for inst in sorted(root.iterdir()):
            if not inst.is_dir():
                continue
            # instance של CF מכיל minecraftinstance.json
            is_inst = (inst / "minecraftinstance.json").is_file() or (inst / "mods").is_dir() or (inst / "resourcepacks").is_dir()
            if not is_inst:
                continue
            out.append(Instance(
                launcher="CurseForge",
                name=inst.name,
                resourcepacks=inst / "resourcepacks",
                exists=True,
            ))
    return out


def detect_modrinth(home: Path, appdata: Path):
    out = []
    roots = [
        appdata / "ModrinthApp" / "profiles",
        appdata / "com.modrinth.theseus" / "profiles",
        home / "AppData" / "Roaming" / "ModrinthApp" / "profiles",
    ]
    seen = set()
    for root in roots:
        rp = str(root).lower()
        if rp in seen:
            continue
        seen.add(rp)
        if not root.is_dir():
            continue
        for inst in sorted(root.iterdir()):
            if not inst.is_dir():
                continue
            out.append(Instance(
                launcher="Modrinth",
                name=inst.name,
                resourcepacks=inst / "resourcepacks",
                exists=True,
            ))
    return out


def detect_prism(home: Path, appdata: Path):
    out = []
    roots = [
        appdata / "PrismLauncher" / "instances",
        appdata / "MultiMC" / "instances",
        home / "PrismLauncher" / "instances",
        home / "MultiMC" / "instances",
        home / "Desktop" / "MultiMC" / "instances",
    ]
    seen = set()
    for root in roots:
        rp = str(root).lower()
        if rp in seen:
            continue
        seen.add(rp)
        if not root.is_dir():
            continue
        launcher = "MultiMC" if "multimc" in rp else "Prism"
        for inst in sorted(root.iterdir()):
            if not inst.is_dir() or inst.name in (".LAUNCHER_TEMP", "_LAUNCHER_TEMP"):
                continue
            if not ((inst / "instance.cfg").is_file() or (inst / "mmc-pack.json").is_file()
                    or (inst / ".minecraft").is_dir() or (inst / "minecraft").is_dir()):
                continue
            mc = _minecraft_subdir(inst)
            out.append(Instance(
                launcher=launcher,
                name=inst.name,
                resourcepacks=mc / "resourcepacks",
                exists=True,
            ))
    return out


def detect_atlauncher(home: Path, appdata: Path):
    out = []
    roots = [
        appdata / "ATLauncher" / "instances",
        home / "ATLauncher" / "instances",
    ]
    seen = set()
    for root in roots:
        rp = str(root).lower()
        if rp in seen:
            continue
        seen.add(rp)
        if not root.is_dir():
            continue
        for inst in sorted(root.iterdir()):
            if not inst.is_dir():
                continue
            if not ((inst / "instance.json").is_file() or (inst / "resourcepacks").is_dir()):
                continue
            out.append(Instance(
                launcher="ATLauncher",
                name=inst.name,
                resourcepacks=inst / "resourcepacks",
                exists=True,
            ))
    return out


def detect_gdlauncher(home: Path, appdata: Path):
    out = []
    roots = [
        appdata / "gdlauncher_next" / "instances",
        appdata / "gdlauncher_carbon" / "data" / "instances",
    ]
    seen = set()
    for root in roots:
        rp = str(root).lower()
        if rp in seen:
            continue
        seen.add(rp)
        if not root.is_dir():
            continue
        for inst in sorted(root.iterdir()):
            if not inst.is_dir():
                continue
            out.append(Instance(
                launcher="GDLauncher",
                name=inst.name,
                resourcepacks=inst / "resourcepacks",
                exists=True,
            ))
    return out


DETECTORS = [
    detect_vanilla, detect_curseforge, detect_modrinth,
    detect_prism, detect_atlauncher, detect_gdlauncher,
]


def detect_all(home: Optional[Path] = None, appdata: Optional[Path] = None):
    """מחזיר רשימת Instance ייחודית מכל הלאנצ'רים."""
    if home is None:
        home = Path(os.path.expanduser("~"))
    if appdata is None:
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    home = Path(home)
    appdata = Path(appdata)

    results = []
    seen = set()
    for det in DETECTORS:
        try:
            for inst in det(home, appdata):
                if inst.key() in seen:
                    continue
                seen.add(inst.key())
                results.append(inst)
        except Exception as e:  # לא נכשל בגלל לאנצ'ר בעייתי אחד
            sys.stderr.write(f"detector {det.__name__} failed: {e}\n")
    return results


# ============================================================
# התקנה
# ============================================================
def install_pack(zip_path: Path, instance: Instance, overwrite: bool = True):
    """מעתיק את ה-ZIP לתוך תיקיית ה-resourcepacks של ה-instance.
    מחזיר (ok: bool, message: str)."""
    zip_path = Path(zip_path)
    if not zip_path.is_file():
        return False, "קובץ החבילה לא נמצא"
    target_dir = Path(instance.resourcepacks)
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return False, f"לא ניתן ליצור את תיקיית היעד: {e}"
    dest = target_dir / zip_path.name
    if dest.exists() and not overwrite:
        return False, "כבר קיים (דילוג)"
    try:
        shutil.copy2(str(zip_path), str(dest))
    except Exception as e:
        return False, f"העתקה נכשלה: {e}"
    return True, f"הותקן → {dest}"


def newest_zip_in(folder: Path):
    """הקובץ .zip העדכני ביותר בתיקייה (לנוחות: החבילה שהורדת זה עתה)."""
    folder = Path(folder)
    if not folder.is_dir():
        return None
    zips = [p for p in folder.glob("*.zip") if p.is_file()]
    if not zips:
        return None
    return max(zips, key=lambda p: p.stat().st_mtime)


def default_zip_guess():
    home = Path(os.path.expanduser("~"))
    return newest_zip_in(home / "Downloads")


# ============================================================
# GUI
# ============================================================
def run_gui(initial_zip: Optional[str] = None):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.title("MC Pack Installer — התקנת חבילת משאבים")
    root.geometry("760x600")
    try:
        root.tk.call("tk", "scaling", 1.2)
    except Exception:
        pass

    # חבילה מוטמעת (self-extracting) גוברת על כל בחירה אחרת
    embedded = read_embedded_payload()
    embedded_zip = None
    if embedded:
        emb_name, emb_bytes = embedded
        try:
            tmp = Path(tempfile.gettempdir()) / emb_name
            tmp.write_bytes(emb_bytes)
            embedded_zip = tmp
        except Exception:
            embedded_zip = None

    state = {
        "zip": embedded_zip or (Path(initial_zip) if initial_zip else default_zip_guess()),
        "instances": [],
        "vars": [],
        "embedded": embedded_zip is not None,
    }

    # --- קובץ החבילה ---
    top = ttk.Frame(root, padding=10)
    top.pack(fill="x")
    _lbl = "חבילה מוטמעת (מובנית ב-EXE):" if state["embedded"] else "קובץ החבילה (ZIP):"
    ttk.Label(top, text=_lbl, font=("Segoe UI", 10, "bold")).pack(anchor="e")
    zip_row = ttk.Frame(top)
    zip_row.pack(fill="x", pady=4)
    zip_var = tk.StringVar(value=str(state["zip"]) if state["zip"] else "— לא נבחר —")
    zip_entry = ttk.Entry(zip_row, textvariable=zip_var)
    zip_entry.pack(side="left", fill="x", expand=True)

    def choose_zip():
        start = str((state["zip"].parent if state["zip"] else Path(os.path.expanduser("~")) / "Downloads"))
        f = filedialog.askopenfilename(
            title="בחר קובץ חבילת משאבים (ZIP)",
            initialdir=start,
            filetypes=[("Resource pack ZIP", "*.zip"), ("All files", "*.*")],
        )
        if f:
            state["zip"] = Path(f)
            zip_var.set(f)

    ttk.Button(zip_row, text="בחר...", command=choose_zip).pack(side="left", padx=(6, 0))

    # --- כותרת רשימה + כפתורים ---
    hdr = ttk.Frame(root, padding=(10, 0))
    hdr.pack(fill="x")
    ttk.Label(hdr, text="בחר instances להתקנה:", font=("Segoe UI", 10, "bold")).pack(side="right")
    btns = ttk.Frame(hdr)
    btns.pack(side="left")
    ttk.Button(btns, text="רענן זיהוי", command=lambda: refresh()).pack(side="left", padx=2)
    ttk.Button(btns, text="הוסף תיקייה...", command=lambda: add_manual()).pack(side="left", padx=2)
    ttk.Button(btns, text="נקה בחירה", command=lambda: set_all(False)).pack(side="left", padx=2)
    ttk.Button(btns, text="בחר הכל", command=lambda: set_all(True)).pack(side="left", padx=2)

    # --- רשימה נגללת ---
    list_wrap = ttk.Frame(root, padding=10)
    list_wrap.pack(fill="both", expand=True)
    canvas = tk.Canvas(list_wrap, highlightthickness=0)
    sb = ttk.Scrollbar(list_wrap, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas)
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    def _on_wheel(e):
        canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", _on_wheel)

    # --- לוג/סטטוס ---
    log = tk.Text(root, height=7, wrap="word", state="disabled",
                  bg="#0b0e12", fg="#e6ebf1", font=("Consolas", 9))
    log.pack(fill="x", padx=10, pady=(0, 6))

    def log_line(msg, color="#e6ebf1"):
        log.configure(state="normal")
        log.insert("end", msg + "\n")
        log.tag_add(color, "end-2l", "end-1l")
        log.tag_config(color, foreground=color)
        log.see("end")
        log.configure(state="disabled")

    def set_all(val):
        for v in state["vars"]:
            v.set(val)

    def add_manual():
        d = filedialog.askdirectory(title="בחר תיקיית resourcepacks (או תיקיית instance)")
        if not d:
            return
        p = Path(d)
        # אם בחרו תיקיית instance ולא resourcepacks — נשלים
        if p.name.lower() != "resourcepacks":
            if (p / "resourcepacks").exists() or not (p / "assets").exists():
                p = p / "resourcepacks"
        inst = Instance(launcher="ידני", name=p.parent.name or str(p), resourcepacks=p, exists=p.exists())
        state["instances"].append(inst)
        rebuild_rows(select_new=inst)

    def rebuild_rows(select_new=None):
        for w in inner.winfo_children():
            w.destroy()
        state["vars"] = []
        by_launcher = {}
        for inst in state["instances"]:
            by_launcher.setdefault(inst.launcher, []).append(inst)

        for launcher in sorted(by_launcher.keys()):
            grp = ttk.Label(inner, text=f"— {launcher} —", font=("Segoe UI", 9, "bold"))
            grp.pack(anchor="e", pady=(8, 2))
            for inst in by_launcher[launcher]:
                var = tk.BooleanVar(value=(inst is select_new))
                state["vars"].append(var)
                inst._var = var  # קישור לצורך איסוף בהתקנה
                row = ttk.Frame(inner)
                row.pack(fill="x", anchor="e")
                txt = f"{inst.name}   —   {inst.resourcepacks}"
                cb = ttk.Checkbutton(row, text=txt, variable=var)
                cb.pack(side="right", anchor="e")

    def refresh():
        log_line("מזהה instances...", "#93a1b0")
        found = detect_all()
        # שמירה על ערכים ידניים שנוספו
        manual = [i for i in state["instances"] if i.launcher == "ידני"]
        state["instances"] = found + manual
        rebuild_rows()
        counts = {}
        for i in found:
            counts[i.launcher] = counts.get(i.launcher, 0) + 1
        summary = ", ".join(f"{k}: {v}" for k, v in counts.items()) or "לא נמצאו"
        log_line(f"נמצאו {len(found)} instances ({summary})", "#3ad29f")

    def do_install():
        if not state["zip"] or not Path(state["zip"]).is_file():
            messagebox.showerror("שגיאה", "בחר קובץ ZIP תקין של החבילה.")
            return
        selected = [i for i in state["instances"] if getattr(i, "_var", None) and i._var.get()]
        if not selected:
            messagebox.showwarning("אין בחירה", "בחר לפחות instance אחד (או 'בחר הכל').")
            return
        ok_n, fail_n = 0, 0
        log_line(f"מתקין '{Path(state['zip']).name}' ל-{len(selected)} instances...", "#93a1b0")
        for inst in selected:
            ok, msg = install_pack(state["zip"], inst, overwrite=True)
            if ok:
                ok_n += 1
                log_line(f"  ✓ {inst.launcher} / {inst.name}", "#3ad29f")
            else:
                fail_n += 1
                log_line(f"  ✗ {inst.launcher} / {inst.name}: {msg}", "#ff6b6b")
        log_line(f"סיום: {ok_n} הצליחו, {fail_n} נכשלו.", "#4ea1ff")
        messagebox.showinfo("הותקן",
                            f"החבילה הותקנה ב-{ok_n} instances."
                            + (f"\n{fail_n} נכשלו — ראה את הלוג." if fail_n else "")
                            + "\n\nהפעל את המשחק, לך ל-Options → Resource Packs והפעל את החבילה.")

    # --- כפתור התקנה ---
    bottom = ttk.Frame(root, padding=10)
    bottom.pack(fill="x")
    install_btn = ttk.Button(bottom, text="התקן על הנבחרים ▶", command=do_install)
    install_btn.pack(side="right")

    refresh()
    root.mainloop()


def main():
    # מצב headless לבדיקה/דיבוג: מדפיס את מה שזוהה ויוצא (בלי GUI)
    if "--list" in sys.argv or "--detect" in sys.argv:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        insts = detect_all()
        print(f"Detected {len(insts)} instance(s):")
        for i in insts:
            mark = "exists" if Path(i.resourcepacks).parent.exists() else "missing"
            print(f"  [{i.launcher}] {i.name} -> {i.resourcepacks} ({mark})")
        return

    # מצב בדיקה: מדפיס אם יש חבילה מוטמעת ומה גודלה
    if "--check-embed" in sys.argv:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        emb = read_embedded_payload()
        if emb:
            print(f"EMBEDDED name={emb[0]} zip_bytes={len(emb[1])}")
        else:
            print("NO_EMBEDDED_PAYLOAD")
        return

    initial = None
    # תמיכה בגרירת ZIP על ה-EXE, או קריאה עם נתיב
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".zip"):
        initial = sys.argv[1]
    run_gui(initial)


if __name__ == "__main__":
    main()
