"""P0 内容抽取：把 14 个讲师页 + Demo 页解析为结构化 JSON。

输出：
    data/faculty.json   14 位讲师（含分组、简介、章节原语）
    data/demos.json     14 部 Demo（分级、标题、视频地址）
    data/_diag.txt      未识别块的诊断清单，供人工核对

章节原语（type）：
    intro    简介段落 + 标签
    cards    caps 卡片网格（可带 leadCard 引导卡）
    works    作品海报（图片或文字版式）
    teaching 教学理念引导卡 + 要点卡
    timeline 时间轴
    narrative 纯段落
"""
import glob
import json
import os
import re
from html import unescape
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACULTY = os.path.join(ROOT, "archive", "faculty-legacy")
DATA = os.path.join(ROOT, "data")
DIAG = []

VOID = {"img", "br", "hr", "meta", "link", "input", "source", "area", "base", "col"}
SKIP = {"script", "style"}
KNOWN = {"sec-head", "intro", "cap-grid", "rail", "teach-card", "company",
         "edu-grid", "timeline", "carousel-hint", "car-nav", "cap-row", "progress", "flow"}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []
        self.parent = parent

    @property
    def cls(self):
        return self.attrs.get("class", "")

    def has(self, cls):
        return cls in self.cls.split()

    def walk(self):
        for c in self.children:
            if isinstance(c, Node) and c.tag not in SKIP:
                yield c
                yield from c.walk()

    def find_all(self, cls=None, tag=None):
        out = []
        for n in self.walk():
            if cls and not n.has(cls):
                continue
            if tag and n.tag != tag:
                continue
            out.append(n)
        return out

    def find(self, cls=None, tag=None):
        for n in self.find_all(cls, tag):
            return n
        return None

    def kids(self):
        return [c for c in self.children if isinstance(c, Node) and c.tag not in SKIP]

    def all_text(self):
        buf = []
        for c in self.children:
            buf.append(c if isinstance(c, str) else c.all_text())
        return norm("".join(buf))


def norm(s):
    s = unescape(s).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip()


class Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", [], None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse(path):
    b = Builder()
    b.feed(open(path, encoding="utf-8").read())
    return b.root


def paras(node, skip_cls=()):
    out = []
    if node is None:
        return out
    for p in node.find_all(tag="p"):
        if any(p.has(c) for c in skip_cls):
            continue
        t = p.all_text()
        if t:
            out.append(t)
    return out


def caps(node):
    return [c.all_text() for c in node.find_all(cls="cap") if c.all_text()]


def timeline(node):
    items = []
    for it in node.find_all(cls="tl-item"):
        y = it.find(cls="tl-year")
        t = it.find(cls="tl-text")
        items.append({"year": y.all_text() if y else "", "text": t.all_text() if t else ""})
    return items


def stats(node):
    out = []
    for es in node.find_all(cls="es"):
        b = es.find(tag="b")
        s = es.find(tag="span")
        out.append({"num": b.all_text() if b else "", "label": s.all_text() if s else ""})
    return out


def lead_card(sec):
    """公司 / 教育 / 教学 引导卡"""
    company = sec.find(cls="company")
    edu = sec.find(cls="edu-main")
    teach = sec.find(cls="teach-card")
    node = company or edu or teach
    if node is None:
        return None
    h = node.find(tag="h3") or node.find(tag="h4")
    sub = node.find(cls="c-sub")
    if sub is None and edu is not None:
        sub = node.find(tag="span")
    title = h.all_text() if h else ""
    sub_text = sub.all_text() if sub else ""
    if sub_text and title.endswith(sub_text):
        title = title[: -len(sub_text)].strip()
    card = {
        "title": title,
        "sub": sub_text,
        "paras": paras(node),
        "caps": caps(node),
    }
    tl = timeline(node)
    if tl:
        card["timeline"] = tl
    st = stats(node)
    if st:
        card["stats"] = st
    return card


def cards_of(sec):
    items = []
    for it in sec.find_all(cls="cap-item"):
        n = it.find(cls="n")
        h = it.find(tag="h4") or it.find(tag="h3")
        tags = it.find(cls="cap-tags")
        tail = it.find(cls="cap-tail")
        items.append({
            "no": n.all_text() if n else "",
            "title": h.all_text() if h else "",
            "paras": paras(it, skip_cls=("cap-tags", "cap-tail")),
            "tags": tags.all_text() if tags else "",
            "tail": tail.all_text() if tail else "",
        })
    for it in sec.find_all(cls="edu-card"):
        h = it.find(tag="h4") or it.find(tag="h3")
        items.append({
            "no": "",
            "title": h.all_text() if h else "",
            "paras": paras(it),
            "tags": "",
            "tail": "",
        })
    return items


