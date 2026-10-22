"""YCLJ 铬白 Logo 素材构建：黑底抠图，图形与字标分开导出。

源图：纯黑背景，白色 3D 环形 + 紫粉橙渐变高光，下方 YCLJ 字标。
输出：
  mark.png / mark@2x.png  仅图形，透明底，供导航与主视觉
  lockup.png              图形 + YCLJ，供页脚或印刷场景
  favicon 套件            深底衬，保证小尺寸可辨
"""
import os
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

ROOT = r"w:\Project\公司官网"
SRC = r"c:\Users\Admin2\.trae-cn\attachments\7b1408c8-5b39-446f-88ef-2fd201d85b58_3eb4202d-a12b-4db5-9ec0-031c4ed85221_cf99cbc7c537a4ace138b4db7e96d32c.jpg"
STORE = os.path.join(ROOT, "assets", "logo", "yclj")
OUT = os.path.join(ROOT, "site", "assets", "logo", "yclj")
os.makedirs(STORE, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
SYM_BOTTOM = 946  # 字标从 y=956 开始

MADE = []


def save(img, path, colors=None, **kw):
    if colors:
        img.quantize(colors=colors, method=Image.FASTOCTREE).save(path, "PNG", optimize=True)
    else:
        img.save(path, **kw)
    MADE.append((path, os.path.getsize(path)))


def key_black(img):
    """从四边泛洪去掉与边缘连通的纯黑，保留内部黑洞（环心）"""
    a = np.array(img.convert("RGB")).astype(np.int16)
    lum = a.max(axis=2)
    H, W = lum.shape
    dark = lum < 26

    bg = np.zeros((H, W), dtype=bool)
    q = deque()
    for x in range(W):
        for y in (0, H - 1):
            if dark[y, x] and not bg[y, x]:
                bg[y, x] = True
                q.append((y, x))
    for y in range(H):
        for x in (0, W - 1):
            if dark[y, x] and not bg[y, x]:
                bg[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and dark[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True
                q.append((ny, nx))

    alpha = np.where(bg, 0, 255).astype(np.uint8)
    al = Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(0.7))
    return Image.merge("RGBA", [Image.fromarray(a[:, :, i].astype(np.uint8), "L") for i in range(3)] + [al])


def fit(img, box_w, box_h):
    s = min(box_w / img.width, box_h / img.height)
    return img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)


def tile(mark, size, ratio=.84):
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = Image.new("L", (size, size), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=round(size * .24), fill=255)
    plate = Image.new("RGBA", (size, size), (9, 10, 14, 255))
    m = fit(mark, size * ratio, size * ratio)
    plate.alpha_composite(m, ((size - m.width) // 2, (size - m.height) // 2))
    plate.putalpha(mask)
    return plate


def main():
    img = Image.open(SRC)
    cut = key_black(img)
    bbox = cut.getbbox()
    cut.save(os.path.join(STORE, "cut.png"), optimize=True)

    sym = cut.crop((bbox[0], bbox[1], bbox[2], SYM_BOTTOM))
    word = cut.crop((bbox[0], 966, bbox[2], min(bbox[3], img.height)))
    print("图形", sym.size, "字标", word.size)

    save(fit(sym, 1024, 1024), os.path.join(OUT, "mark.png"), colors=192)
    save(fit(sym, 512, 512), os.path.join(OUT, "mark-512.png"), colors=128)

    lock_h = 300
    lock_w = round(word.width * lock_h / word.height)
    gap = round(lock_h * .18)
    total_w = max(sym.width * lock_h // sym.height, lock_w)
    canvas = Image.new("RGBA", (total_w, lock_h + gap + lock_h), (0, 0, 0, 0))
    s = fit(sym, total_w, lock_h)
    canvas.alpha_composite(s, ((total_w - s.width) // 2, 0))
    w = word.resize((lock_w, lock_h), Image.LANCZOS)
    canvas.alpha_composite(w, ((total_w - w.width) // 2, lock_h + gap))
    save(canvas, os.path.join(OUT, "lockup.png"), colors=192)

    for size in (32, 48, 180, 512):
        p = tile(sym, size)
        name = "apple-touch-icon.png" if size == 180 else f"favicon-{size}.png"
        save(p, os.path.join(OUT, name), colors=64)
    Image.open(os.path.join(OUT, "favicon-48.png")).convert("RGBA").save(
        os.path.join(ROOT, "site", "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    MADE.append((os.path.join(ROOT, "site", "favicon.ico"),
                 os.path.getsize(os.path.join(ROOT, "site", "favicon.ico"))))

    total = sum(s for _, s in MADE)
    print(f"生成 {len(MADE)} 个文件，共 {total / 1024:.0f} KB")
    for p, s in MADE:
        print(f"  {os.path.relpath(p, ROOT):<50} {s / 1024:>7.1f} KB")


if __name__ == "__main__":
    main()
