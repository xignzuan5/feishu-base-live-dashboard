#!/usr/bin/env python3
"""把 scrape_page.py 导出的 rows.json 写进飞书多维表格（推断字段类型、按主键去重、可反复运行做定期刷新）。

用法：
    python3 rows_to_base.py --rows rows.json --key 地区 --preview                       # 只看推断出的字段类型
    python3 rows_to_base.py --rows rows.json --key 地区 --new-base "各省 GDP（网页抓取）" --table 各省GDP
    python3 rows_to_base.py --rows rows.json --key 地区 --base-url <已有多维表格链接> --table 各省GDP

规则：
  - 字段类型：数字（去千分位、%、单位）、日期、链接、单选（取值少且重复多）、文本；主键列做主字段
  - 自动加「来源链接」「抓取时间」两列，方便溯源
  - 已有表时按主键 upsert：主键已存在 → 更新，不存在 → 新增；不删除旧行
  - 同一张表串行写入，每批 ≤ 200 条
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import larkcli  # noqa: E402

NUM = re.compile(r"^[+\-−]?[¥$€]?\s*[\d,]+(\.\d+)?\s*(%|万|亿|千)?$")
DATE = re.compile(r"^(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})日?$")
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
DATE_DMY = re.compile(r"^(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})$")   # 13 Jun 2025
DATE_MDY = re.compile(r"^([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})$")   # Jun 13, 2025 / June 13 2025


def parse_date(v):
    """返回 (年, 月, 日) 或 None。支持 2025-06-13、2025年6月13日、13 Jun 2025、June 13, 2025；
    不猜 06/07/2025 这类日月顺序有歧义的写法。"""
    v = v.strip()
    m = DATE.match(v)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m1, m2 = DATE_DMY.match(v), DATE_MDY.match(v)
        if m1:
            d, mon, y = int(m1.group(1)), m1.group(2), int(m1.group(3))
        elif m2:
            mon, d, y = m2.group(1), int(m2.group(2)), int(m2.group(3))
        else:
            return None
        mo = MONTHS.get(mon[:3].lower())
        if not mo:
            return None
    return (y, mo, d) if 1 <= mo <= 12 and 1 <= d <= 31 else None
URL = re.compile(r"^https?://")


def to_number(v):
    s = str(v).strip().replace(",", "").replace("−", "-").replace("¥", "").replace("$", "").replace("€", "")
    mult = 1.0
    for unit, m in (("亿", 1e8), ("万", 1e4), ("千", 1e3)):
        if s.endswith(unit):
            s, mult = s[: -len(unit)], m
    s = s.rstrip("%").strip()
    try:
        return float(s) * mult
    except ValueError:
        return None


def infer(columns, rows, key):
    fields = []
    for c in columns:
        vals = [str(r.get(c, "")).strip() for r in rows]
        filled = [v for v in vals if v not in ("", "—", "-", "N/A", "n/a")]
        n = max(len(filled), 1)
        if c == key:
            kind = "text"
        elif filled and sum(1 for v in filled if NUM.match(v.replace(" ", ""))) / n >= 0.9:
            kind = "number"
        elif filled and sum(1 for v in filled if parse_date(v)) / n >= 0.9:
            kind = "datetime"
        elif filled and sum(1 for v in filled if URL.match(v)) / n >= 0.9:
            kind = "url"
        elif filled and len(set(filled)) <= 20 and len(set(filled)) / n <= 0.5 and max(len(v) for v in filled) <= 16:
            kind = "select"
        else:
            kind = "text"
        f = {"name": c, "kind": kind}
        if kind == "select":
            f["options"] = sorted(set(filled), key=filled.index)
        fields.append(f)
    return fields


def field_json(f):
    k = f["kind"]
    if k == "number":
        pct = "%" in f["name"] or "率" in f["name"]
        return {"type": "number", "name": f["name"], "style": {"type": "plain", "precision": 2, "thousands_separator": not pct}}
    if k == "datetime":
        return {"type": "datetime", "name": f["name"], "style": {"format": "yyyy-MM-dd"}}
    if k == "url":
        return {"type": "text", "name": f["name"], "style": {"type": "url"}}
    if k == "select":
        hues = ["Blue", "Green", "Orange", "Purple", "Turquoise", "Red", "Yellow", "Carmine", "Wathet", "Lime"]
        return {"type": "select", "name": f["name"], "multiple": False,
                "options": [{"name": o, "hue": hues[i % len(hues)], "lightness": "Light"} for i, o in enumerate(f["options"])]}
    return {"type": "text", "name": f["name"]}


def cell(f, v):
    v = str(v).strip()
    if v in ("", "—", "-", "N/A", "n/a"):
        return None
    if f["kind"] == "number":
        return to_number(v)
    if f["kind"] == "datetime":
        ymd = parse_date(v)
        return "%d-%02d-%02d 00:00" % ymd if ymd else None
    if f["kind"] == "select":
        return [v]
    return v


def existing_keys(base_token, table, key):
    keys, offset = {}, 0
    while True:
        data = larkcli.run(["base", "+record-list", "--base-token", base_token, "--table-id", table, "--format", "json",
                            "--field-id", key, "--limit", "200", "--offset", str(offset)])
        ids = larkcli.find_key(data, "record_id_list") or []
        vals = data.get("data") or []
        for rid, row in zip(ids, vals):
            k = row[0] if isinstance(row, list) and row else None
            if isinstance(k, list):
                k = "".join(str(x.get("text", x)) if isinstance(x, dict) else str(x) for x in k)
            if k:
                keys[str(k)] = rid
        if not data.get("has_more"):
            return keys
        offset += len(ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default="rows.json")
    ap.add_argument("--key", help="主键列（用于去重 / 更新），默认第一列")
    ap.add_argument("--table", default="网页数据")
    ap.add_argument("--base-url", help="写进已有的多维表格")
    ap.add_argument("--new-base", help="新建一个多维表格，取这个名字")
    ap.add_argument("--preview", action="store_true", help="只看推断出的字段类型，不写入")
    args = ap.parse_args()
    src = json.load(open(args.rows, encoding="utf-8"))
    columns, rows = src["columns"], src["rows"]
    key = args.key or columns[0]
    if key not in columns:
        sys.exit("主键列「%s」不在列里：%s" % (key, "、".join(columns)))
    empty = [c for c in columns if c != key and not any(str(r.get(c, "")).strip() for r in rows)]
    if empty:
        print("跳过全空的列：%s" % "、".join(empty))
    cols = [key] + [c for c in columns if c != key and c not in empty]
    fields = infer(cols, rows, key)
    print("| 列 | 推断类型 | 示例 |\n|---|---|---|")
    for f in fields:
        sample = next((str(r.get(f["name"])) for r in rows if str(r.get(f["name"], "")).strip()), "")
        print("| %s | %s | %s |" % (f["name"], {"text": "文本", "number": "数字", "datetime": "日期", "url": "链接",
                                              "select": "单选（%d 项）" % len(f.get("options", []))}[f["kind"]], sample[:30]))
    dup = len(rows) - len({str(r.get(key)) for r in rows})
    if dup:
        print("🟡 主键「%s」有 %d 个重复值：同一主键只保留最后一行" % (key, dup))
    if args.preview:
        return
    if not args.base_url and not args.new_base:
        sys.exit("需要 --base-url 或 --new-base")
    schema = [field_json(f) for f in fields] + [
        {"type": "text", "name": "来源链接", "style": {"type": "url"}},
        {"type": "datetime", "name": "抓取时间", "style": {"format": "yyyy-MM-dd HH:mm"}},
    ]
    if args.new_base:
        data = larkcli.run(["base", "+base-create", "--name", args.new_base, "--time-zone", "Asia/Shanghai",
                            "--table-name", args.table, "--fields", json.dumps(schema, ensure_ascii=False)])
        token = larkcli.find_key(data, "base_token") or larkcli.find_key(data, "app_token")
        url = larkcli.find_key(data, "url") or ""
        # 新建时自带的空行先清掉
        stale = existing_keys(token, args.table, key)
        empties = larkcli.run(["base", "+record-list", "--base-token", token, "--table-id", args.table,
                               "--format", "json", "--limit", "50"])
        ids = [rid for rid in (larkcli.find_key(empties, "record_id_list") or []) if rid not in stale.values()]
        if ids:
            a = ["base", "+record-delete", "--base-token", token, "--table-id", args.table, "--yes"]
            for rid in ids:
                a += ["--record-id", rid]
            larkcli.run(a)
    else:
        token = re.search(r"/base/([A-Za-z0-9]+)", args.base_url).group(1)
        url = args.base_url
        tables = larkcli.run(["base", "+table-list", "--base-token", token])
        names = [t.get("name") for t in (tables.get("tables") or [])]
        if args.table not in names:
            larkcli.run(["base", "+table-create", "--base-token", token, "--name", args.table,
                         "--fields", json.dumps(schema, ensure_ascii=False)])
            print("已新建表「%s」" % args.table)
    have = existing_keys(token, args.table, key)
    by_key = {}
    for r in rows:
        rec = {f["name"]: cell(f, r.get(f["name"], "")) for f in fields}
        rec = {k: v for k, v in rec.items() if v is not None}
        rec["来源链接"] = src.get("source_url", "")
        rec["抓取时间"] = src.get("fetched_at", "")  # 带时区的 ISO 时间，避免被按多维表格时区误读
        by_key[str(r.get(key))] = rec
    creates = [v for k, v in by_key.items() if k not in have]
    updates = {have[k]: v for k, v in by_key.items() if k in have}
    if creates:
        larkcli.batch_create(token, args.table, creates)
    if updates:
        larkcli.batch_update(token, args.table, updates)
    print("✓ 新增 %d 条、更新 %d 条 → %s（表：%s）" % (len(creates), len(updates), url or token, args.table))


if __name__ == "__main__":
    main()
