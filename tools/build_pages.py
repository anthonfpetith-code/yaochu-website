"""P3 / P4 页面生成：师资列表、14 个讲师详情、Demo 作品库。

用法：
    python tools/build_pages.py

输入：data/faculty.json、data/site.json、data/demos.json
输出：site/faculty/index.html、site/faculty/<slug>/index.html、site/demos/index.html
"""
import json
import os
import re
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
DATA = os.path.join(ROOT, "data")

ARROW = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
         'stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>')
PLAY = '<svg viewBox="0 0 24 24"><path d="m8 5 11 7-11 7Z"/></svg>'
CLOSE = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
         'stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>')
MENU = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>')
DOWNLOAD = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
            '<path d="m7 10 5 5 5-5"/><path d="M12 15V3"/></svg>')


def e(x):
    return escape(str(x or ""), quote=True)


def nav(prefix, dark=False, current=""):
    cls = "nav nav--solid" if not dark else "nav nav--dark"
    mark = f"{prefix}assets/logo/mark-dark.png" if dark else f"{prefix}assets/logo/mark.png"
    links = [("关于", "index.html#about"), ("业务", "index.html#business"),
             ("案例", "index.html#cases"), ("师资", "faculty/index.html"),
             ("Demo", "demos/index.html"), ("合作", "index.html#partners")]
    items = "".join(
        f'<a href="{prefix}{href}"{" aria-current=\"page\"" if label == current else ""}>{label}</a>'
        for label, href in links
    )
    sheet = "".join(
        f'<a href="{prefix}{href}" style="--i:{i}">{label}</a>' for i, (label, href) in enumerate(links)
    )
    return f'''<header class="{cls}" id="nav">
  <div class="nav__inner">
    <a class="brand" href="{prefix}index.html" aria-label="遥触灵境 首页">
      <img class="brand__mark" src="{mark}" width="40" height="34" alt="">
      <span class="brand__name">遥触灵境</span>
    </a>
    <nav class="nav__links" aria-label="主导航">{items}</nav>
    <div class="nav__actions">
      <a class="btn btn--sm {'btn--green' if not dark else 'btn--ghost'}" href="{prefix}index.html#contact">联系我们</a>
      <button class="nav__toggle" id="navToggle" aria-label="打开菜单" aria-expanded="false" aria-controls="sheet">{MENU}</button>
    </div>
  </div>
</header>
<div class="sheet" id="sheet" role="dialog" aria-modal="true" aria-label="导航菜单">
  <button class="sheet__close" id="sheetClose" aria-label="关闭菜单">{CLOSE}</button>
  {sheet}
</div>'''


def foot_min(prefix, dark=False):
    if dark:
        return f'''<footer class="lib-foot">
  <div class="container lib-foot__inner">
    <span>© 2026 遥触灵境（杭州）科技有限公司</span>
    <span><a href="{prefix}faculty/index.html">师资团队</a> · <a href="{prefix}index.html">返回官网首页</a></span>
  </div>
</footer>'''
    return f'''<footer class="foot-min">
  <div class="container foot-min__inner">
    <span>© 2026 遥触灵境（杭州）科技有限公司</span>
    <span><a href="{prefix}index.html">返回官网首页</a> · <a href="{prefix}index.html#contact">联系我们</a></span>
  </div>
</footer>'''


