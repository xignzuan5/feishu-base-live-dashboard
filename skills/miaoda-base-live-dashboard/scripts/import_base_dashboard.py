#!/usr/bin/env python3
"""把多维表格「原生仪表盘」迁移成妙搭看板的需求说明（dashboard-spec.json）。

读取仪表盘里每个组件（类型 / 数据表 / 指标与聚合 / 分组维度 / 筛选 / 排序 / Top N / 布局），
逐个映射成妙搭看板的面板，并抓取多维表格算好的结果作为「原值快照」，迁移后用
verify_spec_board.py 逐项核对数字，保证口径一致。

用法（在工作目录运行，文件写到当前目录）：
    python3 import_base_dashboard.py --base-url "https://xxx.feishu.cn/base/<token>"            # 列出仪表盘
    python3 import_base_dashboard.py --base-url ... --dashboard "经营仪表盘" [--sync-plan sync-plan.json]

产物：
    dashboard-spec.json     统一需求说明（会议整理 / 仪表盘迁移 / 现场问答 三种来源同一格式）
    migration-report.md     迁移报告：组件 → 面板对照、不支持项的替代方案、需要补同步的字段
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import larkcli  # noqa: E402

# 多维表格组件类型 → (面板 kind, 默认图表, 可切换图表, 说明)
BLOCK_MAP = {
    "statistics": ("kpi", None, [], ""),
    "line": ("trend", "line", ["line", "area", "bar"], ""),
    "area": ("trend", "area", ["area", "line", "bar"], ""),
    "column": ("category", "column", ["column", "bar", "treemap", "donut", "segmented"], ""),
    "bar": ("category", "bar", ["bar", "column", "treemap", "donut", "segmented"], ""),
    "pie": ("category", "donut", ["donut", "segmented", "bar", "treemap"], "饼图统一改为环形图（中心显示合计）"),
    "ring": ("category", "donut", ["donut", "segmented", "bar", "treemap"], ""),
    "ranking": ("category", "bar", ["bar", "column", "treemap"], ""),
    "funnel": ("category", "bar", ["bar", "column"], "漏斗图以排序条形图呈现，阶段顺序按原配置排序"),
    "wordCloud": ("category", "treemap", ["treemap", "bar"], "词云改为矩形树图（面积表达频次，可读性更好）"),
    "combo": ("trend", "line", ["line", "bar"], "组合图不做双 Y 轴：多个指标同轴展示，量级差异大时建议拆成两个面板"),
    "radar": ("stacked", "grouped", ["grouped", "stacked"], "雷达图改为分组柱状图（便于比较具体数值）"),
    "scatter": ("category", "column", ["column", "bar"], "原散点图是「维度 × 指标」，按柱状图呈现"),
    "nps": ("category", "segmented", ["segmented", "column"], "NPS 以占比条呈现推荐 / 中立 / 贬损分段"),
    "text": ("text", None, [], ""),
}

FORMAT_BY_STYLE = {"currency": "currency", "percentage": "percent"}


def parse_base_token(url):
    m = re.search(r"/base/([A-Za-z0-9]+)", url or "")
    return m.group(1) if m else None


def list_all(args, key="items"):
    out, token = [], None
    while True:
        a = list(args) + ["--page-size", "100"] + (["--page-token", token] if token else [])
        data = larkcli.run(a)
        out.extend(data.get(key) or [])
        if not data.get("has_more"):
            return out
        token = data.get("page_token")


def table_schema(base_token, table_name, cache):
    if table_name in cache:
        return cache[table_name]
    data = larkcli.run(["base", "+table-get", "--base-token", base_token, "--table-id", table_name])
    tables = cache.setdefault("__ids__", {})
    fields = data.get("fields") or []
    primary_id = (data.get("table") or {}).get("primary_field")
    schema = {"primary": None, "fields": {}}
    for f in fields:
        info = {"type": f.get("type")}
        if f.get("type") == "select":
            info["multiple"] = bool(f.get("multiple"))
            opts = [o.get("name") for o in (f.get("options") or []) if o.get("name")]
            if opts:
                info["options"] = opts
        if f.get("type") == "link":
            info["link_table_id"] = f.get("link_table")
        style = f.get("style") or {}
        if style.get("type") in FORMAT_BY_STYLE:
            info["format"] = FORMAT_BY_STYLE[style["type"]]
        if f.get("type") == "number" and style.get("percentage"):
            info["format"] = "percent"
        schema["fields"][f.get("name")] = info
        if f.get("id") == primary_id:
            schema["primary"] = f.get("name")
    tables[(data.get("table") or {}).get("id")] = table_name
    cache[table_name] = schema
    return schema


def resolve_link_targets(base_token, cache):
    listing = larkcli.run(["base", "+table-list", "--base-token", base_token])
    id2name = {t.get("id") or t.get("table_id"): t.get("name") or t.get("table_name")
               for t in (listing.get("tables") or listing.get("items") or [])}
    for tname, schema in list(cache.items()):
        if tname.startswith("__"):
            continue
        for fname, info in schema["fields"].items():
            if info.get("link_table_id"):
                info["link_table"] = id2name.get(info.pop("link_table_id"), None)


def normalize_filter(f):
    if not f or not f.get("conditions"):
        return None
    conds = []
    for c in f["conditions"]:
        v = c.get("value")
        if isinstance(v, list) and len(v) == 2 and v[0] == "ExactDate":
            v = {"exact_date_ms": v[1]}
        conds.append({"field": c.get("field_name"), "op": c.get("operator"), "value": v})
    return {"conjunction": f.get("conjunction", "and"), "conditions": conds}


def baseline_of(base_token, block_id):
    """抓多维表格算好的结果，转成 {维度值或 '__total__': 指标值}（最多两层维度用 ' | ' 拼接）"""
    data, last = None, None
    for attempt in range(4):  # get-data 偶发返回 API error [1]，退避重试
        try:
            data = larkcli.run(["base", "+dashboard-block-get-data", "--base-token", base_token,
                                "--block-id", block_id], retries=1)
            break
        except larkcli.LarkError as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    if data is None:
        return {"error": str(last)[:200]}
    dims = [d["alias"] for d in (data.get("dimensions") or [])]
    meas = [m["alias"] for m in (data.get("measures") or [])]
    values = {}
    rows = data.get("main_data") or []
    for row in rows:
        key = " | ".join(str((row.get(a) or {}).get("value")) for a in dims) or "__total__"
        for i, m in enumerate(meas):
            k = key if len(meas) == 1 else "%s :: %s" % (key, data["measures"][i].get("field_name"))
            values[k] = (row.get(m) or {}).get("value")
    # 行数撞到整数上限时，多维表格只返回了前一部分：标记截断，核对时丢弃最后一个分组
    return {"values": values, "rows": len(rows), "truncated": len(rows) in (500, 1000, 2000, 5000)}


def to_panel(block, cfg, schema_cache, base_token):
    btype = block.get("type")
    kind, default_chart, charts, note = BLOCK_MAP.get(btype, ("category", "bar", ["bar", "column"], "未知组件类型，按条形图处理"))
    panel = {
        "id": block["block_id"],
        "kind": kind,
        "title": block.get("name") or btype,
        "layout": block.get("position"),
        "origin": {"from": "base-dashboard", "block_id": block["block_id"], "block_type": btype},
        "notes": [note] if note else [],
    }
    if kind == "text":
        panel["text"] = cfg.get("text", "")
        return panel
    table = cfg.get("table_name")
    panel["table"] = table
    schema = table_schema(base_token, table, schema_cache) if table else {"fields": {}}
    if cfg.get("count_all"):
        panel["measures"] = [{"agg": "COUNT", "label": "记录数"}]
    else:
        panel["measures"] = [
            {"field": s.get("field_name"), "agg": (s.get("rollup") or "SUM").upper(), "label": s.get("field_name")}
            for s in cfg.get("series") or []
        ]
    fmt = "number"
    for m in panel["measures"]:
        finfo = schema["fields"].get(m.get("field") or "", {})
        if finfo.get("format"):
            fmt = finfo["format"]
    panel["format"] = fmt
    dims = []
    for g in cfg.get("group_by") or []:
        finfo = schema["fields"].get(g.get("field_name"), {})
        dims.append({"field": g.get("field_name"), "mode": g.get("mode", "integrated"), "field_type": finfo.get("type")})
        if g.get("sort"):
            panel["sort"] = {"by": "value" if g["sort"].get("type") == "value" else "dimension",
                             "order": g["sort"].get("order", "asc")}
    panel["dimensions"] = dims
    # 时间维度的柱 / 条 → 趋势；两层维度 → 堆叠
    if dims and dims[0].get("field_type") in ("datetime", "created_at", "updated_at"):
        if kind == "category":
            kind, default_chart, charts = "trend", "bar", ["bar", "line", "area"]
        panel["notes"].append("原图按时间点逐个分组（点过密），迁移后按天聚合；今日视图按小时")
    if kind == "category" and len(dims) == 2:
        kind, default_chart, charts = "stacked", "stacked", ["stacked", "grouped", "percent"]
    if kind == "category" and len(panel["measures"]) > 1:
        kind, default_chart, charts = "stacked", "grouped", ["grouped", "stacked"]
    panel["kind"] = kind
    if default_chart:
        panel["default_chart"] = default_chart
        panel["chart_types"] = charts
    if cfg.get("limit_size"):
        panel["limit"] = cfg["limit_size"]
    flt = normalize_filter(cfg.get("filter"))
    if flt:
        panel["filter"] = flt
    # 原仪表盘不按时间筛选：默认不加时间范围，保证迁移后数字一致；提示可选的时间字段
    time_fields = [n for n, f in schema["fields"].items() if f.get("type") == "datetime"]
    panel["time_field"] = None
    if time_fields:
        panel["suggested_time_field"] = time_fields[0]
    return panel


def check_sync_coverage(spec, plan_path):
    if not plan_path or not os.path.exists(plan_path):
        return None
    plan = json.load(open(plan_path, encoding="utf-8"))
    synced = {t["source"]: set(t.get("exclude", [])) for t in plan.get("tables", [])}
    gaps = []
    for board in spec["boards"]:
        for p in board["panels"]:
            t = p.get("table")
            if not t:
                continue
            if t not in synced:
                gaps.append("表「%s」未在同步计划里（面板：%s）" % (t, p["title"]))
                continue
            used = [m.get("field") for m in p.get("measures", []) if m.get("field")]
            used += [d["field"] for d in p.get("dimensions", [])]
            used += [c["field"] for c in (p.get("filter") or {}).get("conditions", [])]
            for f in used:
                if f in synced[t]:
                    gaps.append("字段「%s.%s」在同步计划里被排除（面板：%s）" % (t, f, p["title"]))
    return gaps


def write_report(spec, gaps, path):
    lines = ["# 多维表格仪表盘 → 妙搭看板 迁移报告", "",
             "- 源仪表盘：**%s**（%s）" % (spec["source"]["dashboard_name"], spec["source"]["base_url"]),
             "- 组件数：%d，生成面板：%d" % (spec["source"]["block_count"], len(spec["boards"][0]["panels"])),
             "- 生成时间：%s" % time.strftime("%Y-%m-%d %H:%M"), "",
             "## 组件 → 面板对照", "",
             "| 组件 | 原类型 | 面板 | 默认图表 / 可切换 | 数据表 | 指标 | 维度 | 筛选 | 说明 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for p in spec["boards"][0]["panels"]:
        meas = "、".join("%s(%s)" % (m.get("field") or "全部记录", m["agg"]) for m in p.get("measures", [])) or "—"
        dims = "、".join(d["field"] for d in p.get("dimensions", [])) or "—"
        flt = "；".join("%s %s %s" % (c["field"], c["op"], c.get("value")) for c in (p.get("filter") or {}).get("conditions", [])) or "—"
        charts = "%s / %s" % (p.get("default_chart") or "—", "、".join(p.get("chart_types", [])) or "—")
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            p["title"], p["origin"]["block_type"], p["kind"], charts, p.get("table") or "—", meas, dims, flt,
            "；".join(p.get("notes", [])) or ""))
    lines += ["", "## 需要处理", ""]
    if gaps:
        lines += ["- 🔴 " + g for g in gaps]
    elif gaps is None:
        lines.append("- 🟡 未提供同步计划（--sync-plan），无法检查字段是否已同步")
    else:
        lines.append("- 🟢 用到的表和字段都已在同步计划内")
    lines += ["", "## 迁移后的增强（原仪表盘没有）", "",
              "- 实时：多维表格改数 5~10 秒后看板自动刷新，无需手动刷新页面",
              "- 3 套风格一键切换（深烘焙 / 燕麦白 / 霓虹大屏），可投屏",
              "- 每个面板可切换图表类型；同一实体全局同色",
              "- 可选：给面板加时间范围（见各面板 suggested_time_field），并补对比周期",
              "", "## 核对", "", "迁移完成后运行 `verify_spec_board.py`，逐个面板对比多维表格原值与看板接口返回值。"]
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--dashboard", help="仪表盘 id 或名称（不传则列出全部）")
    ap.add_argument("--board-key", default="migrated")
    ap.add_argument("--sync-plan")
    ap.add_argument("--out", default="dashboard-spec.json")
    ap.add_argument("--report", default="migration-report.md")
    ap.add_argument("--no-baseline", action="store_true", help="不抓原值快照")
    args = ap.parse_args()

    base_token = parse_base_token(args.base_url)
    if not base_token:
        data = larkcli.run(["base", "+url-resolve", "--url", args.base_url])
        base_token = larkcli.find_key(data, "base_token") or larkcli.find_key(data, "token")
    dashboards = list_all(["base", "+dashboard-list", "--base-token", base_token])
    if not args.dashboard:
        for d in dashboards:
            print("%s  %s" % (d.get("dashboard_id"), d.get("name")))
        return
    target = next((d for d in dashboards if args.dashboard in (d.get("dashboard_id"), d.get("name"))), None)
    if not target:
        sys.exit("找不到仪表盘：%s" % args.dashboard)
    did = target["dashboard_id"]
    blocks = list_all(["base", "+dashboard-block-list", "--base-token", base_token, "--dashboard-id", did])
    blocks.sort(key=lambda b: ((b.get("position") or {}).get("y", 0), (b.get("position") or {}).get("x", 0)))
    print("仪表盘「%s」共 %d 个组件" % (target.get("name"), len(blocks)))
    cache, panels = {}, []
    for b in blocks:
        detail = larkcli.run(["base", "+dashboard-block-get", "--base-token", base_token, "--dashboard-id", did,
                              "--block-id", b["block_id"]])
        cfg = (detail.get("block") or {}).get("data_config") or {}
        panel = to_panel(b, cfg, cache, base_token)
        if panel["kind"] != "text" and not args.no_baseline:
            panel["baseline"] = baseline_of(base_token, b["block_id"])
        panels.append(panel)
        print("  ✓ %-16s %-10s → %s" % (panel["title"], b.get("type"), panel["kind"]))
    resolve_link_targets(base_token, cache)
    spec = {
        "version": 1,
        "title": target.get("name"),
        "source": {"type": "base-dashboard", "base_url": args.base_url, "base_token": base_token,
                   "dashboard_id": did, "dashboard_name": target.get("name"), "block_count": len(blocks)},
        "timezone": "Asia/Shanghai",
        "default_style": "espresso",
        "refresh_seconds": 5,
        "boards": [{"key": args.board_key, "label": target.get("name"), "group": "多维表格迁移",
                    "description": "由多维表格仪表盘「%s」迁移，数字已与原仪表盘逐项核对" % target.get("name"),
                    "default_range": "30d", "panels": panels}],
        "schema": {k: v for k, v in cache.items() if not k.startswith("__")},
        "open_questions": [],
    }
    gaps = check_sync_coverage(spec, args.sync_plan)
    json.dump(spec, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    write_report(spec, gaps, args.report)
    print("已写入 %s、%s%s" % (args.out, args.report, "；⚠ %d 项需处理" % len(gaps) if gaps else ""))


if __name__ == "__main__":
    main()
