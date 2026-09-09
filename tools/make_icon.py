# -*- coding: utf-8 -*-
"""💎 Іконка «Апскейл» — багаторозмірний .ico (16…256), кожен розмір намальований окремо
з 8× супер-семплінгом, тому краї гладкі і на 16 px у заголовку, і на 256 px на столі.
Власник 08.09: «пікселить головний значок» — у старому .ico був лише 256 px, і Windows стискала
його сама (без згладжування).  Запуск: python tools/make_icon.py  (потрібен Pillow)."""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).with_name("apskeyl.ico")
SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
SS = 8                                                    # супер-семплінг


def draw(size: int) -> Image.Image:
    s = size * SS
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = lambda f: f * s
    # силует: корона (трапеція) + рундист + павільйон (трикутник)
    top_l, top_r, top_y = x(0.24), x(0.76), x(0.20)
    g_l, g_r, g_y = x(0.06), x(0.94), x(0.44)
    tip = (x(0.50), x(0.95))
    crown = [(top_l, top_y), (top_r, top_y), (g_r, g_y), (g_l, g_y)]
    pav = [(g_l, g_y), (g_r, g_y), tip]
    d.polygon(crown, fill=(63, 132, 232, 255))
    d.polygon(pav, fill=(31, 79, 174, 255))
    # грані корони: центральний «стіл» світліший, бокові темніші
    tl, tr = x(0.36), x(0.64)
    d.polygon([(tl, top_y), (tr, top_y), (x(0.66), g_y), (x(0.34), g_y)], fill=(124, 192, 255, 255))
    d.polygon([(top_l, top_y), (tl, top_y), (x(0.34), g_y), (g_l, g_y)], fill=(48, 110, 214, 255))
    d.polygon([(tr, top_y), (top_r, top_y), (g_r, g_y), (x(0.66), g_y)], fill=(48, 110, 214, 255))
    # грані павільйону: центральний клин світліший
    d.polygon([(x(0.34), g_y), (x(0.66), g_y), tip], fill=(47, 111, 219, 255))
    d.polygon([(x(0.42), g_y), (x(0.58), g_y), tip], fill=(77, 163, 255, 255))
    # тонкий світлий контур — читається на темному й світлому тлі
    w = max(1, s // 64)
    d.line(crown + [crown[0]], fill=(200, 228, 255, 230), width=w, joint="curve")
    d.line([(g_l, g_y), tip, (g_r, g_y)], fill=(200, 228, 255, 230), width=w, joint="curve")
    d.line([(g_l, g_y), (g_r, g_y)], fill=(230, 242, 255, 200), width=w)
    return im.resize((size, size), Image.LANCZOS)


def main() -> None:
    frames = [draw(sz) for sz in SIZES]
    frames[-1].save(OUT, format="ICO", sizes=[(sz, sz) for sz in SIZES], append_images=frames[:-1])
    chk = Image.open(OUT)
    print("записано", OUT, "розміри:", sorted(chk.info.get("sizes", {chk.size})))


if __name__ == "__main__":
    main()
