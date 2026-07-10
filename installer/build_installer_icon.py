#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
יוצר את אייקון ברירת המחדל של המתקין ואת קובץ ה-.ico שאיתו בונים את ה-stub.

חשוב: ה-.ico מכיל **תמונה יחידה בגודל קבוע 256x256, 32-bit, לא-דחוסה (BMP/DIB)**.
זה מה שמאפשר לכלי בדפדפן להחליף את בייטי האייקון ב-EXE במקום (in-place),
כי גודל ה-RT_ICON ידוע וקבוע (270376 בייטים).

הרצה:  python installer/build_installer_icon.py
פלט:   installer/installer_icon.ico  (+ installer/installer_icon_preview.png)
"""
import struct
from pathlib import Path
from PIL import Image, ImageDraw

SIZE = 256
HERE = Path(__file__).resolve().parent


def draw_default_icon() -> Image.Image:
    """אייקון ברירת מחדל: ריבוע מעוגל ירוק עם קופסה וחץ הורדה."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # רקע מעוגל עם גרדיאנט פשוט (ירוק כהה→בהיר)
    for y in range(SIZE):
        t = y / SIZE
        r = int(28 + t * 20)
        g = int(150 + t * 60)
        b = int(110 + t * 40)
        d.line([(0, y), (SIZE, y)], fill=(r, g, b, 255))
    # מסכת פינות מעוגלות
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=52, fill=255)
    img.putalpha(mask)

    d = ImageDraw.Draw(img)
    # קופסה (חבילה)
    box_top = 96
    d.rounded_rectangle([60, box_top, 196, 200], radius=14, fill=(255, 255, 255, 235))
    d.line([(128, box_top), (128, 200)], fill=(60, 170, 120, 255), width=6)
    d.line([(60, box_top + 34), (196, box_top + 34)], fill=(60, 170, 120, 255), width=6)
    # חץ הורדה למעלה
    d.rectangle([118, 40, 138, 92], fill=(255, 255, 255, 245))
    d.polygon([(100, 84), (156, 84), (128, 116)], fill=(255, 255, 255, 245))
    return img


def rgba_to_ico_dib(img: Image.Image) -> bytes:
    """ממיר תמונת RGBA 256x256 ל-DIB של אייקון (BITMAPINFOHEADER + BGRA bottom-up + AND mask אפסים)."""
    assert img.size == (SIZE, SIZE)
    img = img.convert("RGBA")
    px = img.load()
    # BITMAPINFOHEADER: biHeight = 2*H (XOR+AND), 32bit, ללא דחיסה
    header = struct.pack(
        "<IiiHHIIiiII",
        40,          # biSize
        SIZE,        # biWidth
        SIZE * 2,    # biHeight (כפול)
        1,           # biPlanes
        32,          # biBitCount
        0,           # biCompression (BI_RGB)
        SIZE * SIZE * 4,  # biSizeImage
        0, 0, 0, 0,  # ppm/colors
    )
    # נתוני צבע BGRA, שורות bottom-up
    color = bytearray()
    for y in range(SIZE - 1, -1, -1):
        for x in range(SIZE):
            r, g, b, a = px[x, y]
            color += bytes((b, g, r, a))
    # AND mask: 1 ביט לפיקסל, שורות מיושרות ל-4 בייט. לכל השקיפות דואג ה-alpha → מסכה אפסים.
    row_bytes = ((SIZE + 31) // 32) * 4  # =32 עבור 256
    and_mask = bytes(row_bytes * SIZE)
    return bytes(header) + bytes(color) + and_mask


def build_ico(dib: bytes) -> bytes:
    """עוטף DIB יחיד בקובץ .ico."""
    # ICONDIR
    out = struct.pack("<HHH", 0, 1, 1)
    # ICONDIRENTRY: width/height=0 מסמן 256
    out += struct.pack(
        "<BBBBHHII",
        0, 0, 0, 0,   # width, height, colorcount, reserved
        1, 32,        # planes, bitcount
        len(dib), 22, # bytesInRes, imageOffset (6 + 16)
    )
    return out + dib


def main():
    img = draw_default_icon()
    dib = rgba_to_ico_dib(img)
    ico = build_ico(dib)
    (HERE / "installer_icon.ico").write_bytes(ico)
    img.save(HERE / "installer_icon_preview.png")
    print(f"wrote installer_icon.ico ({len(ico)} bytes), DIB={len(dib)} bytes")
    assert len(dib) == 40 + SIZE * SIZE * 4 + ((SIZE + 31) // 32) * 4 * SIZE, "DIB size mismatch"
    print("DIB size OK (expected RT_ICON size =", len(dib), ")")


if __name__ == "__main__":
    main()
