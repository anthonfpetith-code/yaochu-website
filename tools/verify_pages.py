"""P3 / P4 验收：师资列表、讲师详情、Demo 库。

用法：
    python tools/verify_pages.py
输出：
    _check/faculty-list.png, person.png, demos.png
"""
import os

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_check")
BASE = "http://localhost:8899"


def launch(p):
    try:
        return p.chromium.launch()
    except Exception:
        return p.chromium.launch(channel="msedge")


def audit(page, label, shot):
    errors, failed = [], []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("requestfailed", lambda r: failed.append(r.url.split("/")[-1]))
    page.goto(BASE + label, wait_until="networkidle")
    page.wait_for_timeout(800)
    h = page.evaluate("document.body.scrollHeight")
    y = 0
    while y < h:
        page.evaluate(f"window.scrollTo(0,{y})")
        page.wait_for_timeout(200)
        y += 600
    page.wait_for_timeout(600)
    data = page.evaluate("""() => {
      const rev = [...document.querySelectorAll('[data-reveal]')];
      const imgs = [...document.images];
      return {
        reveal: rev.length,
        hidden: rev.filter(e => !e.classList.contains('is-in')).length,
        imgs: imgs.length,
        broken: imgs.filter(i => !i.complete || i.naturalWidth === 0).length,
        overflow: document.documentElement.scrollWidth > window.innerWidth
      };
    }""")
    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(400)
    page.screenshot(path=os.path.join(OUT, shot), full_page=True)
    print(f"[{label}] reveal {data['reveal']}/{data['hidden']} hidden | imgs {data['imgs']} broken {data['broken']} "
          f"| overflow {data['overflow']} | console {len(errors)} | failed {len(failed)}")
    for x in errors[:5]:
        print("   ERR", x)
    return data


def main():
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        b = launch(p)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()

        # 师资列表
        audit(pg, "/faculty/", "faculty-list.png")
        pg.click('[data-filter="founder"]')
        pg.wait_for_timeout(400)
        vis = pg.evaluate("""() => ({
          founders: [...document.querySelectorAll('.fcard')].filter(e => e.offsetParent).length,
          mentors: [...document.querySelectorAll('.mcard')].filter(e => e.offsetParent).length
        })""")
        print("   筛选创始人 ->", vis)
        pg.click('[data-filter="all"]')

        # 详情
        audit(pg, "/faculty/chenqichang/", "person.png")
        pg.wait_for_timeout(200)

        # Demo
        pg2 = ctx.new_page()
        video_req = []
        pg2.on("request", lambda r: video_req.append(r.url) if ".mp4" in r.url else None)
        audit(pg2, "/demos/", "demos.png")
        print(f"   首屏 mp4 请求数 {len(video_req)}")
        pg2.click(".vcard")
        pg2.wait_for_timeout(900)
        opened = pg2.evaluate("""() => ({
          open: document.getElementById('modal').classList.contains('is-open'),
          src: !!document.getElementById('player').getAttribute('src'),
          title: document.getElementById('modalTitle').textContent
        })""")
        print("   弹层:", opened)
        pg2.keyboard.press("Escape")
        pg2.wait_for_timeout(300)
        print("   ESC 关闭:", not pg2.evaluate("document.getElementById('modal').classList.contains('is-open')"))

        # 移动端
        mob = b.new_page(viewport={"width": 390, "height": 844})
        for path in ("/faculty/", "/faculty/chenqichang/", "/demos/"):
            mob.goto(BASE + path, wait_until="networkidle")
            mob.wait_for_timeout(500)
            print(f"   移动端 {path} 横向溢出:", mob.evaluate("document.documentElement.scrollWidth > window.innerWidth"))
        mob.goto(BASE + "/faculty/", wait_until="networkidle")
        mob.wait_for_timeout(600)
        mob.screenshot(path=os.path.join(OUT, "mobile-faculty.png"))
        mob.goto(BASE + "/faculty/chenqichang/", wait_until="networkidle")
        mob.wait_for_timeout(600)
        mob.screenshot(path=os.path.join(OUT, "mobile-person.png"))
        b.close()


if __name__ == "__main__":
    main()
