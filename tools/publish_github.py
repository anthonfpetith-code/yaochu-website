"""通过 GitHub API 发布站点（本机 git 443 被阻断时的备用通道）。

用法：
    python tools/publish_github.py

做法：
    main 分支        完整项目（site / data / tools / assets）
    gh-pages 分支    site/ 的内容，作为 Pages 发布源
    Pages            Deploy from a branch -> gh-pages / (root)

不使用 Actions 工作流，因为当前 token 只有 repo 权限，缺少 workflow 权限。
"""
import base64
import os
import subprocess
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
OWNER = "anthonfpetith-code"
REPO = "yaochu-website"
API = "https://api.github.com"
MAIN_MSG = "Remote: build Yaochu corporate site with faculty and demo library"
PAGES_MSG = "Deploy: publish site to gh-pages"


def token():
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


S = requests.Session()
S.headers.update({
    "Authorization": f"Bearer {token()}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
})


def call(method, path, **kw):
    r = S.request(method, API + path, timeout=60, **kw)
    if r.status_code >= 400:
        raise RuntimeError(f"{method} {path} -> {r.status_code} {r.text[:300]}")
    return r.json() if r.text else {}


def blob(local_path, repo_path):
    data = open(local_path, "rb").read()
    res = call("POST", f"/repos/{OWNER}/{REPO}/git/blobs",
               json={"content": base64.b64encode(data).decode(), "encoding": "base64"})
    return {"path": repo_path, "mode": "100644", "type": "blob", "sha": res["sha"]}


def make_commit(entries, message, parent):
    tree = call("POST", f"/repos/{OWNER}/{REPO}/git/trees", json={"tree": entries})
    commit = call("POST", f"/repos/{OWNER}/{REPO}/git/commits",
                  json={"message": message, "tree": tree["sha"],
                        "parents": [parent] if parent else []})
    return commit["sha"]


def head(ref):
    try:
        return call("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/{ref}")["object"]["sha"]
    except RuntimeError:
        return None


def ensure_initial():
    sha = head("main")
    if sha:
        return sha
    content = open(os.path.join(ROOT, ".gitignore"), "rb").read()
    call("PUT", f"/repos/{OWNER}/{REPO}/contents/.gitignore",
         json={"message": "chore: init repository",
               "content": base64.b64encode(content).decode(), "branch": "main"})
    time.sleep(2)
    return head("main")


def push_main(parent):
    paths = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    entries = []
    for i, rel in enumerate(paths, 1):
        entries.append(blob(os.path.join(ROOT, rel.replace("/", os.sep)), rel))
        if i % 20 == 0:
            print(f"  main blobs {i}/{len(paths)}")
    sha = make_commit(entries, MAIN_MSG, parent)
    call("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/main", json={"sha": sha})
    print("main commit", sha[:10], f"({len(paths)} 个文件)")
    return sha


def push_pages():
    entries = []
    count = 0
    for dirpath, _, names in os.walk(SITE):
        for name in names:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, SITE).replace(os.sep, "/")
            entries.append(blob(full, rel))
            count += 1
            if count % 20 == 0:
                print(f"  pages blobs {count}")
    sha = make_commit(entries, PAGES_MSG, None)
    if head("gh-pages"):
        call("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/gh-pages", json={"sha": sha})
    else:
        call("POST", f"/repos/{OWNER}/{REPO}/git/refs",
             json={"ref": "refs/heads/gh-pages", "sha": sha})
    print("gh-pages commit", sha[:10], f"({count} 个文件)")
    return sha


def enable_pages():
    try:
        call("POST", f"/repos/{OWNER}/{REPO}/pages",
             json={"source": {"branch": "gh-pages", "path": "/"}})
        print("Pages 已开启：gh-pages 分支")
    except RuntimeError as exc:
        if "409" in str(exc):
            call("PUT", f"/repos/{OWNER}/{REPO}/pages",
                 json={"source": {"branch": "gh-pages", "path": "/"}})
            print("Pages 已更新为 gh-pages 分支")
        else:
            raise


def wait_build():
    time.sleep(8)
    for _ in range(30):
        builds = call("GET", f"/repos/{OWNER}/{REPO}/pages/builds?per_page=1")
        if builds:
            b = builds[0]
            print(f"  build {b['status']}")
            if b["status"] == "built":
                return b
            if b["status"] == "errored":
                raise RuntimeError(f"构建失败: {b.get('error', {}).get('message')}")
        time.sleep(10)
    raise RuntimeError("构建超时")


def main():
    print(f"发布到 {OWNER}/{REPO}")
    parent = ensure_initial()
    push_main(parent)
    push_pages()
    enable_pages()
    wait_build()
    page = call("GET", f"/repos/{OWNER}/{REPO}/pages")
    print("访问地址:", page.get("html_url"))
    print("仓库地址:", f"https://github.com/{OWNER}/{REPO}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("失败:", exc)
        sys.exit(1)
