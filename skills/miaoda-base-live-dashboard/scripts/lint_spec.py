#!/usr/bin/env python3
"""看板需求说明的设计检查（把「专业、不像 AI 生成」的规范变成可机检的规则）。

用法：python3 lint_spec.py dashboard-spec.json [更多 spec ...]
🔴 错误必须修（退出码 1）；🟡 建议按规范调整；迁移来的看板为保持原样可以保留 🟡。

规则来源：Stephen Few《信息仪表盘设计》、IBM Carbon 数据可视化、PatternFly 看板规范、
Power BI 看板设计指南、阿里 DataV 大屏规范，以及本 skill 的 dataviz 配色规则。
"""
import json
import re
import sys

KIND_CHARTS = {
    "trend": {"line", "area", "bar"},
    "category": {"bar", "column", "treemap", "donut", "segmented"},
    "stacked": {"stacked", "grouped", "percent"},
}
BAD_UP_WORDS = ("逾期", "超期", "退款", "流失", "投诉", "取消", "缺陷", "延期", "未回款", "输单", "让利", "成本")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def lint(spec, path):
    errs, warns = [], []
    E = lambda b, p, m: errs.append("[%s%s] %s" % (b, "/" + p if p else "", m))  # noqa: E731
    W = lambda b, p, m: warns.append("[%s%s] %s" % (b, "/" + p if p else "", m))  # noqa: E731
    keys = set()
    for b in spec.get("boards", []):
        bk = b.get("key", "?")
        if not re.match(r"^[a-z0-9-]+$", bk):
            E(bk, "", "看板 key 只能用小写字母、数字、短横线（会进 URL）")
        if bk in keys:
            E(bk, "", "看板 key 重复")
        keys.add(bk)
        panels = b.get("panels", [])
        migrated = (spec.get("source") or {}).get("type") == "base-dashboard"
        kpis = [p for p in panels if p.get("kind") == "kpi"]
        charts = [p for p in panels if p.get("kind") not in ("kpi", "text")]
        if not panels:
            E(bk, "", "空看板")
        if not migrated:
            if not 3 <= len(kpis) <= 9:
                W(bk, "", "指标卡 %d 个：建议 4~9 个，每个都要能支撑一个决策" % len(kpis))
            if not 3 <= len(charts) <= 8:
                W(bk, "", "图表面板 %d 个：建议 3~8 个，超过就拆成两个看板" % len(charts))
        if len(panels) > 14:
            W(bk, "", "面板 %d 个，一屏放不下，管理层看板应一屏讲完" % len(panels))
        ids, titles = set(), set()
        time_fields = set()
        for p in panels:
            pid, title, kind = str(p.get("id", "?")), p.get("title", ""), p.get("kind")
            if pid in ids:
                E(bk, pid, "面板 id 重复")
            ids.add(pid)
            if title in titles:
                E(bk, pid, "面板标题重复：%s" % title)
            titles.add(title)
            if kind not in ("kpi", "trend", "category", "stacked", "table", "text"):
                E(bk, pid, "未知 kind：%s" % kind)
                continue
            if " · " in title or "—" in title:
                W(bk, pid, "标题里有「 · 」或破折号拼接，像模板文案；直接写清量的是什么")
            if EMOJI.search(title):
                W(bk, pid, "标题里有 emoji，看板标题不用 emoji")
            if len(title) > 16:
                W(bk, pid, "标题 %d 字偏长，口径说明放 subtitle" % len(title))
            if kind == "text":
                continue
            if not p.get("table"):
                E(bk, pid, "缺少 table")
            measures = p.get("measures") or []
            if kind == "table" and p.get("columns"):
                continue  # 记录清单：逐条列字段，不做聚合检查
            dims = p.get("dimensions") or []
            for m in measures:
                if (m.get("agg") or "").upper() not in ("SUM", "AVERAGE", "MAX", "MIN", "COUNT", "COUNT_DISTINCT"):
                    E(bk, pid, "不支持的聚合：%s" % m.get("agg"))
                if (m.get("agg") or "").upper() not in ("COUNT",) and not m.get("field"):
                    E(bk, pid, "%s 聚合需要 field" % m.get("agg"))
            if kind == "kpi":
                if p.get("compute") == "ratio":
                    if len(measures) != 2:
                        E(bk, pid, "ratio 指标卡需要恰好 2 个指标（分子、分母）")
                    if p.get("format") not in ("percent", "decimal"):
                        W(bk, pid, "比率类指标建议 format=percent（人均类用 decimal）")
                elif len(measures) != 1:
                    E(bk, pid, "指标卡只能有 1 个指标（比率用 compute: ratio）")
                if dims:
                    E(bk, pid, "指标卡不能有维度")
                if not p.get("time_field") and not migrated and not p.get("snapshot"):
                    W(bk, pid, "指标卡没有 time_field，无法显示环比；当前状态类指标（在手、逾期、库存）请标 snapshot: true 并在 subtitle 写明「当前」")
            if kind == "category" and len(dims) != 1:
                E(bk, pid, "category 面板需要恰好 1 个维度")
            if kind == "stacked" and not (len(dims) == 2 or (len(dims) == 1 and len(measures) >= 2)):
                E(bk, pid, "stacked 面板需要 2 个维度，或 1 个维度 + 多个指标")
            if kind == "trend" and not dims:
                E(bk, pid, "trend 面板第 1 个维度应是日期字段")
            allowed = KIND_CHARTS.get(kind)
            if allowed:
                bad = [c for c in (p.get("chart_types") or []) if c not in allowed]
                if bad:
                    E(bk, pid, "%s 面板不支持图表类型 %s" % (kind, bad))
                if p.get("default_chart") and p["default_chart"] not in allowed:
                    E(bk, pid, "default_chart=%s 不适用于 %s" % (p["default_chart"], kind))
            if kind == "category" and p.get("default_chart") == "donut" and (p.get("limit") or 99) > 5 and not dims[0].get("order") if dims else False:
                W(bk, pid, "环形图默认展示：分类可能超过 5 个，建议默认 bar，donut 留作可切换")
            if kind == "kpi" and any(w in title for w in BAD_UP_WORDS) and p.get("good_when", "up") != "down":
                W(bk, pid, "「%s」是越少越好的指标，设 good_when: down，否则上涨会显示成绿色" % title)
            if p.get("time_field"):
                time_fields.add((p.get("table"), p["time_field"]))
            lay = p.get("layout")
            if lay:
                if lay.get("w", 1) < 1 or lay.get("x", 0) + lay.get("w", 1) > 12:
                    E(bk, pid, "layout 超出 12 栅格：%s" % lay)
            if kind == "trend" and len(measures) > 2:
                W(bk, pid, "趋势面板 %d 个指标：量级不同的指标别画在同一轴上，拆面板" % len(measures))
        tables = {}
        for t, f in time_fields:
            tables.setdefault(t, set()).add(f)
        for t, fs in tables.items():
            if len(fs) > 1:
                W(bk, "", "表「%s」用了多个时间口径 %s：确认用户理解每个面板按哪个日期统计（写在 subtitle）" % (t, sorted(fs)))
    return errs, warns


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    total_err = 0
    for path in sys.argv[1:]:
        spec = json.load(open(path, encoding="utf-8"))
        errs, warns = lint(spec, path)
        total_err += len(errs)
        print("== %s：🔴 %d · 🟡 %d" % (path, len(errs), len(warns)))
        for e in errs:
            print("  🔴 " + e)
        for w in warns:
            print("  🟡 " + w)
    sys.exit(1 if total_err else 0)


if __name__ == "__main__":
    main()
