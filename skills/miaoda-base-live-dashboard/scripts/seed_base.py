#!/usr/bin/env python3
"""通用演示数据造数器：按「领域包」建一个多维表格并灌入有业务规律的数据。

用法（状态写到 ./.state/<domain>-base.json，可断点续跑）：
    python3 seed_base.py --domain work      # 工作 / 项目管理
    python3 seed_base.py --domain crm       # 客户管理
    python3 seed_base.py --domain crm --resume

领域包 = scripts/domains/<domain>.py，需提供：
    BASE_NAME: str                         多维表格名称
    TABLES: [(表名, [字段 JSON...]), ...]  依赖顺序：关联字段只能指向前面已建的表
    FORMULAS: {表名: [公式字段 JSON...]}  数据写完后再建（避免逐批重算）
    generate(now: datetime) -> {表名: [行...]}
        每行是 {字段名: 值}；必须带 "$key"（表内唯一的业务键）；
        关联字段写成 {"$link": "目标表名", "keys": ["业务键", ...]}，由本脚本换成 record_id。
"""
import argparse
import importlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import larkcli  # noqa: E402

STATE_DIR = ".state"


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def resolve_links(row, ids):
    out = {}
    for k, v in row.items():
        if k == "$key":
            continue
        if isinstance(v, dict) and "$link" in v:
            target = ids.get(v["$link"], {})
            rec = [{"id": target[key]} for key in v.get("keys", []) if key in target]
            if rec:
                out[k] = rec
            continue
        out[k] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--time-zone", default="Asia/Shanghai")
    args = ap.parse_args()
    dom = importlib.import_module("domains.%s" % args.domain)
    state_file = os.path.join(STATE_DIR, "%s-base.json" % args.domain)
    os.makedirs(STATE_DIR, exist_ok=True)
    st = json.load(open(state_file, encoding="utf-8")) if (args.resume and os.path.exists(state_file)) else {}
    if not args.resume and os.path.exists(state_file):
        sys.exit("已存在 %s；续跑加 --resume，重建先删掉它" % state_file)

    def save():
        json.dump(st, open(state_file, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 1. 建库建表
    if not st.get("base_token"):
        first, fields = dom.TABLES[0]
        data = larkcli.run(["base", "+base-create", "--name", dom.BASE_NAME, "--time-zone", args.time_zone,
                            "--table-name", first, "--fields", json.dumps(fields, ensure_ascii=False)])
        st["base_token"] = larkcli.find_key(data, "base_token") or larkcli.find_key(data, "app_token")
        st["base_url"] = larkcli.find_key(data, "url") or ""
        st["tables"] = {}
        save()
        log("已创建多维表格：%s" % (st["base_url"] or st["base_token"]))
        listing = larkcli.run(["base", "+table-list", "--base-token", st["base_token"]])
        for t in listing.get("tables") or listing.get("items") or []:
            st["tables"][t.get("name") or t.get("table_name")] = t.get("id") or t.get("table_id")
        # base-create 会带默认空行，清掉
        # 1.0.98 起 +record-list 默认写 ndjson 文件；用 --format json 直接拿 record_id_list
        recs = larkcli.run(["base", "+record-list", "--base-token", st["base_token"], "--table-id", first,
                            "--limit", "50", "--format", "json"])
        rids = larkcli.find_key(recs, "record_id_list") or []
        if rids:
            a = ["base", "+record-delete", "--base-token", st["base_token"], "--table-id", first, "--yes"]
            for r in rids:
                a += ["--record-id", r]
            larkcli.run(a)
        save()
    for name, fields in dom.TABLES[1:]:
        if name in st["tables"]:
            continue
        data = larkcli.run(["base", "+table-create", "--base-token", st["base_token"], "--name", name,
                            "--fields", json.dumps(fields, ensure_ascii=False)])
        st["tables"][name] = larkcli.find_key(data, "table_id") or larkcli.find_key(data, "id")
        save()
        log("已建表 %s" % name)

    # 2. 生成并写入数据（业务键 → record_id）
    rows_by_table = dom.generate()
    st.setdefault("ids", {})
    for name, _ in dom.TABLES:
        rows = rows_by_table.get(name, [])
        done = st["ids"].setdefault(name, {})
        todo = [r for r in rows if r["$key"] not in done]
        if not todo:
            continue
        log("写入 %s：%d 条" % (name, len(todo)))
        for i in range(0, len(todo), 200):
            chunk = todo[i:i + 200]
            got = larkcli.batch_create(st["base_token"], st["tables"][name],
                                       [resolve_links(r, st["ids"]) for r in chunk])
            for r, rid in zip(chunk, got):
                done[r["$key"]] = rid
            save()

    # 3. 公式字段
    st.setdefault("formulas_done", [])
    for name, fields in getattr(dom, "FORMULAS", {}).items():
        for f in fields:
            key = "%s.%s" % (name, f["name"])
            if key in st["formulas_done"]:
                continue
            larkcli.run(["base", "+field-create", "--base-token", st["base_token"], "--table-id", st["tables"][name],
                         "--json", json.dumps(f, ensure_ascii=False), "--i-have-read-guide"])
            st["formulas_done"].append(key)
            save()
            log("公式字段 %s" % key)
    if not st.get("base_url"):
        info = larkcli.run(["base", "+base-get", "--base-token", st["base_token"]])
        st["base_url"] = larkcli.find_key(info, "url") or ""
        save()
    log("完成 ✅ %s  表：%s" % (st.get("base_url"), ", ".join("%s(%d)" % (k, len(v)) for k, v in st["ids"].items())))


if __name__ == "__main__":
    main()
