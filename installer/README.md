# MC Pack Installer (EXE עצמאי)

מתקין ל-Windows שמזהה אוטומטית את כל ה-Minecraft instances שלך ומתקין אליהם חבילת משאבים.

## איך זה עובד — self-extracting, בלי releases
1. בונים חבילה בכלי הווב ולוחצים **"בנה מתקין EXE (עם החבילה בפנים)"**.
2. הדפדפן מוריד את בסיס המתקין ([`MC-Pack-Installer-stub.exe`](MC-Pack-Installer-stub.exe)), **מדביק את קובץ ה-ZIP של החבילה לזנב ה-EXE**, ומוריד קובץ EXE יחיד — עם החבילה כבר בפנים.
3. פשוט מורידים ומפעילים. אין קבצים נפרדים, אין הורדות נוספות.

כשה-EXE רץ הוא קורא את עצמו, מוצא את החבילה המוטמעת בזנב, מזהה instances ומתקין.

### פורמט ההטמעה
הדפדפן מוסיף לסוף ה-EXE:
```
[ stub.exe ][ block ][ footer ]
block  = name_len(2, LE) + name(utf-8) + zip_bytes
footer = "MCPKZIP1"(8) + block_len(8, LE)     ← בסוף הקובץ ממש
```
נתונים בזנב של EXE של PyInstaller אינם פוגעים בהרצה (ה-loader מתעלם מ-overlay נוסף) — נבדק.

## מה הוא מזהה
- **Minecraft רגיל** — `%APPDATA%\.minecraft`
- **CurseForge** — כל ה-instances (כולל מיקומי Documents / OneDrive)
- **Modrinth App** — כל ה-profiles
- **Prism Launcher / MultiMC / ATLauncher / GDLauncher** — מאמץ מיטבי
- כפתור **"הוסף תיקייה..."** לכל מיקום שלא זוהה אוטומטית

## שימוש
1. הפעל את ה-EXE שהורדת. אם החבילה מוטמעת — היא נבחרת אוטומטית (כתוב "חבילה מוטמעת").
2. סמן instances (יש **"בחר הכל"**), ולחץ **"התקן על הנבחרים"**.
3. במשחק: Options → Resource Packs → הפעל את החבילה.

טיפ: EXE ללא חבילה מוטמעת עדיין עובד כמתקין רגיל — בוחר אוטומטית את ה-ZIP האחרון מ-Downloads, או גוררים ZIP עליו.

מצבי דיבוג (בלי GUI): `--list` מדפיס instances שזוהו; `--check-embed` מדפיס אם יש חבילה מוטמעת.

## הפעלה מהמקור (בלי EXE)
```
python installer/mc_pack_installer.py
```
דורש Python 3.9+ עם tkinter (מגיע כברירת מחדל ב-Windows).

## בנייה מחדש של ה-stub (רק אם שינית את הקוד)
ה-stub המובנה כבר ב-repo. אם שינית את [`mc_pack_installer.py`](mc_pack_installer.py) צריך לבנות אותו מחדש:

**מקומית:**
```
pip install pyinstaller pillow
python installer/build_installer_icon.py
pyinstaller --onefile --windowed --name "MC-Pack-Installer-stub" --icon installer/installer_icon.ico installer/mc_pack_installer.py
```
העתק את `dist/MC-Pack-Installer-stub.exe` אל `installer/MC-Pack-Installer-stub.exe` ובצע commit.

**חשוב לגבי אייקון:** ה-stub נבנה עם משבצת אייקון יחידה 256×256, 32-bit, לא-דחוסה (נוצרת ע"י [`build_installer_icon.py`](build_installer_icon.py)). זה מה שמאפשר לכלי בדפדפן להחליף את אייקון ה-EXE באייקון החבילה במקום (in-place) בלי לשבור את ה-PE. אל תבנה עם `.ico` רב-גדלים או PNG-דחוס — זה ישבור את החלפת האייקון בדפדפן.

**דרך GitHub (בלי Python מקומי):**
Actions → **Build installer stub** → **Run workflow** → הורד את ה-artifact → החלף בו את הקובץ ב-`installer/` ובצע commit.

## הערת אנטי-וירוס
EXE שנבנה עם PyInstaller ואינו חתום עלול לקבל אזהרת SmartScreen ("More info" → "Run anyway") או false-positive באנטי-וירוס. הקוד פתוח וקריא כאן — אפשר לבנות בעצמך.