def head(title, desc, prefix, extra_css, body_class=""):
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="theme-color" content="{'#0A0A0C' if body_class else '#FFFFFF'}">
<link rel="icon" href="{prefix}favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="{prefix}assets/logo/favicon-32.png">
<link rel="apple-touch-icon" href="{prefix}assets/logo/apple-touch-icon.png">
<link rel="stylesheet" href="{prefix}assets/css/tokens.css">
<link rel="stylesheet" href="{prefix}assets/css/site.css">
<link rel="stylesheet" href="{prefix}assets/css/{extra_css}">
<script src="{prefix}assets/js/site.js" defer></script>
</head>
<body class="{body_class}">
<div class="progress" id="progress" aria-hidden="true"></div>
'''


def poster_url(name, prefix="../../"):
    return f"{prefix}assets/img/posters/{name.replace('poster-', '')}"


def tags_html(tags, attrs=""):
    if not tags:
        return ""
    return f'<div class="chips"{attrs}>' + "".join(f"<span>{e(t)}</span>" for t in tags) + "</div>"


# ---------------- 章节渲染 ----------------
def render_leadcard(lc):
    if not lc:
        return ""
    sub = f'<span class="leadcard__sub">{e(lc["sub"])}</span>' if lc.get("sub") else ""
    body = "".join(f"<p>{e(p)}</p>" for p in lc.get("paras", []))
    caps = ('<div class="chips">' + "".join(f"<span>{e(c)}</span>" for c in lc.get("caps", [])) + "</div>") if lc.get("caps") else ""
    stats = ""
    if lc.get("stats"):
        stats = '<div class="leadcard__stats">' + "".join(
            f"<div><b>{e(s['num'])}</b><span>{e(s['label'])}</span></div>" for s in lc["stats"]) + "</div>"
    return f'<div class="leadcard"><h3>{e(lc["title"])}{sub}</h3>{body}{caps}{stats}</div>'


def render_cards(cards):
    if not cards:
        return ""
    out = []
    for c in cards:
        no = f'<div class="pcard__no">{e(c["no"])}</div>' if c.get("no") else ""
        tags = f'<p class="pcard__tags">{e(c["tags"])}</p>' if c.get("tags") else ""
        paras = "".join(f"<p>{e(p)}</p>" for p in c.get("paras", []))
        tail = f'<div class="pcard__tail">{e(c["tail"])}</div>' if c.get("tail") else ""
        out.append(f'<article class="pcard">{no}<h4>{e(c["title"])}</h4>{tags}{paras}{tail}</article>')
    return '<div class="cardgrid">' + "".join(out) + "</div>"


def render_works(sec):
    items = sec.get("works", [])
    if not items:
        return ""
    cards = []
    for w in items:
        rank = f'<span class="wcard__rank">{e(w["rank"])}</span>' if w.get("rank") else ""
        if w.get("image"):
            ph = f'<div class="wcard__ph">{rank}<img src="{poster_url(w["image"])}" alt="{e(w.get("alt") or w["title"])}" loading="lazy"></div>'
        else:
            t = w.get("typo") or {}
            ph = f'''<div class="wcard__ph"><div class="typo">
  <span class="typo__no">{e(t.get("no") or "AIGC")}</span>
  <span class="typo__big">{e(t.get("big") or w["title"][:1])}</span>
  <div class="typo__meta"><b>{e(t.get("name") or w["title"])}</b><i>{e(t.get("kind") or "")}{(" · " + t.get("platform")) if t.get("platform") else ""}</i></div>
</div></div>'''
        heat = ""
        if w.get("heat"):
            heat = f'<div class="wcard__heat"><b>{e(w["heat"]["num"])}</b><span>{e(w["heat"]["label"])}</span></div>'
            ph = ph[: -len("</div>")] + heat + "</div>"
        meta = f'''<div class="wcard__meta"><div class="wcard__title">{e(w["title"])}</div>
<div class="wcard__genre">{e(w.get("genre", ""))}</div>
<div class="wcard__tag">{e(w.get("tag", ""))}</div></div>'''
        cards.append(f'<div class="wcard">{ph}{meta}</div>')
    return '<div class="rail">' + "".join(cards) + "</div>"


def render_timeline(items):
    if not items:
        return ""
    inner = "".join(
        f'<div class="tl__item"><span class="tl__year">{e(i["year"])}</span><div class="tl__text">{e(i["text"])}</div></div>'
        for i in items)
    return f'<div class="tl">{inner}</div>'


def render_flow(steps):
    if not steps:
        return ""
    return '<div class="flowgrid">' + "".join(
        f'<div class="fstep"><span>{e(s["no"])}</span><b>{e(s["title"])}</b><p>{e(s["text"])}</p></div>'
        for s in steps) + "</div>"


def render_section(sec):
    tag = sec.get("tag", "")
    no = tag.split("·")[0].strip() if "·" in tag else ""
    head_html = f'''<div class="psec__head">
  <span class="psec__no">{e(no)}</span>
  <h2 class="psec__title">{e(sec["heading"])}</h2>
  <span class="psec__en">{e(sec.get("en", ""))}</span>
