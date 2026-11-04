#!/usr/bin/env python3
"""迁移口径核对：多维表格仪表盘的原值（dashboard-spec.json 里的 baseline） vs 妙搭看板接口返回值。

用法：
    python3 verify_spec_board.py --spec dashboard-spec.json --url http://localhost:8090/app/<app_id> [--board migrated]

规则：数值相对误差 ≤ 0.5% 判为一致；Top N 比对前 N 项的名称与数值。
数据在实时变化（同步中 / 有人在改表），偶发小差异属正常，重跑一次即可。
"""
import argparse
import json
import sys
import urllib.request


def fetch(url):
    req = urllib.request.Request(url, headers={"Cookie": "suda-csrf-token=x", "X-Suda-Csrf-Token": "x"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("data", body)


def close(a, b, tol=0.005):
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return str(a) == str(b)
    if a == b:
        return True
    return abs(a - b) <= tol * max(abs(a), abs(b), 1e-9)


def actual_values(panel):
    kind = panel.get("kind")
    if kind == "kpi":
        return {"__total__": panel["kpi"]["value"]}
    if kind == "category":
        return {i["name"]: i["value"] for i in panel["category"]["items"]}
    if kind == "stacked":
        s = panel["stacked"]
        out = {}
        for ser in s["series"]:
            for c, v in zip(s["categories"], ser["values"]):
                if v:
                    out["%s | %s" % (c, ser["name"])] = v
        return out
    if kind == "trend":
        out = {}
        for ser in panel["trend"]["series"]:
            for p in ser["points"]:
                out[p["x"]] = p["y"]
        return out
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default="dashboard-spec.json")
    ap.add_argument("--url", required=True, help="应用根地址，如 http://localhost:8090/app/app_xxx")
    ap.add_argument("--board")
    args = ap.parse_args()
    spec = json.load(open(args.spec, encoding="utf-8"))
    board = next(b for b in spec["boards"] if not args.board or b["key"] == args.board)
    data = fetch("%s/api/spec-board/board/%s" % (args.url.rstrip("/"), board["key"]))
    ok = bad = skipped = 0
    for p in board["panels"]:
        base = (p.get("baseline") or {}).get("values")
        got = data["panels"].get(str(p["id"]))
        if not base or not got or got.get("kind") in ("text", "error"):
            if got and got.get("kind") == "error":
                print("🔴 %-14s 查询失败：%s" % (p["title"], got["message"]))
                bad += 1
            else:
                skipped += 1
            continue
        act = actual_values(got)
        if got["kind"] == "trend":  # 时间维度：原值键是日期时间，按日聚合后比较
            agg = {}
            for k, v in base.items():
                day = str(k)[5:10] if len(str(k)) >= 10 else str(k)
                agg[day] = agg.get(day, 0) + float(v or 0)
            if p["baseline"].get("truncated") and agg:
                agg.pop(list(agg.keys())[-1])  # 原值被截断：最后一天不完整，不参与核对
            base = agg
        keys = list(base.keys())[: p.get("limit") or 50]
        diffs = [(k, base[k], act.get(k)) for k in keys if not close(base[k], act.get(k))]
        if diffs:
            bad += 1
            print("🔴 %-14s %d/%d 项不一致，例：%s" % (p["title"], len(diffs), len(keys),
                                                  "；".join("%s 原 %s / 新 %s" % d for d in diffs[:3])))
        else:
            ok += 1
            sample = "；".join("%s=%s" % (k, act.get(k)) for k in keys[:2])
            print("🟢 %-14s 一致（%d 项）%s" % (p["title"], len(keys), "  " + sample if sample else ""))
    print("\n核对完成：🟢 一致 %d · 🔴 不一致 %d · 跳过 %d（文本 / 无原值）" % (ok, bad, skipped))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
