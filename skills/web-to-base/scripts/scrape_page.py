#!/usr/bin/env python3
"""网页 → 结构化数据（只用 Python 标准库）。

两步走，中间让用户挑：
    python3 scrape_page.py --url <网址>                         # 1. 合规检查 + 列出页面里能抓的数据块
    python3 scrape_page.py --url <网址> --pick t2 --out rows.json  # 2. 导出选中的数据块（清洗后的行）

识别三类数据块：
    t1, t2…  HTML 表格（<table>，含表头）
    j1…      JSON-LD 结构化数据（schema.org 的 ItemList / Product / Event 等）
    l1…      重复出现的列表项（同一父节点下 ≥ 5 个结构相同的 <li> / 卡片）
页面是前端渲染（拿到的 HTML 里几乎没有正文）时会提示改走浏览器路线（见 references/page-types.md）。

合规：默认遵守 robots.txt（不允许就停）、带可识别的 User-Agent、请求之间至少间隔 2 秒、
只抓公开页面；不抓需要登录、付费墙后面的内容，不采集个人信息。
"""
import argparse
import html
import json
import os
import re
import sys
import time
from datetime import datetime
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser

UA = "web-to-base-skill/0.1 (+https://github.com/xignzuan5/feishu-base-live-dashboard)"
CACHE_DIR = ".web-cache"
MIN_INTERVAL = 2.0


