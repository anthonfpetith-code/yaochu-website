"""P1 首页验收：桌面/移动截图、控制台错误、资源加载、进场动画完成度。

用法：
    python tools/verify_page.py
输出：
    _check/desktop-full.png, _check/desktop-hero.png, _check/mobile-top.png
"""
import os

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_check")
URL = "http://localhost:8899/"


def launch(p):
    try:
        return p.chromium.launch()
    except Exception:
        return p.chromium.launch(channel="msedge")


def main():
    os.makedirs(OUT, exist_ok=True)
    errors, failed = [], []

    with sync_playwright() as p:
        browser = launch(p)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("requestfailed", lambda r: failed.append(f"{r.url} :: {r.failure}"))
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(900)
        page.screenshot(path=os.path.join(OUT, "desktop-hero.png"))

        # 逐屏滚动，触发所有进场动画
        h = page.evaluate("document.body.scrollHeight")
        y = 0
        while y < h:
            page.evaluate(f"window.scrollTo(0,{y})")
            page.wait_for_timeout(260)
            y += 600
        page.evaluate("window.scrollTo(0,document.body.scrollHeight)")
        page.wait_for_timeout(700)

        stats = page.evaluate("""() => {
          const rev = [...document.querySelectorAll('[data-reveal]')];
          const imgs = [...document.images];
          return {
            revealTotal: rev.length,
            revealHidden: rev.filter(e => !e.classList.contains('is-in')).length,
            metrics: [...document.querySelectorAll('.metric__num')].map(e => e.textContent.replace(/\\s+/g,' ').trim()),
            imgsTotal: imgs.length,
            imgsBroken: imgs.filter(i => !i.complete || i.naturalWidth === 0).map(i => i.currentSrc || i.src),
            navScrolled: document.getElementById('nav').classList.contains('is-scrolled'),
            docW: document.documentElement.scrollWidth,
            winW: window.innerWidth
          };
        }""")

        page.evaluate("window.scrollTo(0,0)")
        page.wait_for_timeout(400)
        page.screenshot(path=os.path.join(OUT, "desktop-full.png"), full_page=True)

        for name, sel in [("about", "#about"), ("business", "#business"), ("dark", ".dark"),
                          ("cases", "#cases"), ("faculty", "#faculty"), ("demo", "#demos"),
                          ("contact", "#contact"), ("footer", ".footer")]:
            loc = page.locator(sel)
            loc.scroll_into_view_if_needed()
            page.wait_for_timeout(450)
            loc.screenshot(path=os.path.join(OUT, f"section-{name}.png"))

        # 移动端
        mob = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        mob.goto(URL, wait_until="networkidle")
        mob.wait_for_timeout(800)
        page_m = mob.evaluate("""() => ({
          overflowX: document.documentElement.scrollWidth > window.innerWidth,
          toggleVisible: getComputedStyle(document.getElementById('navToggle')).display !== 'none'
        })""")
        mob.screenshot(path=os.path.join(OUT, "mobile-top.png"))
        mob.click("#navToggle")
        mob.wait_for_timeout(500)
        mob.screenshot(path=os.path.join(OUT, "mobile-menu.png"))

        browser.close()

    print("== 桌面 1440x900 ==")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("== 移动 390x844 ==")
    print(f"  {page_m}")
    print(f"== 控制台错误 {len(errors)} 条 ==")
    for e in errors[:10]:
        print("  " + e)
    print(f"== 请求失败 {len(failed)} 条 ==")
    for f in failed[:10]:
        print("  " + f)


if __name__ == "__main__":
    main()