</div>'''

    t = sec.get("type")
    body = ""
    if t == "intro":
        lead = f'<p class="lead">{e(sec["lead"])}</p>' if sec.get("lead") else ""
        paras = "".join(f"<p>{e(p)}</p>" for p in sec.get("paras", []))
        prose = f'<div class="prose">{paras}</div>' if paras else ""
        body = lead + prose + tags_html(sec.get("caps"))
    elif t == "works":
        body = render_leadcard(sec.get("leadCard")) + render_works(sec)
    elif t == "timeline":
        body = render_leadcard(sec.get("leadCard")) + render_timeline(sec.get("timeline")) + tags_html(sec.get("caps"))
    elif t == "flow":
        body = render_leadcard(sec.get("leadCard")) + render_flow(sec.get("steps")) + render_cards(sec.get("cards"))
    elif t == "teaching":
        body = render_leadcard(sec.get("leadCard")) + render_cards(sec.get("cards"))
    else:
        lc = render_leadcard(sec.get("leadCard"))
        paras = "".join(f"<p>{e(p)}</p>" for p in sec.get("paras", []))
        body = lc + (f'<div class="prose">{paras}</div>' if paras else "") + render_cards(sec.get("cards"))

    return f'<section class="psec" data-reveal>{head_html}{body}</section>'


# ---------------- 师资列表页 ----------------
def build_index(people, site):
    prefix = "../"
    founders = [p for p in people if p["group"] == "founder"]
    mentors = [p for p in people if p["group"] != "founder"]

    def fcard(p):
        tags = "".join(f"<span>{e(t)}</span>" for t in p.get("tags", []))
        return f'''<a class="fcard" href="{p["slug"]}/index.html" data-reveal data-group="founder">
  <div class="fcard__photo"><img src="{prefix}assets/img/faculty/{p["slug"]}.jpg" width="560" height="700" alt="{e(p["name"])}" loading="lazy"></div>
  <div class="fcard__body">
    <h2 class="fcard__name">{e(p["name"])}</h2>
    <div class="fcard__title">{e(p["title"])}</div>
    <p class="fcard__desc">{e(p["summary"])}</p>
    <div class="fcard__tags">{tags}</div>
    <span class="fcard__go">查看履历 {ARROW}</span>
  </div>
</a>'''

    def mcard(p, i):
        tags = "".join(f"<span>{e(t)}</span>" for t in p.get("tags", []))
        return f'''<a class="mcard" href="{p["slug"]}/index.html" data-reveal data-group="mentor" style="--i:{i % 3}">
  <div class="mcard__photo"><img src="{prefix}assets/img/faculty/{p["slug"]}.jpg" width="560" height="700" alt="{e(p["name"])}" loading="lazy"></div>
  <div class="mcard__body">
    <div class="mcard__name">{e(p["name"])}</div>
    <div class="mcard__title">{e(p["title"])}</div>
    <p class="mcard__desc">{e(p["summary"])}</p>
    <div class="mcard__tags">{tags}</div>
    <span class="mcard__go">查看履历 {ARROW}</span>
  </div>
</a>'''

    works = {(w["title"]) for p in people for s in p["sections"] for w in s.get("works", [])}
    body = head("师资团队 · 遥触灵境",
                f"遥触灵境 {len(people)} 位一线实战导师，覆盖平台操盘、工作流开发、短剧创作、企业培训与教学设计。",
                prefix, "faculty.css")
    body += nav(prefix, current="师资")
    body += f'''<main>
  <header class="page-hero">
    <div class="container">
      <div class="breadcrumb" data-reveal><a href="{prefix}index.html">首页</a><span>/</span><span>师资团队</span></div>
      <h1 class="page-hero__title" data-reveal="blur" style="--i:1">{len(people)} 位一线实战导师</h1>
      <p class="page-hero__sub" data-reveal style="--i:2">{e(site["faculty_note"])}</p>
      <div class="fstats" data-reveal style="--i:3">
        <div class="fstat"><b>{len(people)}</b><span>在册导师</span></div>
        <div class="fstat"><b>{len(founders)}</b><span>创始人</span></div>
        <div class="fstat"><b>{len(mentors)}</b><span>导师团队</span></div>
        <div class="fstat"><b>{len(works)}</b><span>部代表作品</span></div>
      </div>
    </div>
  </header>

  <div class="container">
    <div class="filter" role="group" aria-label="筛选成员" data-reveal>
      <button data-filter="all" class="is-on" aria-pressed="true">全部 {len(people)}</button>
      <button data-filter="founder" aria-pressed="false">创始人 {len(founders)}</button>
      <button data-filter="mentor" aria-pressed="false">导师 {len(mentors)}</button>
    </div>

    <section class="founders" data-section="founder">
      {"".join(fcard(p) for p in founders)}
    </section>

    <section class="mentors" data-section="mentor">
      {"".join(mcard(p, i) for i, p in enumerate(mentors))}
    </section>

    <div class="roster-cta" data-reveal>
      <div><b>想看他们做出来的东西</b><p>{e(site["demo_note"])}</p></div>
      <a class="btn btn--green" href="{prefix}demos/index.html">进入 Demo 库 {ARROW}</a>
    </div>
  </div>