def robots_allowed(url):
    parts = urllib.parse.urlsplit(url)
    robots_url = "%s://%s/robots.txt" % (parts.scheme, parts.netloc)
    rp = urllib.robotparser.RobotFileParser()
    # 自己带 User-Agent 去取：标准库默认 UA 常被网站 403，会被误判成「全部禁止」
    req = urllib.request.Request(robots_url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            rp.parse(resp.read().decode("utf-8", errors="replace").splitlines())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False, "robots.txt 拒绝访问（HTTP %d），按禁止处理" % e.code
        return True, "没有 robots.txt（HTTP %d），按未声明处理" % e.code
    except Exception:
        return True, "robots.txt 读取失败，按未声明处理（请人工确认网站条款）"
    # robots 规则里的路径是百分号编码的，中文路径要先编码再比对
    path = urllib.parse.quote(parts.path or "/", safe="/%:@") + ("?" + parts.query if parts.query else "")
    allowed = rp.can_fetch(UA, "%s://%s%s" % (parts.scheme, parts.netloc, path))
    return allowed, "robots.txt %s" % ("允许" if allowed else "禁止")


def fetch(url, refresh=False):
    os.makedirs(CACHE_DIR, exist_ok=True)
    key = re.sub(r"[^A-Za-z0-9]+", "_", url)[-150:] + ".html"
    path = os.path.join(CACHE_DIR, key)
    if os.path.exists(path) and not refresh:
        return open(path, encoding="utf-8").read(), True
    stamp = os.path.join(CACHE_DIR, ".last")
    if os.path.exists(stamp):
        wait = MIN_INTERVAL - (time.time() - os.path.getmtime(stamp))
        if wait > 0:
            time.sleep(wait)
    parts = urllib.parse.urlsplit(url)
    safe_url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, urllib.parse.quote(parts.path, safe="/%:@"),
                                         parts.query, parts.fragment))
    req = urllib.request.Request(safe_url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        body = resp.read().decode(charset, errors="replace")
    open(stamp, "w").close()
    open(path, "w", encoding="utf-8").write(body)
    return body, False


def clean_text(s):
    s = html.unescape(s)
    s = re.sub(r"\[\s*(\d+|[a-z]|注\s*\d*|note \d+|citation needed)\s*\]", "", s)  # 维基脚注 [1] [a]
    return re.sub(r"\s+", " ", s).strip()


class PageParser(HTMLParser):
    """收集表格、JSON-LD、列表项与正文长度。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.jsonld, self.lists = [], [], []
        self._table_stack, self._cell, self._row = [], None, None
        self._in_script, self._script_type, self._script_buf = False, "", []
        self._skip = 0
        self._li_stack, self.text_len = [], 0
        self._caption = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("style", "noscript"):
            self._skip += 1
        if tag == "script":
            self._in_script, self._script_type, self._script_buf = True, (a.get("type") or ""), []
        if tag == "table":
            self._table_stack.append({"rows": [], "caption": "", "cls": a.get("class") or ""})
        elif self._table_stack:
            t = self._table_stack[-1]
            if tag == "tr":
                self._row = []
            elif tag in ("td", "th") and self._row is not None:
                self._cell = {"text": [], "th": tag == "th", "span": int(a.get("colspan") or 1)
                              if str(a.get("colspan") or "1").isdigit() else 1}
            elif tag == "caption":
                self._caption = []
            elif tag == "a" and self._cell is not None and a.get("href"):
                self._cell.setdefault("href", a.get("href"))
            elif tag == "br" and self._cell is not None:
                self._cell["text"].append(" ")
            t["cls"] = t["cls"]
        if tag == "li":
            self._li_stack.append({"text": [], "href": None, "depth": len(self._li_stack)})
        elif tag == "a" and self._li_stack and a.get("href") and not self._li_stack[-1]["href"]:
            self._li_stack[-1]["href"] = a.get("href")

    def handle_endtag(self, tag):
        if tag in ("style", "noscript") and self._skip:
            self._skip -= 1
        if tag == "script" and self._in_script:
            if "ld+json" in self._script_type:
                try:
                    self.jsonld.append(json.loads("".join(self._script_buf)))
                except ValueError:
                    pass
            self._in_script = False
        if not self._table_stack:
            pass
        elif tag in ("td", "th") and self._cell is not None and self._row is not None:
            txt = clean_text("".join(self._cell["text"]))
            for _ in range(min(self._cell["span"], 20)):
                self._row.append({"text": txt, "th": self._cell["th"], "href": self._cell.get("href")})
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self._table_stack[-1]["rows"].append(self._row)
            self._row = None
        elif tag == "caption" and self._caption is not None:
            self._table_stack[-1]["caption"] = clean_text("".join(self._caption))
            self._caption = None
        elif tag == "table":
            self.tables.append(self._table_stack.pop())
        if tag == "li" and self._li_stack:
            li = self._li_stack.pop()
            self.lists.append({"text": clean_text("".join(li["text"])), "href": li["href"], "depth": li["depth"]})

    def handle_data(self, data):
        if self._in_script:
            self._script_buf.append(data)
            return
        if self._skip:
            return
        self.text_len += len(data.strip())
        if self._cell is not None:
            self._cell["text"].append(data)
        if self._caption is not None:
            self._caption.append(data)
        if self._li_stack:
            self._li_stack[-1]["text"].append(data)


def table_block(t):
    rows = [r for r in t["rows"] if any(c["text"] for c in r)]
    if len(rows) < 3:
        return None
    header = rows[0]
    if not any(c["th"] for c in header) and len(rows) > 1:
        header = [{"text": "列%d" % (i + 1)} for i in range(len(rows[0]))]
        body = rows
    else:
        body = rows[1:]
        # 多级表头：第二行也全是 th、且不是「合计」这类数字行时才合并
        numeric = sum(1 for c in body[0] if re.search(r"\d", c["text"])) if body else 0
        if body and all(c["th"] for c in body[0]) and len(body[0]) == len(header) and numeric < len(body[0]) / 2:
            header = [{"text": (h["text"] + " " + s["text"]).strip() if h["text"] != s["text"] else h["text"]}
                      for h, s in zip(header, body[0])]
            body = body[1:]
    cols, seen = [], {}
    for i, h in enumerate(header):
        name = h["text"] or "列%d" % (i + 1)
        seen[name] = seen.get(name, 0) + 1
        cols.append(name if seen[name] == 1 else "%s_%d" % (name, seen[name]))
    data = []
    for r in body:
        has_num = sum(1 for c in r if re.search(r"\d", c["text"])) >= len(r) / 2
        if all(c["th"] for c in r) and len(body) > 3 and not has_num:
            continue  # 表格中间的分组标题行（「合计」这类数字行保留，可用 --drop-rows 去掉）
        vals = [c["text"] for c in r][: len(cols)]
        if len(vals) < len(cols) * 0.6:
            continue
        vals += [""] * (len(cols) - len(vals))
        data.append(dict(zip(cols, vals)))
    if len(data) < 2:
        return None
    return {"kind": "table", "caption": t["caption"], "columns": cols, "rows": data}


def jsonld_blocks(items):
    out = []
    for doc in items:
        docs = doc if isinstance(doc, list) else doc.get("@graph", [doc]) if isinstance(doc, dict) else []
        for d in docs:
            if not isinstance(d, dict):
                continue
            elems = d.get("itemListElement")
            rows = []
            if isinstance(elems, list):
                for e in elems:
                    item = e.get("item", e) if isinstance(e, dict) else {}
                    if isinstance(item, dict):
                        rows.append({k: (v if isinstance(v, (str, int, float)) else json.dumps(v, ensure_ascii=False))
                                     for k, v in item.items() if not k.startswith("@")})
            elif d.get("@type"):
                rows.append({k: (v if isinstance(v, (str, int, float)) else json.dumps(v, ensure_ascii=False))
                             for k, v in d.items() if not k.startswith("@")})
            if rows:
                cols = sorted({k for r in rows for k in r})
                out.append({"kind": "jsonld", "caption": str(d.get("@type", "")), "columns": cols, "rows": rows})
    return out


def list_blocks(items):
    groups = {}
    for li in items:
        if 4 <= len(li["text"]) <= 200:
            groups.setdefault(li["depth"], []).append(li)
    out = []
    for depth, lis in groups.items():
        if len(lis) >= 5:
            rows = [{"文本": li["text"], "链接": li["href"] or ""} for li in lis]
            out.append({"kind": "list", "caption": "列表（第 %d 层）" % (depth + 1), "columns": ["文本", "链接"], "rows": rows})
    return out


def analyze(body):
    p = PageParser()
    p.feed(body)
    blocks = []
    for t in p.tables:
        b = table_block(t)
        if b and any("查论编" in c or "查看讨论编辑" in c for c in b["columns"]):
            continue  # 维基百科导航框
        if b:
            blocks.append(b)
    blocks.sort(key=lambda b: -len(b["rows"]))
    named = []
    for i, b in enumerate(blocks, 1):
        b["id"] = "t%d" % i
        named.append(b)
    for i, b in enumerate(jsonld_blocks(p.jsonld), 1):
        b["id"] = "j%d" % i
        named.append(b)
    for i, b in enumerate(list_blocks(p.lists)[:3], 1):
        b["id"] = "l%d" % i
        named.append(b)
    script_heavy = body.count("<script") > 20 and p.text_len < 2000
    return named, script_heavy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--pick", help="要导出的数据块 id（如 t1）")
    ap.add_argument("--out", default="rows.json")
    ap.add_argument("--refresh", action="store_true", help="不用本地缓存，重新请求")
    ap.add_argument("--drop-rows", help="去掉第一列匹配这个正则的行（如 合计|总计|全国）")
    ap.add_argument("--ignore-robots", action="store_true", help="仅限你拥有或已获授权的网站")
    args = ap.parse_args()

    ok, why = robots_allowed(args.url)
    print("合规检查：%s" % why)
    if not ok and not args.ignore_robots:
        sys.exit("🔴 该网站的 robots.txt 不允许抓取这个页面，已停止。请改用官方 API / 数据下载，或联系网站获取授权。")
    body, cached = fetch(args.url, args.refresh)
    blocks, script_heavy = analyze(body)
    if script_heavy or not blocks:
        print("🟡 页面像是前端渲染（HTML 里几乎没有正文）或没有可识别的数据块：改走浏览器路线，见 references/page-types.md")
    if not args.pick:
        print("\n页面：%s%s\n" % (args.url, "（本地缓存）" if cached else ""))
        print("| 数据块 | 类型 | 标题 | 行数 | 列 |\n|---|---|---|---|---|")
        for b in blocks[:15]:
            cols = "、".join(b["columns"][:8]) + ("…" if len(b["columns"]) > 8 else "")
            print("| %s | %s | %s | %d | %s |" % (b["id"], {"table": "表格", "jsonld": "结构化数据", "list": "列表"}[b["kind"]],
                                                 b["caption"][:24] or "—", len(b["rows"]), cols))
        if blocks:
            first = blocks[0]
            print("\n%s 前 3 行预览：" % first["id"])
            for r in first["rows"][:3]:
                print("  " + json.dumps(r, ensure_ascii=False)[:240])
        return
    block = next((b for b in blocks if b["id"] == args.pick), None)
    if not block:
        sys.exit("没有数据块 %s" % args.pick)
    rows = block["rows"]
    if args.drop_rows:
        first = block["columns"][0]
        before = len(rows)
        rows = [r for r in rows if not re.search(args.drop_rows, str(r.get(first, "")))]
        print("去掉 %d 行（第一列匹配 %s）" % (before - len(rows), args.drop_rows))
    out = {"source_url": args.url, "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"), "block": args.pick,
           "caption": block["caption"], "columns": block["columns"], "rows": rows}
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("✓ 已导出 %s：%d 行 × %d 列 → %s" % (args.pick, len(rows), len(block["columns"]), args.out))


if __name__ == "__main__":
    main()