def flow_of(sec):
    steps = []
    for st in sec.find_all(cls="flow-step"):
        no = st.find(cls="fn")
        b = st.find(tag="b")
        sp = st.find(tag="span")
        spans = [s for s in st.find_all(tag="span") if not s.has("fn")]
        steps.append({
            "no": no.all_text() if no else "",
            "title": b.all_text() if b else "",
            "text": spans[0].all_text() if spans else "",
        })
    return steps


def works_of(sec):
    items = []
    for art in sec.find_all(tag="article"):
        meta = art.find(cls="meta")
        title = meta.find(cls="t") if meta else None
        genre = meta.find(cls="g") if meta else None
        tag = art.find(cls="tag")
        rank = art.find(cls="rank")
        item = {
            "title": title.all_text() if title else "",
            "genre": genre.all_text() if genre else "",
            "tag": tag.all_text() if tag else "",
            "rank": rank.all_text() if rank else "",
        }
        heat = art.find(cls="heat")
        if heat:
            hn = heat.find(cls="h-num")
            hl = heat.find(cls="h-label")
            item["heat"] = {"num": hn.all_text() if hn else "", "label": hl.all_text() if hl else ""}
        img = art.find(tag="img")
        typo = art.find(cls="typo-poster")
        if img is not None:
            item["image"] = img.attrs.get("src", "")
            item["alt"] = img.attrs.get("alt", "")
        elif typo is not None:
            def g(c, t="div"):
                n = typo.find(cls=c, tag=t) or typo.find(cls=c)
                return n.all_text() if n else ""
            item["typo"] = {
                "big": g("big"),
                "name": g("name"),
                "kind": g("type", "span"),
                "no": g("no", "span"),
                "platform": g("platform", "span"),
                "small": bool(typo.find(cls="name") is not None and typo.find(cls="name").has("sm")),
            }
        if item["title"]:
            items.append(item)
    return items


def collect(path):
    root = parse(path)
    out = {}
    header = root.find(tag="header")
    if header:
        h1 = header.find(tag="h1")
        out["name"] = h1.all_text() if h1 else ""
        tag = header.find(cls="hero-tag")
        out["tagline"] = tag.all_text() if tag else ""
        out["roles"] = [r.all_text() for r in header.find_all(cls="role")]
        motto = header.find(cls="motto")
        out["motto"] = paras(motto)[0] if motto and paras(motto) else ""
        out["stats"] = []
        for sb in header.find_all(cls="sb-item"):
            num = sb.find(cls="sb-num")
            lbl = sb.find(cls="sb-label")
            out["stats"].append({"num": num.all_text() if num else "",
                                "label": lbl.all_text() if lbl else ""})
        out["marquee"] = [m.all_text() for m in header.find_all(cls="mq-item")]

    main = root.find(tag="main")
    out["sections"] = []
    if main is None:
        return out

    for sec in main.find_all(tag="section"):
        head = sec.find(cls="sec-title")
        if head is None:
            continue
        heading = head.all_text()
        en = sec.find(cls="sec-en")
        tag = sec.find(cls="sec-tag")
        body = {"heading": heading,
                "en": en.all_text() if en else "",
                "tag": tag.all_text() if tag else ""}
        where = f"{os.path.basename(os.path.dirname(path))}/{sec.attrs.get('id', '')}"

        intro = sec.find(cls="intro")
        if intro is not None:
            lead = intro.find(cls="lead")
            body["lead"] = lead.all_text() if lead else ""
            body["paras"] = [p for p in paras(intro, skip_cls=("lead",)) if p != body["lead"]]
            body["caps"] = caps(intro)

        lc = lead_card(sec)
        if lc:
            body["leadCard"] = lc

        ws = works_of(sec)
        if ws:
            body["works"] = ws
            hint = sec.find(cls="carousel-hint")
            body["hint"] = hint.all_text() if hint else ""

        steps = flow_of(sec)
        if steps:
            body["steps"] = steps

        cs = cards_of(sec)
        if cs:
            body["cards"] = cs

        tl = timeline(sec)
        if tl:
            body["timeline"] = tl

        if ws:
            body["type"] = "works"
        elif steps:
            body["type"] = "flow"
        elif sec.find(cls="teach-card") is not None:
            body["type"] = "teaching"
        elif tl:
            body["type"] = "timeline"
        elif cs:
            body["type"] = "cards"
        elif intro is not None:
            body["type"] = "intro"
        elif paras(sec):
            body["type"] = "narrative"
            if not body.get("paras"):
                body["paras"] = paras(sec)
        else:
            body["type"] = "unknown"

        if body["type"] == "unknown":
            DIAG.append(f"{where}「{heading}」: 未归类，正文 {len(sec.all_text())} 字")
        for child in sec.kids():
            if not (set(child.cls.split()) & KNOWN):
                DIAG.append(f"{where}「{heading}」: 顶层块 class=\"{child.cls}\" 未处理")
        out["sections"].append(body)
    return out


