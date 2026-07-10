# מחקר: Minecraft Resource Packs — מבנה, טעינה, כלים והפצה

## מטרת המחקר
לתחקר לעומק כיצד resource packs במיינקראפט (Java Edition) בנויים מבחינה טכנית, כיצד המשחק טוען וממזג אותם, אילו כלים ואוטומציה קיימים ליצירה וניהול שלהם, וכיצד הם מופצים ומותקנים — כבסיס ידע לפני עבודה נרחבת על פרויקט ניהול resource packs.

## תשובה מרוכזת
Resource pack הוא ארכיון (תיקייה או ZIP) שמזוהה על ידי קובץ `pack.mcmeta` בשורש שלו, ומכיל תיקיית `assets/<namespace>/` עם טקסטורות, מודלים, סאונדים, פונטים וטקסטים שמחליפים או מוסיפים לנכסי ברירת המחדל של המשחק. מיינקראפט טוען את כל ה-packs הפעילים כ"מחסנית" (stack) — ה-pack העליון ברשימה גובר על התחתונים, ופאק ברירת המחדל (vanilla) תמיד יושב בתחתית כבסיס. כל pack מוצהר עם מספר גרסת פורמט (`pack_format`, ולאחרונה `min_format`/`max_format`) שקובע תאימות לגרסת המשחק. קיימת אקוסיסטמת כלים עשירה (Blockbench, MCreator, PackSquash, packwiz ועוד) ליצירה, אופטימיזציה וניהול, וערוצי הפצה סטנדרטיים (Modrinth, CurseForge, PlanetMinecraft) לצד הפצה ישירה משרת דרך `server.properties`.

---

## 1. מבנה קבצים טכני ופורמט

