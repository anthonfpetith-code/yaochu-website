"""新 Logo（panomovo）素材构建：从黑底原图提取图形并生成网页素材。

源图特征：
- 纯黑背景，白色 3D 形体，内部一道彩色渐变折页，两个纯黑"眼睛"
- 下方有 panomovo / 灵境奇幕 字标，本流程不使用

处理：
1 从画布四边泛洪，只有与边缘连通的暗像素算背景
2 眼睛属于前景，保留为不透明
3 边缘轻微羽化，避免锯齿

用法：
    python tools/build_logo_panomovo.py
"""
import base64
import os
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "logo", "panomovo", "source-1254.png")
RAW = os.path.join(ROOT, "assets", "logo", "panomovo", "mark-raw.png")
OUT = os.path.join(ROOT, "site", "assets", "logo", "panomovo")
SYM_BOTTOM = 760  # 字标从 y≈785 开始，这里切在图形与文字之间

MADE = []


def save(img, path, colors=None, **kw):
    if colors:
        img.quantize(colors=colors, method=Image.FASTOCTREE).save(path, "PNG", optimize=True)
    else:
        img.save(path, **kw)
    MADE.append((path, os.path.getsize(path)))


def extract():
    img = Image.open(SRC).convert("RGB")
    a = np.array(img).astype(np.int16)
    lum = a.max(axis=2)
    H, W = lum.shape
    dark = lum < 38

    bgl = np.zeros((H, W), dtype=bool)
    q = deque()
    for x in range(W):
        for y in (0, H - 1):
            if dark[y, x] and not bgl[y, x]:
                bgl[y, x] = True
                q.append((y, x))
    for y in range(H):
        for x in (0, W - 1):
            if dark[y, x] and not bgl[y, x]:
                bgl[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and dark[ny, nx] and not bgl[ny, nx]:
                bgl[ny, nx] = True
                q.append((ny, nx))

    obj = ~bgl
    ys, xs = np.where(obj)
    keep = ys < SYM_BOTTOM
    ys, xs = ys[keep], xs[keep]
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()

    alpha = np.where(bgl, 0, 255).astype(np.uint8)[y0:y1 + 1, x0:x1 + 1]
    rgb = a[y0:y1 + 1, x0:x1 + 1].astype(np.uint8)
    al = Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(0.6))
    out = Image.merge("RGBA", [Image.fromarray(rgb[:, :, i], "L") for i in range(3)] + [al])
    out.save(RAW, optimize=True)
    print("提取图形", out.size, round(os.path.getsize(RAW) / 1024, 1), "KB")
    return out


def padded(img, ratio, h):
    w = round(img.width * h / img.height)
    s = img.resize((w, h), Image.LANCZOS)
    side = round(max(w, h) * (1 + ratio * 2))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(s, ((side - w) // 2, (side - h) // 2), s)
    return canvas


def build(src):
    os.makedirs(OUT, exist_ok=True)

    save(src.resize((512, round(512 * src.height / src.width)), Image.LANCZOS),
         os.path.join(OUT, "mark.png"), colors=128)
    save(src.resize((1024, round(1024 * src.height / src.width)), Image.LANCZOS),
         os.path.join(OUT, "mark@2x.png"), colors=192)
    save(padded(src, 0.10, 512), os.path.join(OUT, "mark-pad.png"), colors=128)
    save(padded(src, 0.10, 1024), os.path.join(OUT, "mark-pad@2x.png"), colors=192)

    # 小尺寸下白色形体容易糊，favicon 用深底衬
    for size in (32, 48, 180, 512):
        plate = Image.new("RGBA", (size, size), (13, 16, 22, 255))
        s = src.resize((round(size * 0.82), round(size * 0.82 * src.height / src.width)), Image.LANCZOS)
        plate.paste(s, ((size - s.width) // 2, (size - s.height) // 2), s)
        name = "apple-touch-icon.png" if size == 180 else f"favicon-{size}.png"
        save(plate, os.path.join(OUT, name), colors=64)

    Image.open(os.path.join(OUT, "favicon-48.png")).convert("RGBA").save(
        os.path.join(ROOT, "site", "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    MADE.append((os.path.join(ROOT, "site", "favicon.ico"),
                 os.path.getsize(os.path.join(ROOT, "site", "favicon.ico"))))

    og = Image.new("RGB", (1200, 630), (255, 255, 255))
    m = src.resize((430, round(430 * src.height / src.width)), Image.LANCZOS)
    og.paste(m, ((1200 - m.width) // 2, (630 - m.height) // 2 - 20), m)
    save(og, os.path.join(OUT, "og-cover.jpg"), quality=88, optimize=True, progressive=True)

    d = np.array(src.copy()).astype(float)
    vis = d[:, :, 3] > 128
    d[:, :, :3][vis] = np.clip(d[:, :, :3][vis] * 1.06 + 6, 0, 255)
    dark = Image.fromarray(d.astype(np.uint8), "RGBA")
    save(dark, os.path.join(OUT, "mark-dark.png"))


def main():
    os.makedirs(os.path.dirname(RAW), exist_ok=True)
    if not os.path.exists(SRC):
        raise SystemExit(f"缺少源图：{SRC}")
    src = extract()
    build(src)
    total = sum(s for _, s in MADE)
    print(f"生成 {len(MADE)} 个文件，共 {total / 1024:.0f} KB")
    for p, s in MADE:
        print(f"  {os.path.relpath(p, ROOT):<58} {s / 1024:>7.1f} KB")


if __name__ == "__main__":
    main()
