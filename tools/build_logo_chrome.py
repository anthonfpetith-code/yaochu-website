"""铬金 Logo 素材构建：白底抠图 + 深色底衬 + favicon。

材质：银色镜面主体 + 香槟金边，背景接近纯白(254)。
白色金属放在白底上会消失，因此网页素材一律配深色底衬。
"""
import os
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = r"w:\Project\公司官网"
SRC = r"c:\Users\Admin2\.trae-cn\attachments\76bf59b2-29ef-4da5-ac3a-60cc6e7a6856_4de204c3-186c-4f36-8d30-fd1df425f5cf_fffdd302d66c30bb8b3dfdab6b849228.jpg"
STORE = os.path.join(ROOT, "assets", "logo", "chrome")
OUT = os.path.join(ROOT, "site", "assets", "logo", "chrome")
os.makedirs(STORE, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

MADE = []


def save(img, path, colors=None, **kw):
    if colors:
        img.quantize(colors=colors, method=Image.FASTOCTREE).save(path, "PNG", optimize=True)
    else:
        img.save(path, **kw)
    MADE.append((path, os.path.getsize(path)))


def cutout():
    """从四边泛洪，只去掉与边缘连通的近白像素；金属高光保留"""
    img = Image.open(SRC).convert("RGB")
    a = np.array(img).astype(np.int16)
    lum = a.mean(axis=2)
    H, W = lum.shape
    near_white = lum >= 249

    bg = np.zeros((H, W), dtype=bool)
    q = deque()
    for x in range(W):
        for y in (0, H - 1):
            if near_white[y, x] and not bg[y, x]:
                bg[y, x] = True
                q.append((y, x))
    for y in range(H):
        for x in (0, W - 1):
            if near_white[y, x] and not bg[y, x]:
                bg[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and near_white[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True
                q.append((ny, nx))

    alpha = np.where(bg, 0, 255).astype(np.uint8)
    # 先向内收 1px 再羽化：去掉金属边缘残留的白边
    al = Image.fromarray(alpha, "L").filter(ImageFilter.MinFilter(3))
    al = al.filter(ImageFilter.GaussianBlur(0.7))
    out = Image.merge("RGBA", [Image.fromarray(np.array(img)[:, :, i], "L") for i in range(3)] + [al])
    box = out.getchannel("A").getbbox()
    out = out.crop(box)
    print("抠图后尺寸", out.size, "| 背景覆盖率", round(bg.mean() * 100, 1), "%")
    out.save(os.path.join(STORE, "mark-cut.png"), optimize=True)
    return out


def fit(img, box_w, box_h):
    s = min(box_w / img.width, box_h / img.height)
    return img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)


def plate(mark, size, bg=(8, 8, 10), ratio=0.82, radius=0.24):
    """深色圆角底衬 + 柔和内光"""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    r = round(size * radius)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=(*bg, 255))

    # 顶部微光
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-size * .3, -size * .55, size * 1.3, size * .5], fill=(255, 255, 255, 26))
    glow = glow.filter(ImageFilter.GaussianBlur(size * .07))
    canvas.alpha_composite(glow)

    m = fit(mark, size * ratio, size * ratio)
    x = (size - m.width) // 2
    y = (size - m.height) // 2
    canvas.alpha_composite(m, (x, y))

    # 圆角裁切
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=255)
    canvas.putalpha(mask)
    return canvas


def hero_plate(mark, w, h):
    bg = Image.new("RGB", (w, h), (10, 10, 13))
    d = ImageDraw.Draw(bg)
    d.ellipse([-w * .25, -h * .45, w * 1.25, h * .95], fill=(18, 18, 23))
    d.ellipse([w * .06, h * .04, w * .94, h * .98], fill=(27, 27, 34))
    bg = bg.filter(ImageFilter.GaussianBlur(w * .05))
    m = fit(mark, w * .78, h * .78)
    bg.paste(m, ((w - m.width) // 2, (h - m.height) // 2), m)
    return bg


def main():
    mark = cutout()

    save(plate(mark, 256, ratio=.80), os.path.join(OUT, "plate-256.png"), colors=96)
    save(plate(mark, 512, ratio=.80), os.path.join(OUT, "plate-512.png"), colors=128)
    save(plate(mark, 1024, ratio=.80), os.path.join(OUT, "plate-1024.png"), colors=160)
    save(plate(mark, 512, ratio=.86, radius=.5), os.path.join(OUT, "plate-round.png"), colors=96)

    # 透明图形（供深色页面直接摆放）
    save(fit(mark, 1024, 1024), os.path.join(OUT, "mark.png"), colors=192)
    save(hero_plate(mark, 1200, 900), os.path.join(OUT, "hero-plate.jpg"),
         quality=88, optimize=True, progressive=True)

    # favicon
    for size in (32, 48, 180, 512):
        p = plate(mark, size, ratio=.80, radius=.24)
        name = "apple-touch-icon.png" if size == 180 else f"favicon-{size}.png"
        save(p, os.path.join(OUT, name), colors=64)
    Image.open(os.path.join(OUT, "favicon-48.png")).convert("RGBA").save(
        os.path.join(ROOT, "site", "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    MADE.append((os.path.join(ROOT, "site", "favicon.ico"),
                 os.path.getsize(os.path.join(ROOT, "site", "favicon.ico"))))

    total = sum(s for _, s in MADE)
    print(f"生成 {len(MADE)} 个文件，共 {total / 1024:.0f} KB")
    for p, s in MADE:
        print(f"  {os.path.relpath(p, ROOT):<52} {s / 1024:>7.1f} KB")


if __name__ == "__main__":
    main()
