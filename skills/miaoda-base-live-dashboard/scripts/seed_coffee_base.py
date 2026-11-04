#!/usr/bin/env python3
"""一键创建「鹿野咖啡·连锁经营」演示多维表格并灌入数据。

用法（在任意工作目录运行，状态写到 ./.state/）：
    python3 seed_coffee_base.py            # 全流程：建库建表 → 写数据 → 建公式 → 建视图
    python3 seed_coffee_base.py --name "我的演示库"
    python3 seed_coffee_base.py --resume   # 中断后续跑（复用 .state/ 里的 base 与已写入进度）

完成后打印 base_url，并写入 .state/coffee-base.json（模拟下单脚本、同步配置都读它）。
"""
import argparse
import json
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coffee_demo as cd  # noqa: E402
import larkcli  # noqa: E402

STATE_DIR = ".state"
STATE_FILE = os.path.join(STATE_DIR, "coffee-base.json")
DATASET_FILE = os.path.join(STATE_DIR, "dataset.pkl")


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_state(st):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=2)


def load_dataset(resume):
    if resume and os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, "rb") as fh:
            return pickle.load(fh)
    ds = cd.generate_all()
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(DATASET_FILE, "wb") as fh:
        pickle.dump(ds, fh)
    return ds


def create_schema(st, name):
    if st.get("base_token"):
        log("复用已有 Base %s" % st["base_token"])
    else:
        first_name, first_fields = cd.TABLES[0]
        data = larkcli.run(["base", "+base-create", "--name", name, "--time-zone", cd.TZ,
                            "--table-name", first_name, "--fields", json.dumps(first_fields, ensure_ascii=False)])
        st["base_token"] = larkcli.find_key(data, "base_token") or larkcli.find_key(data, "app_token")
        st["base_url"] = larkcli.find_key(data, "url") or ""
        st["tables"] = {}
        tid = larkcli.find_key(data, "table_id")
        if tid:
            st["tables"][first_name] = tid
        save_state(st)
        log("已创建 Base：%s" % st["base_token"])
    if cd.TABLES[0][0] not in st["tables"]:
        tables = larkcli.run(["base", "+table-list", "--base-token", st["base_token"]])
        for t in larkcli.find_key(tables, "items") or larkcli.find_key(tables, "tables") or []:
            st["tables"][t.get("table_name") or t.get("name")] = t.get("table_id") or t.get("id")
        save_state(st)
    for tname, fields in cd.TABLES[1:]:
        if tname in st["tables"]:
            continue
        data = larkcli.run(["base", "+table-create", "--base-token", st["base_token"], "--name", tname,
                            "--fields", json.dumps(fields, ensure_ascii=False)])
        st["tables"][tname] = larkcli.find_key(data, "table_id") or larkcli.find_key(data, "id")
        save_state(st)
        log("已建表 %s → %s" % (tname, st["tables"][tname]))
    # 清掉 base-create 可能自带的默认空行
    first_tid = st["tables"][cd.TABLES[0][0]]
    if not st.get("cleaned_default_rows"):
        data = larkcli.run(["base", "+record-list", "--base-token", st["base_token"], "--table-id", first_tid,
                            "--limit", "50", "--format", "json"])
        ids = larkcli.find_key(data, "record_id_list") or []
        if ids:
            args = ["base", "+record-delete", "--base-token", st["base_token"], "--table-id", first_tid, "--yes"]
            for rid in ids:
                args += ["--record-id", rid]
            larkcli.run(args)
            log("清理首表默认空行 %d 条" % len(ids))
        st["cleaned_default_rows"] = True
        save_state(st)


def write_table(st, tname, keys, rows):
    """keys: 每行的业务主键（用于建立 业务键→record_id 映射）。支持断点续传。"""
    ids_map = st.setdefault("ids", {}).setdefault(tname, {})
    todo = [(k, r) for k, r in zip(keys, rows) if k not in ids_map]
    if not todo:
        log("%s 已写完（%d 条）" % (tname, len(ids_map)))
        return ids_map
    log("写入 %s：%d 条（已存在 %d）" % (tname, len(todo), len(ids_map)))
    batch = 200
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        got = larkcli.batch_create(st["base_token"], st["tables"][tname], [r for _, r in chunk])
        for (k, _), rid in zip(chunk, got):
            ids_map[k] = rid
        save_state(st)
        log("  %s %d/%d" % (tname, len(ids_map), len(ids_map) + len(todo) - i - len(chunk)))
    return ids_map


def write_data(st, ds):
    now = cd.now_local()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    store_ids = write_table(st, "门店", [s["name"] for s in ds["stores"]], [cd.store_row(s) for s in ds["stores"]])
    product_ids = write_table(st, "商品", [p[0] for p in cd.PRODUCTS],
                              [cd.product_row(p, i, today) for i, p in enumerate(cd.PRODUCTS)])
    campaign_ids = write_table(st, "营销活动", [c["name"] for c in ds["campaigns"]],
                               [cd.campaign_row(c) for c in ds["campaigns"]])
    member_ids = write_table(st, "会员", [m["card"] for m in ds["members"]],
                             [cd.member_row(m, store_ids) for m in ds["members"]])
    order_ids = write_table(st, "订单", [o["no"] for o in ds["orders"]],
                            [cd.order_row(o, store_ids, member_ids, campaign_ids) for o in ds["orders"]])
    write_table(st, "订单明细", [l["no"] for l in ds["items"]],
                [cd.item_row(l, order_ids, product_ids) for l in ds["items"]])
    st["last_order_seq"] = {}
    for o in ds["orders"]:
        day, seq = o["no"][2:10], int(o["no"].split("-")[1])
        st["last_order_seq"][day] = max(st["last_order_seq"].get(day, 0), seq)
    save_state(st)


def create_formulas(st):
    done = st.setdefault("formulas_done", [])
    for tname, fields in cd.FORMULAS.items():
        for f in fields:
            key = "%s.%s" % (tname, f["name"])
            if key in done:
                continue
            larkcli.run(["base", "+field-create", "--base-token", st["base_token"], "--table-id", st["tables"][tname],
                         "--json", json.dumps(f, ensure_ascii=False), "--i-have-read-guide"])
            done.append(key)
            save_state(st)
            log("公式字段 %s" % key)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="鹿野咖啡·连锁经营数据（演示）")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    st = load_state() if args.resume else {}
    if not args.resume and os.path.exists(STATE_FILE):
        sys.exit("已存在 %s；续跑请加 --resume，重新建库请先删除 .state/" % STATE_FILE)
    ds = load_dataset(args.resume)
    log("数据集：门店 %d / 商品 %d / 活动 %d / 会员 %d / 订单 %d / 明细 %d" % (
        len(ds["stores"]), len(cd.PRODUCTS), len(ds["campaigns"]), len(ds["members"]),
        len(ds["orders"]), len(ds["items"])))
    create_schema(st, args.name)
    write_data(st, ds)
    create_formulas(st)
    if not st.get("base_url"):
        info = larkcli.run(["base", "+base-get", "--base-token", st["base_token"]])
        st["base_url"] = larkcli.find_key(info, "url") or ""
        save_state(st)
    log("完成 ✅  Base: %s" % (st.get("base_url") or st["base_token"]))
    log("表：%s" % json.dumps(st["tables"], ensure_ascii=False))


if __name__ == "__main__":
    main()
