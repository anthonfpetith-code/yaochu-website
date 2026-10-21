"""P1 素材构建：Logo 变体、讲师头像、海报去重、favicon。

用法：
    python tools/build_assets.py

输入：assets/logo/logo-source-2880.png、archive/faculty-legacy/*/photo.jpg、archive/faculty-legacy/*/poster-*.jpg
输出：site/assets/logo/*、site/assets/img/faculty/*、site/assets/img/posters/*
"""
import glob
import hashlib
import json
import os
from io import BytesIO

from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY = os.path.join(ROOT, "archive", "faculty-legacy")
SITE = os.path.join(ROOT, "site")
LOGO_SRC = os.path.join(ROOT, "assets", "logo", "logo-source-2880.png")
LOGO_OUT = os.path.join(SITE, "assets", "logo")
IMG_OUT = os.path.join(SITE, "assets", "img")
FAC_OUT = os.path.join(IMG_OUT, "faculty")
POS_OUT = os.path.join(IMG_OUT, "posters")

# 右上角绿色 R 标记的实测包围盒（内无任何黑色像素，可安全擦除）
R_BOX = (1975, 330, 2285, 620)

MADE = []


def save(img, path, **kw):
    img.save(path, **kw)
    MADE.append((path, os.path.getsize(path)))


def save_logo(img, path, colors=48):
    """Logo 只有两色，调色板量化可压到原体积的 1/8，边缘几乎无损"""
    img.quantize(colors=colors, method=Image.FASTOCTREE).save(path, "PNG", optimize=True)
    MADE.append((path, os.path.getsize(path)))


def trim(img):
    box = img.getchannel("A").getbbox()
    return img.crop(box) if box else img


def scale(img, h):
    w = round(img.width * h / img.height)
    return img.resize((w, h), Image.LANCZOS)


def recolor(img, black_to, green_to):
    """把黑色像素替换为 black_to、绿色像素替换为 green_to，保留 alpha"""
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a < 8:
                continue
            if g > r + 25 and g > b + 25:
                px[x, y] = (*green_to, a)
            elif max(r, g, b) < 70:
                px[x, y] = (*black_to, a)
    return img


def build_logo():
    os.makedirs(LOGO_OUT, exist_ok=True)
    src = Image.open(LOGO_SRC).convert("RGBA")

    # 1. 擦除 R 标记
    from PIL import ImageDraw
    d = ImageDraw.Draw(src)
    d.rectangle(R_BOX, fill=(0, 0, 0, 0))

    # 2. 按扫描线找到图形区与字标区的分界
    a = src.getchannel("A")
    rows = [y for y in range(src.height) if a.crop((0, y, src.width, y + 1)).getbbox()]
    gap_start = gap_end = None
    for y in range(rows[0], rows[-1]):
        if y not in rows:
            if gap_start is None:
                gap_start = y
            gap_end = y
        elif gap_start is not None and gap_end is not None and y - gap_end > 20:
            break
    symbol = trim(src.crop((0, 0, src.width, gap_start or src.height)))
    wordmark = trim(src.crop((0, gap_end or 0, src.width, src.height)))

    # 3. 浅底版：mark + 竖版 lockup
    save_logo(scale(symbol, 256), os.path.join(LOGO_OUT, "mark.png"))
    save_logo(scale(symbol, 512), os.path.join(LOGO_OUT, "mark@2x.png"))
    lock = Image.new("RGBA", (max(symbol.width, wordmark.width), symbol.height + wordmark.height + 80), (0, 0, 0, 0))
    lock.paste(symbol, ((lock.width - symbol.width) // 2, 0), symbol)
    lock.paste(wordmark, ((lock.width - wordmark.width) // 2, symbol.height + 80), wordmark)
    save_logo(scale(trim(lock), 640), os.path.join(LOGO_OUT, "lockup-v.png"))

    # 4. 深底版：黑转浅灰、绿提亮，保证 #0A0A0C 上可见
    dark = recolor(symbol.copy(), (245, 245, 247), (124, 203, 79))
    save_logo(scale(dark, 256), os.path.join(LOGO_OUT, "mark-dark.png"))
    dark_lock = recolor(trim(lock).copy(), (245, 245, 247), (124, 203, 79))
    save_logo(scale(dark_lock, 640), os.path.join(LOGO_OUT, "lockup-v-dark.png"))

    # 5. favicon
    for size in (16, 32, 48, 180, 512):
        icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        s = scale(symbol, round(size * 0.92))
        if s.width > size:
            s = s.crop(((s.width - size) // 2, 0, (s.width - size) // 2 + size, s.height))
        icon.paste(s, ((size - s.width) // 2, max(0, (size - s.height) // 2)), s)
        name = "apple-touch-icon.png" if size == 180 else f"favicon-{size}.png"
        save_logo(icon, os.path.join(LOGO_OUT, name), colors=64)
    Image.open(os.path.join(LOGO_OUT, "favicon-48.png")).save(
        os.path.join(SITE, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    MADE.append((os.path.join(SITE, "favicon.ico"), os.path.getsize(os.path.join(SITE, "favicon.ico"))))

    return symbol.width / symbol.height


def build_photos():
    os.makedirs(FAC_OUT, exist_ok=True)
    facts = {}
    for p in sorted(glob.glob(os.path.join(LEGACY, "*", "photo.jpg"))):
        slug = os.path.basename(os.path.dirname(p))
        im = Image.open(p).convert("RGB")
        w, h = im.size
        # 统一 4:5，裁切重心上移（人脸通常在上半部）
        out = ImageOps.fit(im, (560, 700), method=Image.LANCZOS, centering=(0.5, 0.32))
        dst = os.path.join(FAC_OUT, f"{slug}.jpg")
        save(out, dst, quality=82, optimize=True, progressive=True)
        facts[slug] = {"src": f"{w}x{h}", "ratio": round(w / h, 2)}
    return facts


def build_posters():
    os.makedirs(POS_OUT, exist_ok=True)
    seen = {}
    mapping = {}
    for p in sorted(glob.glob(os.path.join(LEGACY, "*", "poster-*.jpg"))):
        h = hashlib.md5(open(p, "rb").read()).hexdigest()[:10]
        name = os.path.basename(p).replace("poster-", "")
        if h not in seen:
            im = Image.open(p).convert("RGB")
            if im.width > 560:
                im = im.resize((560, round(im.height * 560 / im.width)), Image.LANCZOS)
            dst = os.path.join(POS_OUT, name)
            save(im, dst, quality=80, optimize=True, progressive=True)
            seen[h] = name
        mapping[name] = seen[h]
    return mapping


def main():
    ratio = build_logo()
    photos = build_photos()
    posters = build_posters()

    with open(os.path.join(ROOT, "data", "assets.json"), "w", encoding="utf-8") as f:
        json.dump({"logo_mark_ratio": round(ratio, 3),
                   "photos": photos,
                   "poster_map": posters}, f, ensure_ascii=False, indent=1)

    total = sum(s for _, s in MADE)
    print(f"生成 {len(MADE)} 个文件，共 {total / 1024:.0f} KB")
    for p, s in MADE:
        print(f"  {os.path.relpath(p, ROOT):<48} {s / 1024:>7.1f} KB")


if __name__ == "__main__":
    main()