### מבנה תיקיות בסיסי
```
ResourcePackName/
├── pack.mcmeta          (חובה — מזהה את ה-pack)
├── pack.png              (אופציונלי — אייקון, כל רזולוציה ריבועית בחזקת 2, מומלץ 128×128)
└── assets/
    └── <namespace>/      (למשל "minecraft" לדריסת קבצי ברירת מחדל, או namespace מותאם אישית)
        ├── blockstates/  (הגדרות מצבי בלוק בפורמט JSON)
        ├── models/
        │   ├── block/
        │   └── item/
        ├── textures/
        │   ├── block/
        │   ├── item/
        │   └── entity/
        ├── items/        (החל מ-1.21.2 — הגדרות item model חדשות)
        ├── sounds/       (קבצי .ogg)
        ├── sounds.json
        ├── lang/         (למשל en_us.json)
        ├── font/
        ├── particles/
        ├── shaders/
        └── texts/
```
כל שמות הקבצים בפאק חייבים להיות באותיות קטנות (מאז 1.11). [Tutorial:Creating a resource pack](https://minecraft.wiki/w/Tutorial:Creating_a_resource_pack)

### pack.mcmeta — המפרט המלא
קובץ ה-JSON הזה הוא שמזהה תיקייה/ZIP כ-resource pack או data pack. [pack.mcmeta – Minecraft Wiki](https://minecraft.wiki/w/Pack.mcmeta)

שדות עיקריים תחת האובייקט `pack`:
- **description** (מחרוזת/text component) — מוצג בריחוף מעל שם הפאק.
- **pack_format** (מספר שלם) — גרסת הפורמט העיקרית (עדיין הדרך הנפוצה כיום ברוב הגרסאות).
- **min_format** / **max_format** (מספר שלם או מערך) — טווח גרסאות נתמכות. **⚠️ שינוי משמעותי**: החל מ-25w31a (וממשיך בפורמט "year.drop" של 2026), `pack_format` הפך לאופציונלי, והוחלף כברירת מחדל ב-`min_format`/`max_format`. [pack.mcmeta – Minecraft Wiki](https://minecraft.wiki/w/Pack.mcmeta)
- **supported_formats** — הוסר החל מ-25w31a (הוחלף ב-min/max_format).
- **filter.block** — מסנן קבצים מ-packs שנטענו לפניו, לפי regex על namespace/path (נוסף ב-1.19).
- **overlays.entries** — תת-פאקים (overlay directories) שמופעלים מעל התוכן הרגיל בהתאם לגרסת המשחק, כל אחד עם `directory`, `min_format`, `max_format` משלו (נוסף ב-1.20.2/23w31a).
- **language** — (resource packs בלבד) מוסיף שפות לתפריט השפה, עם `name`, `region`, `bidirectional`.
- **features.enabled** — הפעלת דגלי פיצ'רים ניסיוניים.

### טבלת גרסאות פורמט (pack_format) — עדכני ל-2026
| pack_format (resource) | גרסת Java | הערות |
|---|---|---|
| 32 | 1.20.5–1.20.6 | טקסטורות שריון זאב |
| 34 | 1.21–1.21.1 | סאונדים חדשים, תקליטים |
| 42 | 1.21.2–1.21.3 | equipment models, tooltips מותאמים |
| 55 | 1.21.5 | wildflowers, עלים נופלים |
| 63 | 1.21.6 | פרמטר blur לטקסטורות |
| 69.0 | 1.21.9–1.21.10 | מערכת minor-version, OpenGL 3.3 נדרש |
| 75.0 | 1.21.11 | עדכוני Unifont, mipmap strategy |
| 84.0 | 26.1 (Tiny Takeover, 24.3.2026) | ראה סעיף שינוי מספור להלן |

[Pack format – Minecraft Wiki](https://minecraft.wiki/w/Pack_format), [Java Edition 26.1 – Minecraft Wiki](https://minecraft.wiki/w/Java_Edition_26.1)

**⚠️ הערה חשובה — שינוי שיטת המספור ב-2026**: החל מ-Minecraft 26.1 ("Tiny Takeover", יצא ב-24 במרץ 2026), מספרי הגרסאות של המשחק עצמו עברו לפורמט `שנה.דרופ.hotfix` (למשל 26.1, 26.2) במקום 1.21.x. זהו שינוי נפרד ממספרי pack_format, אך רלוונטי מאוד לזיהוי תאימות: כל resource pack manager שמסתמך על "1.21" כפורמט גרסה אחרון צריך להתעדכן לתמוך גם ב-26.x. גרסת 26.1 היא הגרסה הראשונה שיצאה ללא גרסה מעורפלת (unobfuscated) נלווית. [Minecraft new version numbering system – Minecraft.net](https://www.minecraft.net/en-us/article/minecraft-new-version-numbering-system), [Java Edition 26.1 – Minecraft Wiki](https://minecraft.wiki/w/Java_Edition_26.1)

בדיקת פורמט בפועל: ניתן לבדוק את pack_format הנוכחי במשחק דרך F3+V או `/version`.

---

## 2. איך המשחק טוען וממזג packs (ה-Stack)

- Resource packs נטענים כ**מחסנית (stack)**: "ה-pack התחתון ביותר נטען ראשון, ולאחר מכן כל pack מעליו מחליף או ממזג נכסים עם אלו שהוא מכיל." [Resource pack – Minecraft Wiki](https://minecraft.wiki/w/Resource_pack)
- ה-**default pack** (וניל) הוא תמיד הבסיס בתחתית המחסנית — הוא נבחר אוטומטית ולא ניתן לבטל את בחירתו. הוא מורכב מ-assets שבתוך `client.jar` וממאגר האובייקטים (asset object store).
- שלושה packs מובנים ב-Java Edition: **Default** (חובה), **Programmer Art** (טקסטורות ישנות טרום-1.14), **High Contrast** (נגישות).
- כאשר קובץ באותו נתיב קיים בכמה packs — **ה-pack הגבוה יותר ברשימה גובר**. אם קובץ לא קיים ב-pack מסוים, המשחק נופל חזרה (fallback) לפאק הבא למטה, ובסופו של דבר ל-vanilla.
- קבצים שקיימים רק ב-pack אחד תמיד עוברים ללא שינוי.
- ב-**Bedrock Edition** ההתנהגות דומה: "הפאק התחתון ביותר נטען ראשון, וכל פאק שמעליו מחליף נכסים בעלי אותו שם." משאבים גלובליים (global resources) תמיד מופעלים מעל world resource packs. [Resource pack – Minecraft Wiki](https://minecraft.wiki/w/Resource_pack)
- **Overlays** (מ-1.20.2 ואילך): תת-תיקיות בתוך אותו pack שמופעלות אוטומטית בהתאם לגרסת המשחק, בלי צורך ב-pack נפרד לכל טווח תאימות. ה-overlays מתעלמים מ-`pack.mcmeta`/`pack.png` משלהם.
- **פאק ברמת עולם (`resources.zip`)**: ניתן לצרף resource pack לעולם ספציפי על ידי הצבת `resources.zip` בתיקיית העולם — הוא נטען מיד מעל ה-default pack, אך **לא מופץ** לשחקנים אחרים דרך LAN.

---

## 3. מודלים, Blockstates ומערכת ה-Item Models (שינוי גדול ב-1.21.4+)

### Blockstates
קבצי JSON תחת `assets/<namespace>/blockstates/` המגדירים אילו מודלים משמשים לכל מצב של בלוק. שני פורמטים:
- **variants** — כל וריאנט הוא שם המורכב ממצבי בלוק מופרדים בפסיקים (בלוק עם מצב יחיד משתמש ב-`""`), עם מודל אחד או מערך מודלים.
- **multipart** — במקום variants, משלב כמה מודלים בהתאם לתנאי `when`; אם `when` לא מוגדר, המודל תמיד חל. דוגמה: גדר עץ (fence) — מודל ה"עמוד" תמיד מוצג, ומודלי החיבורים הצדדיים מותנים בבלוקים סמוכים. [Blockstates definition – Minecraft Wiki](https://minecraft.wiki/w/Blockstates_definition)

מאפייני מודל בתוך blockstate: `model` (נתיב), `x`/`y`/`z` (סיבוב בקפיצות של 90 מעלות).

### ⚠️ שינוי גדול: החלפת מערכת ה-Overrides/Predicates
עד 1.21.4, item models השתמשו במערכת `overrides` עם `predicates` בתוך קובץ `model.json` כדי לבחור מודל שונה לפי תנאים (damage, custom_model_data וכו'). **מ-1.21.4 (24w45a) ואילך, מערכת זו הוסרה לגמרי** והוחלפה ב-**items model definition** חדשה. [Items model definition – Minecraft Wiki](https://minecraft.wiki/w/Items_model_definition)

מיקום: `assets/<namespace>/items/*.json`, מקושר דרך רכיב ה-data component `item_model`.

סוגי מודל עיקריים במערכת החדשה:
- **model** — מודל רגיל מתוך `models/`, עם tint sources אופציונליים (constant, dye, firework, grass, map_color, potion, team, custom_model_data).
- **composite** — מציג כמה תתי-מודלים יחד באותו מרחב.
- **condition** — ענפי on_true/on_false לפי תכונות בוליאניות (broken, component, damaged, selected, using_item...).
- **select** — בחירת מודל לפי ערך דיסקרטי (block_state, charge_type, display_context, main_hand, trim_material...).
- **range_dispatch** — בוחר את הערך הגבוה ביותר שעדיין ≤ מהתכונה המספרית.
- **special** — מודלים מיוחדים מובְנים (banner, bell, book, chest, head, shield, shulker_box, trident).
- **empty** — לא מציג דבר.

זהו שינוי ארכיטקטוני משמעותי מאוד לכל כלי אוטומציה/ניהול resource packs — קוד שמניח את מבנה ה-`overrides` הישן לא יעבוד על גרסאות עדכניות.

---

## 4. Data Packs מול Resource Packs

| | Resource Pack | Data Pack |
|---|---|---|
| שולט ב | טקסטורות, מודלים, סאונד, פונטים, שפה — כל מה שרואים/שומעים | התקדמות (advancements), מימדים, הקסמים, loot tables, מתכונים, מבנים, ביומים — לוגיקת משחק |
| מיקום | תיקיית `resourcepacks` (גלובלי, חוצה-עולמות) | `saves/<world>/datapacks` (ספציפי לעולם) |
| מבנה משותף | שניהם משתמשים ב-`pack.mcmeta` ומערכת `pack_format` דומה | כנ"ל |
| טעינה מחדש | דורש בדרך כלל restart של הלקוח | ניתן ברוב המקרים באמצעות `/reload` תוך כדי משחק |

[Data pack – Minecraft Wiki](https://minecraft.wiki/w/Data_pack)

---

## 5. הפצה, שרתים והתקנה

### שרת (Server-side)
- מגדירים `resource-pack` ב-`server.properties` לכתובת URL של קובץ ZIP.
- יש לחשב **SHA-1** של קובץ ה-ZIP ולהזין ב-`resource-pack-sha1` (יש לעדכן בכל העלאה מחדש).
- `require-resource-pack=true` — מכריח שחקנים לקבל את הפאק; דחייה מנתקת אותם מהשרת.
- [Resource pack – Minecraft Wiki](https://minecraft.wiki/w/Resource_pack), [server.properties – Minecraft Wiki](https://minecraft.wiki/w/Server.properties)

### התקנה אצל שחקן (.minecraft/resourcepacks)
- כל resource pack חייב להיות **תיקייה** או קובץ **.zip** בודד בתוך `.minecraft/resourcepacks`.
- **מבנה ה-ZIP קריטי**: יש לדחוס את תיקיית `assets/` יחד עם `pack.mcmeta` ו-`pack.png` ישירות בשורש ה-ZIP — **בלי** תיקיית-עטיפה נוספת מסביב, אחרת המשחק לא יזהה את הפאק.
- אין לחלץ (unzip) את הקובץ אלא אם היוצר הנחה לעשות זאת.

### פלטפורמות הפצה
- **Modrinth**, **CurseForge**, **PlanetMinecraft** — הפלטפורמות המרכזיות. שתי הראשונות דורשות בדרך כלל לפחות תמונה אחת בתיקיית `images/` ומטא-דאטה תקין (כולל `pack.mcmeta` תקף) כדי לאשר פרויקט.
- כלי **PackUploader** (קוד פתוח, GitHub) מאפשר להעלות pack אחד בו-זמנית ל-CurseForge, Modrinth ו-PlanetMinecraft. [GitHub - ewanhowell5195/PackUploader](https://github.com/ewanhowell5195/PackUploader)

---

## 6. כלים ואוטומציה ליצירה וניהול

מתוך [Tutorial:Programs and editors/Resource pack creators – Minecraft Wiki](https://minecraft.wiki/w/Tutorial:Programs_and_editors/Resource_pack_creators) ומקורות נוספים:

| כלי | סוג | תיאור |
|---|---|---|
| **Blockbench** | עורך מודלים (Win/Mac/Linux/Web) | הכלי המוביל ליצירת מודלים, טקסטורות ואנימציות ל-blocks/items/entities, מייצא ל-JSON תואם-מודל. |
| **MCreator** | סביבת יצירה משולבת | עורך טקסטורות + עורך קוד, מציג את מבנה ה-vanilla ומאפשר דריסת קבצים בגרירה. |
| **PackSquash** | אופטימיזציה/דחיסה | דוחס resource packs להקטנת גודל קובץ וזמן טעינה, כולל הגנה מפני חילוץ. |
| **json_tool** | ניהול קבצי שפה (Python) | איתור כפילויות, השוואת קבצי lang ואוטומציה של שינויים. |
| **PackCrafter** | בונה מבוסס-דפדפן | יצירת פאק מלא בדפדפן, עריכת טקסטורות, אנימציה, תצוגה תלת-ממדית, שיוך סאונד. |
| **Resource Pack Creator** | עורך מבוסס-דפדפן | עריכת בלוקים/פריטים/מובים בדפדפן עם ייצוא ZIP ל-Java ו-Bedrock. |
| **Resource Pack Utilities** | תוסף ל-Blockbench | אוסף כלי עזר לפיתוח resource packs. |
| **Minecraft Creator Tools** | CLI מבוסס-NPM (Bedrock) | כלי שורת-פקודה עם **validators** לאיתור בעיות בפרויקט. |
| **packwiz** | CLI לניהול modpacks (Go) | מנהל מודים/פאקים כקבצי TOML ידידותיים ל-git, עם עדכונים אוטומטיים מ-CurseForge/Modrinth וייצוא לפורמט modpack. [GitHub - packwiz/packwiz](https://github.com/packwiz/packwiz) |

**הערה לפרויקט ניהול resource packs**: כלים כמו packwiz ו-PackSquash מדגימים שני דפוסי-על שימושיים לכלי ניהול: (א) ייצוג המטא-דאטה כקבצי טקסט ידידותיים לגיט (TOML/JSON) במקום בינארי, ו-(ב) שלב build/אופטימיזציה נפרד בין "מקור" ל"תפוצה" (למשל דחיסה, אימות SHA-1, בדיקת התאמת pack_format).

---

## 7. פרטי פורמט נוספים (רלוונטי לכלי אימות/ניהול)

- **אנימציית טקסטורה**: קובץ `<texture>.png.mcmeta` (למשל `stone.png.mcmeta`) עם שדות `interpolate` (ברירת מחדל false), `width`, `height`, `frametime` (ברירת מחדל 1 טיק), ו-`frames` (ברירת מחדל: כל הפריימים בסדר). [Resource pack – Minecraft Wiki](https://minecraft.wiki/w/Resource_pack)
- **sounds.json**: ממוקם ב-`assets/<namespace>/sounds.json`. מפתחות = מזהי אירועי סאונד; לכל אירוע — מערך `sounds` (קובץ אחד נבחר אקראית בכל הפעלה, עם משקל `weight` אופציונלי), `replace` (האם להחליף לגמרי את רשימת ברירת המחדל או להוסיף אליה), ו-`subtitle` (מפתח תרגום לכתוביות). [sounds.json – Minecraft Wiki](https://minecraft.wiki/w/Sounds.json)
- **splashes.txt**: שורות טקסט (מופרדות ב-LF) שמופיעות כ"הבזקים" צהובים במסך הבית.
- **credits.json**: פורמט JSON לרשימת הקרדיטים המוצגת אחרי ה-End Poem.
- **font**: קובץ JSON ב-`assets/<namespace>/font` המכיל רשימת "providers" שמגדירים כיצד כל תו מוצג.
- **pack.png**: כל רזולוציה ריבועית בחזקת 2 עובדת (32×32, 64×64, 128×128...), אך 128×128 מומלץ לאיזון בין איכות לגודל קובץ. [MC-157906 – Mojang Bug Tracker](https://bugs.mojang.com/browse/MC-157906)

---

## אי-ודאויות וסתירות שזוהו

- ⚠️ **גודל pack.png**: מקור אחד ציין "64×64 או 128×128", מקור שני ציין "כל רזולוציה ריבועית בחזקת 2". נפתר: הדרישה בפועל היא ריבוע בחזקת 2 (כולל 128×128), עם 128×128 כהמלצה — אין דרישה נוקשה ל-64×64 בלבד.
- ⚠️ **תוכן הטבלה של pack_format לגרסאות 26.x**: תוצאות החיפוש הראשוניות הראו ערכים לא-אחידים (למשל 88.0 מול 101.1 מול 84.0 עבור אותה טווח גרסאות) מכיוון שדף ה-Wiki מתעדכן באופן שוטף ומכיל גם התייחסות ל-data pack format וגם resource pack format בטבלאות נפרדות שהתערבבו בסיכום הראשוני. הנתון המאומת מהעמוד הייעודי של Java Edition 26.1 הוא: **resource pack format = 84.0, data pack format = 101.1** לגרסת 26.1 (Tiny Takeover, 24.3.2026). מומלץ לבדוק את [Pack format – Minecraft Wiki](https://minecraft.wiki/w/Pack_format) ישירות בטרם קידוד קשיח (hardcoding) של מספרים אלה בכלי ניהול, מכיוון שהם משתנים בכל דרופ.

---

## מקורות
1. [pack.mcmeta – Minecraft Wiki](https://minecraft.wiki/w/Pack.mcmeta)
2. [Pack format – Minecraft Wiki](https://minecraft.wiki/w/Pack_format)
3. [Resource pack – Minecraft Wiki](https://minecraft.wiki/w/Resource_pack)
4. [Tutorial:Creating a resource pack – Minecraft Wiki](https://minecraft.wiki/w/Tutorial:Creating_a_resource_pack)
5. [Items model definition – Minecraft Wiki](https://minecraft.wiki/w/Items_model_definition)
6. [Blockstates definition – Minecraft Wiki](https://minecraft.wiki/w/Blockstates_definition)
7. [Data pack – Minecraft Wiki](https://minecraft.wiki/w/Data_pack)
8. [Sounds.json – Minecraft Wiki](https://minecraft.wiki/w/Sounds.json)
9. [Server.properties – Minecraft Wiki](https://minecraft.wiki/w/Server.properties)
10. [Java Edition 26.1 – Minecraft Wiki](https://minecraft.wiki/w/Java_Edition_26.1)
11. [Minecraft new version numbering system – Minecraft.net](https://www.minecraft.net/en-us/article/minecraft-new-version-numbering-system)
12. [Tutorial:Programs and editors/Resource pack creators – Minecraft Wiki](https://minecraft.wiki/w/Tutorial:Programs_and_editors/Resource_pack_creators)
13. [GitHub - packwiz/packwiz](https://github.com/packwiz/packwiz)
14. [GitHub - ewanhowell5195/PackUploader](https://github.com/ewanhowell5195/PackUploader)
15. [MC-157906 – Mojang Bug Tracker](https://bugs.mojang.com/browse/MC-157906)

*תאריך איסוף המקורות: 10 ביולי 2026.*

## האם המטרה הושגה?
**כן, במלואה** — כל ארבעת תחומי המיקוד שנבחרו (מבנה טכני, טעינה ומיזוג, כלים ואוטומציה, הפצה והתקנה) כוסו לעומק עם מקורות מאומתים מה-Minecraft Wiki הרשמי ומקורות משניים אמינים. נמצא גם מידע קריטי ובלתי-צפוי לפרויקט: השינוי הגדול במערכת ה-item models (הסרת overrides/predicates לטובת items model definition) והמעבר של מיינקראפט עצמו לשיטת מספור גרסאות מבוססת-שנה (26.x) — שני שינויים שחשוב שכלי ניהול resource packs יתחשב בהם.
