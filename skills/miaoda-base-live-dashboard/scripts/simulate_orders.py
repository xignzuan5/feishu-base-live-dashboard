#!/usr/bin/env python3
"""模拟实时下单：每隔 N 秒往「订单 / 订单明细」表写一单，并把较早的「制作中/配送中」订单推进为「已完成」。

演示时开着它，看板的实时订单流、今日营收、最近 60 分钟柱图都会跟着动。

用法（在 seed_coffee_base.py 的同一工作目录运行，读取 .state/coffee-base.json）：
    python3 simulate_orders.py                  # 默认每 6 秒一单，Ctrl+C 停止
    python3 simulate_orders.py --interval 3 --count 50
    python3 simulate_orders.py --burst 10       # 立刻连下 10 单（演示“高峰”）
"""
import argparse
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coffee_demo as cd  # noqa: E402
import larkcli  # noqa: E402

STATE_FILE = os.path.join(".state", "coffee-base.json")
DATASET_FILE = os.path.join(".state", "dataset.pkl")


def load():
    if not os.path.exists(STATE_FILE):
        sys.exit("找不到 %s：先在本目录运行 seed_coffee_base.py" % STATE_FILE)
    with open(STATE_FILE, encoding="utf-8") as fh:
        st = json.load(fh)
    import pickle
    with open(DATASET_FILE, "rb") as fh:
        ds = pickle.load(fh)
    return st, ds


def save(st):
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=2)


def place_order(st, ds, rng, pending):
    now = cd.now_local()
    stores = [s for s in ds["stores"] if s["status"] != "装修升级"]
    store = cd.wchoice(rng, [(s, s["weight"]) for s in stores])
    members_by_store = {}
    for m in ds["members"]:
        members_by_store.setdefault(m["home"]["name"], []).append(m)
    day = now.strftime("%Y%m%d")
    seq = st.setdefault("last_order_seq", {}).get(day, 0) + 1
    st["last_order_seq"][day] = seq
    order, lines = cd.gen_order(rng, now, store, members_by_store, ds["members"], ds["campaigns"], seq, recent=True)
    ids = st["ids"]
    row = cd.order_row(order, ids["门店"], ids["会员"], ids["营销活动"])
    order_id = larkcli.batch_create(st["base_token"], st["tables"]["订单"], [row])[0]
    ids["订单"][order["no"]] = order_id
    item_rows = [cd.item_row(l, {order["no"]: order_id}, ids["商品"]) for l in lines]
    larkcli.batch_create(st["base_token"], st["tables"]["订单明细"], item_rows)
    pending.append((time.time(), order_id))
    save(st)
    names = "、".join("%s×%d" % (l["product"], l["qty"]) if l["qty"] > 1 else l["product"] for l in lines)
    print("[%s] 新订单 %s  %s  %s  ¥%.2f  %s" % (
        now.strftime("%H:%M:%S"), order["no"], store["name"].replace("鹿野咖啡·", ""),
        order["channel"], order["paid"], names), flush=True)


def complete_old(st, pending, older_than):
    """把 older_than 秒前下的单改成已完成（看板上状态会从「制作中」变「已完成」）"""
    due = [p for p in pending if time.time() - p[0] > older_than]
    if not due:
        return
    updates = {rid: {"订单状态": ["已完成"], "评价星级": random.choice([4, 5, 5, None])} for _, rid in due}
    for rid in list(updates):
        if updates[rid]["评价星级"] is None:
            updates[rid].pop("评价星级")
    larkcli.batch_update(st["base_token"], st["tables"]["订单"], updates)
    for p in due:
        pending.remove(p)
    print("           ↳ %d 单已出餐/送达 → 已完成" % len(due), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=6.0, help="下单间隔秒数")
    ap.add_argument("--count", type=int, default=0, help="下多少单后停止（0=一直跑）")
    ap.add_argument("--burst", type=int, default=0, help="立即连续下 N 单后退出")
    ap.add_argument("--complete-after", type=float, default=45.0, help="多少秒后把订单改为已完成")
    args = ap.parse_args()
    st, ds = load()
    rng = random.Random()
    pending = []
    if args.burst:
        for _ in range(args.burst):
            place_order(st, ds, rng, pending)
        return
    n = 0
    print("开始模拟下单（每 %.0f 秒一单），Ctrl+C 停止" % args.interval, flush=True)
    try:
        while args.count == 0 or n < args.count:
            place_order(st, ds, rng, pending)
            complete_old(st, pending, args.complete_after)
            n += 1
            time.sleep(max(0.5, rng.uniform(args.interval * 0.5, args.interval * 1.5)))
    except KeyboardInterrupt:
        print("\n已停止，共下单 %d 笔" % n)


if __name__ == "__main__":
    main()
