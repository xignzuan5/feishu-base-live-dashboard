#!/usr/bin/env python3
"""把一份或多份 dashboard-spec.json 编译成看板引擎配置 spec.generated.ts。

字段名 → 数据库列名：读取同步计划对应的 dev 最终映射（sync/<目标表>.dev.final.json）；
字段类型：读 spec 里的 schema（没有就用 lark-cli 现查多维表格）。

用法（在同步计划所在目录运行）：
    python3 build_spec_bundle.py --pair dashboard-spec.json:sync-plan.json --app ../my-app
    python3 build_spec_bundle.py --pair a.spec.json:a-plan.json --pair b.spec.json:b-plan.json --app ../my-app --title "经营看板合集"

多份 spec 可来自不同的多维表格：表会按 Base 区分命名空间，互不冲突。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_base_dashboard as ibd  # noqa: E402

KIND_DEFAULT_CHARTS = {
    "trend": ("area", ["area", "line", "bar"]),
    "category": ("bar", ["bar", "column", "treemap", "donut", "segmented"]),
    "stacked": ("stacked", ["stacked", "grouped", "percent"]),
}


def field_type(base_info, pg_field):
    t = (base_info or {}).get("type")
    pg_t = (pg_field or {}).get("type", "")
    if t == "select":
        return "multiselect" if base_info.get("multiple") else "select"
    if t in ("datetime", "created_at", "updated_at"):
        return "date" if pg_t == "date" else "datetime"
    if t in ("number", "checkbox", "link", "formula", "text"):
        return t
    if t in ("auto_number", "phone", "url", "email"):
        return "text"
    if pg_t in ("numeric", "int8", "int4", "float8"):
        return "number"
    if pg_t == "jsonb":
        return "link"
    return "other"


def build_tables(spec, plan, plan_dir, ns):
    sync_dir = os.path.join(plan_dir, "sync")
    schema = spec.get("schema") or {}
    base_token = (spec.get("source") or {}).get("base_token") or ibd.parse_base_token(plan.get("base_url", ""))
    cache = {}
    tables, warnings = {}, []
    for t in plan["tables"]:
        src, target = t["source"], t["target"]
        final = os.path.join(sync_dir, "%s.dev.final.json" % target)
        if not os.path.exists(final):
            warnings.append("缺少 %s：先运行 sync_base_to_miaoda.py 建同步" % final)
            continue
        cfg = json.load(open(final, encoding="utf-8"))
        tschema = schema.get(src)
        if not tschema and base_token:
            tschema = ibd.table_schema(base_token, src, cache)
        fields = {}
        for fm in cfg.get("field_maps", []):
            if fm.get("enabled", True) is False:
                continue
            bname = (fm.get("base_field") or {}).get("name")
            binfo = (tschema or {}).get("fields", {}).get(bname, {})
            entry = {"col": fm["pg_field"]["name"], "type": field_type(binfo, fm.get("pg_field"))}
            if entry["type"] == "link" and binfo.get("link_table"):
                entry["target"] = "%s:%s" % (ns, binfo["link_table"])
            fields[bname] = entry
        tables["%s:%s" % (ns, src)] = {"pg": target, "primary": (tschema or {}).get("primary") or "", "fields": fields}
    if cache:
        ibd.resolve_link_targets(base_token, cache)
        for key, tm in tables.items():
            src = key.split(":", 1)[1]
            for bname, f in tm["fields"].items():
                link = cache.get(src, {}).get("fields", {}).get(bname, {}).get("link_table")
                if f["type"] == "link" and link:
                    f["target"] = "%s:%s" % (ns, link)
    return tables, warnings


def measure(m):
    out = {"field": m.get("field"), "agg": (m.get("agg") or "SUM").upper(),
           "label": m.get("label") or m.get("field") or "记录数"}
    if m.get("where"):
        out["where"] = m["where"]
    if out["field"] is None:
        out.pop("field")
    return out


def camel_panel(p, ns):
    kind = p.get("kind", "category")
    default_chart, charts = KIND_DEFAULT_CHARTS.get(kind, (None, []))
    out = {
        "id": str(p["id"]),
        "kind": kind,
        "title": p.get("title", ""),
        "measures": [measure(m) for m in p.get("measures", [])],
        "dimensions": [dict({"field": d["field"], "mode": d.get("mode", "integrated")},
                            **({"order": d["order"]} if d.get("order") else {}),
                            **({"via": d["via"]} if d.get("via") else {})) for d in p.get("dimensions", [])],
        "timeField": p.get("time_field"),
        "format": p.get("format", "number"),
        "chartTypes": p.get("chart_types") or charts,
        "notes": p.get("notes", []),
    }
    if p.get("table"):
        out["table"] = "%s:%s" % (ns, p["table"])
    for k_src, k_dst in (("subtitle", "subtitle"), ("limit", "limit"), ("layout", "layout"), ("text", "text"),
                         ("sort", "sort"), ("filter", "filter"), ("compute", "compute"), ("good_when", "goodWhen"),
                         ("columns", "columns"), ("alert", "alert")):
        if p.get(k_src) is not None:
            out[k_dst] = p[k_src]
    if p.get("default_chart") or default_chart:
        out["defaultChart"] = p.get("default_chart") or default_chart
    for k in [k for k, v in out.items() if v is None]:
        if k != "timeField":
            out.pop(k)
    return out


def validate(boards, tables):
    problems = []
    for b in boards:
        for p in b["panels"]:
            if p["kind"] == "text":
                continue
            t = tables.get(p.get("table", ""))
            if not t:
                problems.append("[%s/%s] 表 %s 未同步" % (b["key"], p["title"], p.get("table")))
                continue
            used = [m["field"] for m in p["measures"] if m.get("field")] + [d["field"] for d in p["dimensions"]]
            used += [c["field"] for m in p["measures"] for c in m.get("where", [])]
            used += list(p.get("columns") or [])
            if (p.get("sort") or {}).get("field"):
                used.append(p["sort"]["field"])
            used += [c["field"] for c in (p.get("filter") or {}).get("conditions", [])]
            if p.get("timeField"):
                used.append(p["timeField"])
            for f in used:
                if f not in t["fields"]:
                    problems.append("[%s/%s] 字段 %s 未同步" % (b["key"], p["title"], f))
            for d in p["dimensions"]:
                fm = t["fields"].get(d["field"])
                if fm and fm["type"] == "link" and fm.get("target") not in tables:
                    problems.append("[%s/%s] 关联字段 %s 的目标表未同步" % (b["key"], p["title"], d["field"]))
                elif fm and d.get("via"):
                    tgt = tables.get(fm.get("target", ""), {})
                    if fm["type"] != "link":
                        problems.append("[%s/%s] via 只能用在关联字段上：%s" % (b["key"], p["title"], d["field"]))
                    elif d["via"] not in tgt.get("fields", {}):
                        problems.append("[%s/%s] 关联表里没有字段 %s（或未同步）" % (b["key"], p["title"], d["via"]))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", action="append", required=True, help="spec.json:sync-plan.json")
    ap.add_argument("--app", required=True, help="妙搭应用仓库目录")
    ap.add_argument("--title")
    args = ap.parse_args()
    bundle = {"title": args.title or "", "timezone": "Asia/Shanghai", "entities": [], "boards": [], "tables": {}}
    all_warn = []
    ns_by_base = {}
    for i, pair in enumerate(args.pair):
        spec_path, plan_path = pair.split(":", 1)
        spec = json.load(open(spec_path, encoding="utf-8"))
        plan = json.load(open(plan_path, encoding="utf-8"))
        # 同一个多维表格的多份 spec 共用一组表映射
        base_key = plan.get("base_url") or plan_path
        if base_key in ns_by_base:
            ns = ns_by_base[base_key]
        else:
            ns = ns_by_base[base_key] = "b%d" % (len(ns_by_base) + 1)
            tables, warns = build_tables(spec, plan, os.path.dirname(os.path.abspath(plan_path)), ns)
            all_warn += warns
            bundle["tables"].update(tables)
        bundle["timezone"] = spec.get("timezone", bundle["timezone"])
        bundle["title"] = bundle["title"] or spec.get("title", "")
        # 实体固定配色组：spec 显式给的 entities + 所有维度的固定顺序 order
        for grp in spec.get("entities", []):
            if grp not in bundle["entities"]:
                bundle["entities"].append(grp)
        for b in spec.get("boards", []):
            for p in b.get("panels", []):
                for d in p.get("dimensions", []):
                    if d.get("order") and d["order"] not in bundle["entities"]:
                        bundle["entities"].append(d["order"])
        for b in spec.get("boards", []):
            board = {"key": b["key"], "label": b.get("label", b["key"]), "description": b.get("description", ""),
                     "group": b.get("group") or spec.get("group") or spec.get("title") or "看板",
                     "defaultRange": b.get("default_range", "30d"),
                     "panels": [camel_panel(p, ns) for p in b.get("panels", [])]}
            if b.get("layout"):
                board["layout"] = b["layout"]
            if b.get("style") or spec.get("default_style"):
                board["style"] = b.get("style") or spec.get("default_style")
            bundle["boards"].append(board)
    problems = validate(bundle["boards"], bundle["tables"])
    out = os.path.join(args.app, "server/modules/blueprint/spec.generated.ts")
    body = json.dumps(bundle, ensure_ascii=False, indent=2)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("/** auto generated by build_spec_bundle.py — 不要手改，改 dashboard-spec.json 后重新生成 */\n")
        fh.write("import type { SpecBundle } from './spec.types';\n\n")
        fh.write("export const SPEC_BUNDLE: SpecBundle = %s;\n" % body)
    print("✓ 已生成 %s：%d 个看板、%d 张表" % (out, len(bundle["boards"]), len(bundle["tables"])))
    for w in all_warn + problems:
        print("  ⚠ " + w)


if __name__ == "__main__":
    main()