</main>
'''
    body += foot_min(prefix)
    body += '<script src="../assets/js/faculty.js" defer></script>\n</body>\n</html>\n'
    return body


# ---------------- 讲师详情页 ----------------
def build_person(p, people, site):
    prefix = "../../"
    idx = people.index(p)
    prev_p = people[(idx - 1) % len(people)]
    next_p = people[(idx + 1) % len(people)]

    roles = "".join(f"<p>{e(r)}</p>" for r in p.get("roles", []))
    motto = f'<div class="person__motto" data-reveal style="--i:3">{e(p["motto"])}</div>' if p.get("motto") else ""
    tags = tags_html(p.get("tags"), ' data-reveal style="--i:4"')

    stats = ""
    if p.get("stats"):
        stats = '<div class="pstats" data-reveal>' + "".join(
            f'<div class="pstat"><b>{e(s["num"])}</b><span>{e(s["label"])}</span></div>'
            for s in p["stats"]) + "</div>"

    sections = "".join(render_section(s) for s in p["sections"])

    body = head(f'{p["name"]} · {p["title"]} · 遥触灵境',
                p.get("summary") or f'{p["name"]}，{p["title"]}。', prefix, "faculty.css")
    body += nav(prefix, current="师资")
    body += f'''<main>
  <header class="person">
    <div class="container">
      <div class="breadcrumb" data-reveal><a href="{prefix}index.html">首页</a><span>/</span><a href="../index.html">师资团队</a><span>/</span><span>{e(p["name"])}</span></div>
      <div class="person__grid" style="margin-top:26px">
        <div>
          <div class="person__tagline" data-reveal>{e(p.get("title") or p.get("tagline", ""))}</div>
          <h1 class="person__name" data-reveal="blur" style="--i:1">{e(p["name"])}</h1>
          <div class="person__roles" data-reveal style="--i:2">{roles}</div>
          {motto}
          {tags}
        </div>
        <div class="person__photo" data-reveal style="--i:2">
          <img src="{prefix}assets/img/faculty/{p["slug"]}.jpg" width="560" height="700" alt="{e(p["name"])}">
        </div>
      </div>
      {stats}
    </div>
  </header>

  <div class="container" style="margin-top:clamp(24px,4vw,44px)">
    {sections}
    <nav class="pager" aria-label="讲师翻页">
      <a href="../{prev_p["slug"]}/index.html"><span>上一位</span><b>{e(prev_p["name"])} · {e(prev_p["title"])}</b></a>
      <a href="../{next_p["slug"]}/index.html"><span>下一位</span><b>{e(next_p["name"])} · {e(next_p["title"])}</b></a>
    </nav>
  </div>
</main>
'''
    body += foot_min(prefix)
    body += "</body>\n</html>\n"
    return body


# ---------------- Demo 页 ----------------
def build_demos(demos, site):
    prefix = "../"
    s = [d for d in demos if d["grade"] == "S"]
    a = [d for d in demos if d["grade"] == "A"]
    b = [d for d in demos if d["grade"] not in ("S", "A")]

    def card(d):
        g = d["grade"]
        initial = d["title"].strip()[:1]
        return f'''<article class="vcard" data-url="{e(d["url"])}" data-title="{e(d["title"])}" data-grade="{e(g)}"
  role="button" tabindex="0" aria-label="播放 {e(d["title"])}" data-reveal>
  <div class="vcard__thumb">
    <span class="vcard__fallback" aria-hidden="true">{e(initial)}</span>
    <span class="vcard__badge">{e(g)}</span>
    <video preload="none" muted playsinline data-src="{e(d["url"])}"></video>
    <div class="vcard__play"><div class="vcard__orb">{PLAY}</div></div>
  </div>
  <div class="vcard__body"><span class="vcard__name">{e(d["title"])}</span><span class="vcard__hint">点击播放</span></div>