def js_array(path):
    src = open(path, encoding="utf-8").read()
    block = re.search(r"const LECTURERS = \[(.*?)\n\];", src, re.S)
    meta, order = {}, []
    if not block:
        return meta, order
    for obj in re.finditer(r"\{(.*?)\n  \}", block.group(1), re.S):
        s = obj.group(1)
        get = lambda k: (re.search(rf'{k}:\s*"([^"]*)"', s) or [None, ""])[1]
        tags = re.findall(r'"([^"]*)"', (re.search(r"tags:\s*\[(.*?)\]", s, re.S) or [None, ""])[1])
        slug = get("dir").strip("/")
        order.append(slug)
        meta[slug] = {"group": get("group") or "mentor", "name": get("name"),
                      "title": get("title"), "tags": tags, "summary": get("desc")}
    return meta, order


def main():
    os.makedirs(DATA, exist_ok=True)
    meta, order = js_array(os.path.join(FACULTY, "index.html"))
    people = []

    for d in sorted(glob.glob(os.path.join(FACULTY, "*"))):
        if not os.path.isdir(d) or os.path.basename(d) == "demos":
            continue
        idx = os.path.join(d, "index.html")
        if not os.path.exists(idx):
            continue
        slug = os.path.basename(d)
        page = collect(idx)
        m = meta.get(slug, {})
        people.append({
            "slug": slug,
            "group": m.get("group", "mentor"),
            "name": m.get("name") or page.get("name", ""),
            "title": m.get("title", ""),
            "tags": m.get("tags", []),
            "summary": m.get("summary", ""),
            "tagline": page.get("tagline", ""),
            "roles": page.get("roles", []),
            "motto": page.get("motto", ""),
            "stats": page.get("stats", []),
            "marquee": page.get("marquee", []),
            "photo": "photo.jpg",
            "sections": page.get("sections", []),
        })

    rank = {s: i for i, s in enumerate(order)}
    people.sort(key=lambda r: rank.get(r["slug"], 99))

    with open(os.path.join(DATA, "faculty.json"), "w", encoding="utf-8") as f:
        json.dump({"count": len(people), "people": people}, f, ensure_ascii=False, indent=1)

    demos = []
    dp = os.path.join(FACULTY, "demos", "index.html")
    if os.path.exists(dp):
        src = open(dp, encoding="utf-8").read()
        for m in re.finditer(r'data-url="([^"]+)"\s+data-title="([^"]+)"\s+data-grade="([^"]+)"', src):
            demos.append({"url": m.group(1), "title": m.group(2), "grade": m.group(3)})
    with open(os.path.join(DATA, "demos.json"), "w", encoding="utf-8") as f:
        json.dump({"count": len(demos), "demos": demos}, f, ensure_ascii=False, indent=1)

    with open(os.path.join(DATA, "_diag.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(DIAG) if DIAG else "no issues")

    print(f"讲师 {len(people)} 位 -> data/faculty.json")
    print(f"Demo {len(demos)} 部 -> data/demos.json")
    print(f"诊断 {len(DIAG)} 条 -> data/_diag.txt")
    for p in people:
        t = [s["type"] for s in p["sections"]]
        print(f"  {p['slug']:<15} sec={len(p['sections'])} works={sum(len(s.get('works', [])) for s in p['sections']):<3}"
              f" cards={sum(len(s.get('cards', [])) for s in p['sections']):<3} {','.join(t)}")


if __name__ == "__main__":
    main()
