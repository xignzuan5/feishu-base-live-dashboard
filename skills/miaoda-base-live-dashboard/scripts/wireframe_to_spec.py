#!/usr/bin/env python3
"""线框稿 wireframe.json（来自画板 / 图片 / 截图）+ 多维表格结构 → dashboard-spec.json 草稿。

用法：
    python3 wireframe_to_spec.py --wireframe wireframe.json --base-url <多维表格链接> \
        [--glossary glossary.json] [--board-key sketch] [--out dashboard-spec.json]

做的事：
  1. 识别类型 → 面板 kind / 默认图表 / 可切换图表（见 wireframe_lib.VISUALS）
  2. 草图坐标 → 12 栅格 layout（排版默认「原始布局」，保持草图的位置关系）
  3. 标题业务词 → 多维表格的表与字段：同义词 + 字面相似度打分，挑出表、指标字段、维度字段、时间字段
     - 「额 / 金额 / 营收」→ SUM 金额类字段；「数 / 次数 / 量」→ COUNT；「率」→ 比率（分子分母待确认）
     - 漏斗 → 维度按单选字段的选项顺序固定排序
     - 明细表的表头 → 维度列 + 指标列
  4. 拿不准的（置信度低、比率口径、对不上字段）写进 open_questions，并在面板 notes 标「待确认」
产出是草稿：agent 用选择框和用户确认 open_questions 后，补全口径，再跑 lint_spec.py。
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_base_dashboard as ibd  # noqa: E402
import larkcli  # noqa: E402
import wireframe_lib as wl  # noqa: E402

# 常见业务同义词：标题里的说法 → 字段名里可能出现的词
SYNONYMS = {
    "签约额": ["合同金额", "签约金额", "合同额"], "签约": ["签约", "合同"], "营收": ["实付金额", "营收", "收入", "销售额", "金额"],
    "销售额": ["销售额", "实付金额", "金额"], "回款": ["回款", "已回款金额"], "商机": ["商机", "预计金额"],
    "销售": ["销售", "负责销售", "销售人员"], "客户": ["客户", "客户名称", "客户档案"], "来源": ["来源", "渠道"],
    "阶段": ["阶段", "状态"], "跟进": ["跟进", "跟进记录"], "门店": ["门店", "门店名称"], "订单": ["订单", "订单号"],
    "任务": ["任务"], "项目": ["项目"], "成员": ["成员", "负责人"], "负责人": ["负责人", "成员"],
}
MONEY = re.compile(r"额|金额|营收|收入|销售额|回款|成本|利润|GMV|gmv")
COUNT = re.compile(r"数|次数|数量|个数|量|单量|人数")
RATIO = re.compile(r"率|占比|比例")
SNAPSHOT = re.compile(r"在途|在手|当前|库存|余额|积压|存量|未完成|逾期|超期|待跟进|待处理")
LISTING = re.compile(r"清单|明细|列表|名单|台账")


def lcs(a, b):
    best = 0
    for i in range(len(a)):
        for j in range(i + 1, len(a) + 1):
            if a[i:j] in b and j - i > best:
                best = j - i
    return best


def score(term, name, glossary):
    if not term or not name:
        return 0.0
    if term == name:
        return 1.0
    s = lcs(term, name) / max(len(name), 1)
    if name in term or term in name:
        s = max(s, 0.8)
    for key, alts in list(SYNONYMS.items()) + list(glossary.items()):
        if key in term and any(a in name for a in alts):
            s = max(s, 0.85)
    return s


def load_schema(base_url):
    token = ibd.parse_base_token(base_url)
    listing = larkcli.run(["base", "+table-list", "--base-token", token])
    names = [t.get("name") for t in (listing.get("tables") or [])]
    cache = {}
    for n in names:
        ibd.table_schema(token, n, cache)
    ibd.resolve_link_targets(token, cache)
    return token, {k: v for k, v in cache.items() if not k.startswith("__")}


def best_field(term, fields, glossary, types=None):
    cands = [(score(term, n, glossary), n) for n, f in fields.items() if not types or f.get("type") in types]
    cands.sort(reverse=True)
    return cands[0] if cands and cands[0][0] > 0 else (0.0, None)


def pick_table(panel, schema, glossary):
    h = panel.get("hints", {})
    terms = [t for t in (h.get("measure"), h.get("dimension"), h.get("time_field"), panel.get("title")) if t]
    terms += h.get("columns", [])
    ranked = []
    for tname, ts in schema.items():
        s = max((score(t, tname, glossary) for t in terms), default=0) * 0.6
        s += sum(best_field(t, ts["fields"], glossary)[0] for t in terms) / max(len(terms), 1)
        ranked.append((round(s, 3), tname))
    ranked.sort(reverse=True)
    return ranked


def main_date(fields, hint, glossary, title=""):
    dates = {n: f for n, f in fields.items() if f.get("type") in ("datetime", "created_at")}
    if not dates:
        return None
    if hint:
        s, n = best_field(hint, dates, glossary)
        if n and s >= 0.5:
            return n
    if title:  # 「本周完成任务」→ 实际完成日期；「新增客户」→ 创建日期
        s, n = best_field(re.sub(r"本周|本月|今日|每日|每周|每月|任务|数|量|率", "", title), dates, glossary)
        if n and s >= 0.3:
            return n
    for prefer in ("签约日期", "下单时间", "创建日期", "日期", "时间"):
        for n in dates:
            if prefer in n:
                return n
    return next(iter(dates))


def to_panel(p, schema, glossary, questions, dominant=None):
    kind, default_chart, charts, note = wl.VISUALS.get(p["visual"], wl.VISUALS["unknown"])
    h = p.get("hints", {})
    out = {"id": p["id"], "kind": kind, "title": p["title"] or wl.VISUAL_LABEL[p["visual"]],
           "layout": p["layout"], "notes": list(p.get("notes", [])) + ([note] if note else []),
           "provenance": [{"from": "wireframe", "panel": p["id"], "visual": p["visual"],
                           "confidence": p["confidence"], "evidence": p.get("evidence", [])}]}
    if default_chart:
        out["default_chart"] = default_chart
        out["chart_types"] = charts
    if p["confidence"] < 0.7:
        questions.append("「%s」识别为%s，置信度 %.2f，请确认图表类型" % (out["title"], wl.VISUAL_LABEL[p["visual"]], p["confidence"]))
    if kind == "text":
        out["text"] = p.get("text") or out["title"]
        return out
    ranked = pick_table(p, schema, glossary)
    if dominant and ranked and ranked[0][1] != dominant and ranked[0][0] < 0.6:
        # 证据弱时，跟随同一看板上多数面板使用的主表
        ranked = [r for r in ranked if r[1] == dominant] + [r for r in ranked if r[1] != dominant]
    if ranked and ranked[0][0] < 0.35 and dominant:
        questions.append("「%s」默认用主表「%s」，对吗？" % (out["title"], dominant))
        ranked = [(0.35, dominant)]
    if not ranked or ranked[0][0] < 0.35:
        out["notes"].append("待确认：没有找到对应的数据表")
        questions.append("「%s」对应哪张表？候选：%s" % (out["title"], "、".join(t for _, t in ranked[:3])))
        out["table"] = ranked[0][1] if ranked else ""
        out["measures"] = [{"agg": "COUNT", "label": "记录数"}]
        return out
    tname = ranked[0][1]
    fields = schema[tname]["fields"]
    out["table"] = tname
    if len(ranked) > 1 and ranked[1][0] > ranked[0][0] - 0.05 and ranked[0][1] != dominant:
        questions.append("「%s」用「%s」表还是「%s」表？" % (out["title"], tname, ranked[1][1]))
    measure_term = h.get("measure") or out["title"]
    # 指标
    if RATIO.search(measure_term) and kind == "kpi":
        out["compute"] = "ratio"
        out["format"] = "percent"
        out["measures"] = [{"agg": "COUNT", "label": "分子（待确认）"}, {"agg": "COUNT", "label": "分母（待确认）"}]
        out["notes"].append("待确认：比率的分子、分母口径")
        questions.append("「%s」怎么算？分子、分母分别是什么（例如：已完成 ÷ 全部、赢单 ÷ 已结单）" % out["title"])
    elif MONEY.search(measure_term):
        s, f = best_field(measure_term, fields, glossary, types=("number", "formula"))
        if f:
            out["measures"] = [{"field": f, "agg": "SUM", "label": out["title"] if kind == "kpi" else f}]
            out["format"] = fields[f].get("format", "currency" if MONEY.search(f) else "number")
            if s < 0.6:
                questions.append("「%s」用字段「%s」求和对吗？" % (out["title"], f))
        else:
            out["measures"] = [{"agg": "COUNT", "label": "记录数"}]
            questions.append("「%s」的金额字段是哪个？" % out["title"])
    else:
        # 标题里的业务词能对上金额字段（如「签约排行」→ 合同金额）时按金额求和，否则计数
        s_money, f_money = best_field(out["title"], fields, glossary, types=("number", "formula"))
        funnel_count = p["visual"] == "funnel" and not MONEY.search(out["title"])
        if (f_money and s_money >= 0.8 and not funnel_count and not COUNT.search(measure_term)
                and fields[f_money].get("format") == "currency"):
            out["measures"] = [{"field": f_money, "agg": "SUM", "label": f_money}]
            out["format"] = "currency"
        else:
            out["measures"] = [{"agg": "COUNT", "label": measure_term if kind == "kpi" else "数量"}]
            out["format"] = "number"
    if h.get("format") and kind == "kpi" and "compute" not in out:
        out["format"] = h["format"]
    if len(h.get("series", [])) >= 2:
        questions.append("「%s」有 %d 条线（%s）：如果它们按不同日期统计（如创建日期 vs 完成日期），拆成两个趋势面板，还是只保留一条？" % (
            out["title"], len(h["series"]), "、".join(h["series"])))
    if kind == "kpi" and SNAPSHOT.search(out["title"]):
        out["snapshot"] = True
        out["subtitle"] = "当前"
        questions.append("「%s」的「%s」怎么定义：按哪些状态 / 日期筛选？" % (
            out["title"], SNAPSHOT.search(out["title"]).group(0)))
    # 维度
    dims = []
    if kind == "trend":
        d = main_date(fields, h.get("time_field"), glossary, out["title"] if len(h.get("series", [])) < 2 else "")
        if d:
            dims.append({"field": d})
            out["time_field"] = d
    elif kind in ("category", "stacked", "table"):
        terms = [h.get("dimension")] + ([h.get("dimension2")] if kind == "stacked" else [])
        if kind == "table" and h.get("columns"):
            terms = [h["columns"][0]]
        if not any(terms):
            # 没有「各 X / 按 X / X 排行」这类线索：用标题去匹配单选 / 关联字段（如「商机阶段」→ 阶段）
            s_t, f_t = best_field(out["title"], fields, glossary, types=("select", "link"))
            terms = [f_t] if f_t and s_t >= 0.6 else []
        for term in [t for t in terms if t]:
            s, f = best_field(term, fields, glossary, types=("select", "link", "text"))
            if f:
                dim = {"field": f}
                if fields[f].get("type") == "select" and fields[f].get("multiple"):
                    dim["mode"] = "enumerated"
                if p["visual"] == "funnel" and fields[f].get("options"):
                    dim["order"] = fields[f]["options"]
                    questions.append("漏斗「%s」只看进行中的阶段，还是包含已结束的阶段（%s）？" % (
                        out["title"], "、".join(fields[f]["options"][-2:])))
                dims.append(dim)
                if s < 0.6:
                    questions.append("「%s」按「%s」分组对吗？" % (out["title"], f))
        if not dims:
            sel = [n for n, f in fields.items() if f.get("type") in ("select", "link")]
            questions.append("「%s」按哪个字段分组？候选：%s" % (out["title"], "、".join(sel[:5])))
            if sel:
                dims.append({"field": sel[0]})
        if kind == "table" and h.get("columns") and (LISTING.search(out["title"]) or p["visual"] == "table"):
            matched, missing = [], []
            primary = schema[tname].get("primary")
            for c in h["columns"]:
                if primary and (c == tname or c in tname or tname in c):
                    matched.append(primary)  # 「任务」列 → 任务表主字段（任务标题）
                    continue
                sc, fc = best_field(c, fields, glossary)
                (matched if fc and sc >= 0.6 else missing).append(fc if fc and sc >= 0.6 else c)
            aggregable = any(COUNT.search(c) or MONEY.search(c) for c in h["columns"][1:])
            if LISTING.search(out["title"]) or not aggregable:
                out["columns"] = matched
                out["measures"] = []
                out["dimensions"] = []
                out["limit"] = 20
                dates = [c for c in matched if fields[c].get("type") in ("datetime", "date")]
                if dates:
                    out["sort"] = {"by": "field", "field": dates[0], "order": "asc"}
                out["notes"].append("记录清单：逐条列出 %s" % "、".join(matched))
                if missing:
                    questions.append("清单「%s」的列「%s」在表里没有对应字段：在多维表格加公式字段，还是去掉这些列？" % (
                        out["title"], "、".join(missing)))
                if SNAPSHOT.search(out["title"]):
                    questions.append("清单「%s」只列哪些记录（「%s」的筛选条件）？" % (
                        out["title"], SNAPSHOT.search(out["title"]).group(0)))
                out.setdefault("time_field", None)
                return out
        if kind == "table" and len(h.get("columns", [])) > 1:
            out["measures"] = [{"agg": "COUNT", "label": c} for c in h["columns"][1:]]
            out["notes"].append("待确认：明细表各列的口径（%s）" % "、".join(h["columns"][1:]))
            questions.append("明细表「%s」各列怎么算：%s" % (out["title"], "、".join(h["columns"][1:])))
    out["dimensions"] = dims
    if kind in ("category", "stacked", "trend") and SNAPSHOT.search(out["title"]):
        questions.append("「%s」的「%s」怎么定义：只统计哪些状态的记录？" % (out["title"], SNAPSHOT.search(out["title"]).group(0)))
    if kind == "kpi":
        d = main_date(fields, h.get("time_field"), glossary, out["title"])
        if d and not out.get("snapshot"):
            out["time_field"] = d
    if p["visual"] == "bar" and re.search(r"[Tt][Oo][Pp]\s*(\d+)|前\s*(\d+)", p["title"] + " ".join(p.get("notes", []))):
        m = re.search(r"(\d+)", re.search(r"[Tt][Oo][Pp]\s*\d+|前\s*\d+", p["title"] + " ".join(p.get("notes", []))).group(0))
        out["limit"] = int(m.group(1))
    out.setdefault("time_field", None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wireframe", default="wireframe.json")
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--glossary", help="业务同义词 JSON：{\"签约额\": [\"合同金额\"]}")
    ap.add_argument("--board-key", default="sketch")
    ap.add_argument("--board-label")
    ap.add_argument("--out", default="dashboard-spec.json")
    args = ap.parse_args()
    wf = json.load(open(args.wireframe, encoding="utf-8"))
    for p in wf["panels"]:  # 图片路线由 agent 写线框稿，可以只给 bbox，这里补齐默认字段
        p.setdefault("confidence", 0.8)
        p.setdefault("evidence", [])
        p.setdefault("hints", {})
        p.setdefault("notes", [])
        if p.get("title") and not p["hints"]:
            p["hints"] = wl.hints_from_title(p["title"])
    if any("layout" not in p for p in wf["panels"]):
        wl.assign_layout(wf)
    print(wl.render_preview(wf) + "\n")
    glossary = json.load(open(args.glossary, encoding="utf-8")) if args.glossary else {}
    token, schema = load_schema(args.base_url)
    questions = []
    tops = [pick_table(p, schema, glossary) for p in wf["panels"] if p.get("visual") != "text"]
    votes = {}
    for r in tops:
        if r and r[0][0] >= 0.5:
            votes[r[0][1]] = votes.get(r[0][1], 0) + 1
    dominant = max(votes, key=votes.get) if votes else None
    panels = [to_panel(p, schema, glossary, questions, dominant) for p in wf["panels"]]
    label = args.board_label or re.sub(r"[（(].*?[）)]", "", wf.get("title") or "").strip() or "草图看板"
    spec = {
        "version": 1,
        "title": label,
        "source": {"type": wf["source"].get("type", "wireframe"), "base_url": args.base_url, "base_token": token,
                   "wireframe": args.wireframe, **{k: v for k, v in wf["source"].items() if k != "type"}},
        "timezone": "Asia/Shanghai",
        "default_style": "sky",
        "refresh_seconds": 5,
        "boards": [{"key": args.board_key, "label": label, "group": "草图生成",
                    "description": "由%s里的看板草图生成" % ("飞书画板" if wf["source"].get("type") == "whiteboard" else "图片"),
                    "default_range": "30d", "layout": "original", "panels": panels}],
        "schema": schema,
        "open_questions": questions,
    }
    json.dump(spec, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("| 面板 | 识别为 | 表 | 指标 | 维度 / 时间 |\n|---|---|---|---|---|")
    for p in panels:
        meas = "、".join("%s(%s)" % (m.get("field") or "记录", m["agg"]) for m in p.get("measures", [])) or "—"
        dims = "、".join(d["field"] for d in p.get("dimensions", [])) or (p.get("time_field") or "—")
        if p.get("columns"):
            meas, dims = "（逐条列出）", "列：" + "、".join(p["columns"])
        print("| %s | %s | %s | %s | %s |" % (p["title"], p["kind"], p.get("table", "—"), meas, dims))
    print("\n待确认 %d 项：" % len(questions))
    for q in questions:
        print("  🟡 " + q)
    print("\n已写入 %s（草稿）。确认后跑 lint_spec.py → build_spec_bundle.py" % args.out)


if __name__ == "__main__":
    main()