</article>'''

    tiers = ""
    for key, label, en, items, cls in [("S", "S 级作品", "Premium", s, "s"),
                                       ("A", "A 级作品", "Advanced", a, "a")]:
        if not items:
            continue
        tiers += f'''<section class="tier tier--{cls}">
  <div class="tier__head" data-reveal>
    <span class="tier__grade">{key}</span><span class="tier__name">{label}</span>
    <span class="tier__en">{en}</span><span class="tier__rule"></span>
  </div>
  <div class="vgrid">{"".join(card(d) for d in items)}</div>
</section>'''

    body = head("Demo 作品库 · 遥触灵境",
                f"遥触灵境 Demo 作品库，{len(demos)} 部 S 级与 A 级作品，覆盖游戏 CG、仿真人、3D 漫、海外剧与国内短剧。",
                prefix, "demos.css", body_class="dark-page")
    body += nav(prefix, dark=True, current="Demo")
    body += f'''<main>
  <header class="lib-hero">
    <div class="container">
      <div class="breadcrumb" data-reveal style="color:var(--dark-ink-2)">
        <a href="{prefix}index.html" style="color:var(--dark-ink-2)">首页</a><span>/</span><span>Demo 作品库</span>
      </div>
      <h1 class="lib-hero__title" data-reveal="blur" style="--i:1">Demo <i>作品库</i></h1>
      <p class="lib-hero__sub" data-reveal style="--i:2">按分级归档的团队产出。点击卡片在线播放，播放窗内可下载原片</p>
      <div class="lib-stats" data-reveal style="--i:3">
        <span class="lib-stat"><b>{len(demos)}</b>部作品</span>
        <span class="lib-stat lib-stat--s"><b>{len(s)}</b>部 S 级</span>
        <span class="lib-stat"><b>{len(a)}</b>部 A 级</span>
      </div>
    </div>
  </header>

  <div class="container">
    {tiers}
  </div>
</main>
'''
    body += foot_min(prefix, dark=True)
    body += f'''<div class="modal" id="modal" role="dialog" aria-modal="true" aria-hidden="true" aria-label="视频播放">
  <div class="modal__inner">
    <div class="modal__head">
      <span class="modal__grade s" id="modalGrade">S</span>
      <span class="modal__title" id="modalTitle"></span>
      <div class="modal__actions">
        <a class="modal__btn" id="modalDownload" href="#" download>{DOWNLOAD}<span>下载</span></a>
        <button class="modal__close" id="modalClose" aria-label="关闭">{CLOSE}</button>
      </div>
    </div>
    <video id="player" controls playsinline></video>
    <div class="modal__hint">按 ESC 或点击空白处关闭</div>
  </div>
</div>
<script src="{prefix}assets/js/demos.js" defer></script>
</body>
</html>
'''
    return body


def main():
    faculty = json.load(open(os.path.join(DATA, "faculty.json"), encoding="utf-8"))
    site = json.load(open(os.path.join(DATA, "site.json"), encoding="utf-8"))
    demos = json.load(open(os.path.join(DATA, "demos.json"), encoding="utf-8"))["demos"]
    people = faculty["people"]

    out_dir = os.path.join(SITE, "faculty")
    os.makedirs(out_dir, exist_ok=True)

    html = build_index(people, site)
    open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8").write(html)
    print("师资列表", len(html) // 1024, "KB")

    for p in people:
        d = os.path.join(out_dir, p["slug"])
        os.makedirs(d, exist_ok=True)
        h = build_person(p, people, site)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(h)
        print(f'  {p["slug"]:<16} {len(p["sections"])} 章节  {len(h)//1024} KB')

    ddir = os.path.join(SITE, "demos")
    os.makedirs(ddir, exist_ok=True)
    dh = build_demos(demos, site)
    open(os.path.join(ddir, "index.html"), "w", encoding="utf-8").write(dh)
    print("Demo 库", len(demos), "部", len(dh) // 1024, "KB")


if __name__ == "__main__":
    main()
