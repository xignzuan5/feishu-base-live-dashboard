"""线框稿（wireframe.json）的公共逻辑：图表类型识别、12 栅格换算、ASCII 线框预览、类型 → 面板映射。

wireframe.json 是画板 / 图片 / 截图等「画出来的看板」的统一中间格式：
{
  "version": 1,
  "source": {"type": "whiteboard | image", ...},
  "title": "销售作战室",
  "canvas": {"x": 0, "y": 0, "w": 1200, "h": 820},          # 画面坐标系
  "panels": [{
    "id": "w1",
    "title": "每日签约额趋势",
    "visual": "line",               # 识别出的图表类型，见 VISUALS
    "confidence": 0.9,              # 0~1；< 0.7 的会在确认环节单独问
    "evidence": ["标题含「趋势」", "有折线 + 坐标轴"],
    "bbox": {"x": 40, "y": 210, "w": 740, "h": 280},
    "layout": {"x": 0, "y": 2, "w": 7, "h": 4},   # 12 栅格（与多维表格仪表盘同构）
    "hints": {"time_field": "签约日期", "dimension": "销售", "measure": "签约额",
              "format": "currency", "columns": ["销售", "跟进次数"], "value": "¥1,234 万"},
    "notes": ["原标题：每日签约额趋势（折线，按签约日期）"]
  }]
}
"""
import re

# 识别词表：visual → 面板 kind / 默认图表 / 可切换图表 / 说明
VISUALS = {
    "kpi": ("kpi", None, [], ""),
    "line": ("trend", "line", ["line", "area", "bar"], ""),
    "area": ("trend", "area", ["area", "line", "bar"], ""),
    "column": ("category", "column", ["column", "bar", "treemap"], ""),
    "bar": ("category", "bar", ["bar", "column", "treemap"], ""),
    "donut": ("category", "donut", ["donut", "segmented", "bar", "treemap"], ""),
    "pie": ("category", "donut", ["donut", "segmented", "bar", "treemap"], "饼图统一为环形图"),
    "funnel": ("category", "bar", ["bar", "column"], "漏斗以固定阶段顺序的条形图呈现"),
    "table": ("table", None, [], ""),
    "stacked": ("stacked", "stacked", ["stacked", "grouped", "percent"], ""),
    "heatmap": ("stacked", "stacked", ["stacked", "grouped"], "热力图在配置看板里以堆叠图呈现；需要热力图时走精排路线"),
    "scatter": ("category", "column", ["column", "bar"], "散点图在配置看板里以柱状呈现；需要散点时走精排路线"),
    "meter": ("kpi", None, [], "目标达成以比率指标卡呈现（compute: ratio）"),
    "map": ("category", "bar", ["bar", "column", "treemap"], "地图以按地区的条形图呈现"),
    "text": ("text", None, [], ""),
    "unknown": ("category", "bar", ["bar", "column"], "未识别出图表类型，默认条形图，请确认"),
}

VISUAL_LABEL = {
    "kpi": "指标卡", "line": "折线趋势", "area": "面积趋势", "column": "柱状", "bar": "条形 / 排行",
    "donut": "环形占比", "pie": "饼图占比", "funnel": "漏斗", "table": "明细表", "stacked": "堆叠",
    "heatmap": "热力图", "scatter": "散点", "meter": "进度 / 达成", "map": "地图", "text": "文字说明",
    "unknown": "未识别",
}

# 标题关键词（按优先级）
KEYWORDS = [
    ("funnel", r"漏斗|转化率?链|转化路径"),
    ("table", r"明细|清单|列表|表格|台账|名单"),
    ("heatmap", r"热力|热度图"),
    ("scatter", r"散点|气泡|相关性"),
    ("map", r"地图"),
    ("meter", r"仪表|达成|完成度|进度"),
    ("donut", r"占比|构成|饼|环形|比例|结构"),
    ("bar", r"排行|排名|[Tt][Oo][Pp]\s*\d*|前\s*\d+|榜"),
    ("area", r"面积"),
    ("line", r"趋势|走势|折线|曲线|变化|每日|每周|每月|按日|按周|按月|逐日"),
    ("column", r"柱状|柱图|对比"),
    ("stacked", r"堆叠|×|x\s"),
]
CHART_WORDS = r"[（(][^）)]*[）)]|折线图?|柱状图?|条形图?|饼图|环形图?|面积图?|漏斗图?|热力图|散点图|趋势图"
NUMERIC = re.compile(r"^[¥$￥]?\s*[\d,.]+\s*(%|万|亿|千|元|单|人|个|次|件)?\s*(万|亿)?$")


def clean_title(raw):
    t = re.sub(CHART_WORDS, "", raw).strip(" ：:·-—_")
    return t or raw


def hints_from_title(raw):
    h = {}
    m = re.search(r"按\s*([^\s，,、）)]*?(?:日期|时间|时段|月份|周))", raw)
    if m:
        h["time_field"] = m.group(1)
    t = clean_title(raw)
    for pat in (r"各(.+?)的", r"按(.+?)(?:统计|分布|排行|排名|汇总)", r"^(.+?)(?:排行|排名|榜)",
                r"^(.+?)(?:占比|构成|分布|结构)", r"^(.+?)\s*[×x]\s*(.+)$"):
        m = re.search(pat, t)
        if m:
            h["dimension"] = m.group(1).strip()
            if m.lastindex and m.lastindex >= 2:
                h["dimension2"] = m.group(2).strip()
            break
    meas = re.sub(r"各|按|的|排行|排名|榜|占比|构成|分布|结构|趋势|走势|每日|每周|每月|[Tt][Oo][Pp]\s*\d*", " ", t)
    if h.get("dimension"):
        meas = meas.replace(h["dimension"], " ")
    meas = re.sub(r"\s+", " ", meas).strip()
    if meas:
        h["measure"] = meas.split(" ")[-1]
    return h


def format_from_value(v):
    if not v:
        return None
    if "%" in v:
        return "percent"
    if any(c in v for c in "¥￥$元"):
        return "currency"
    return "number"


def classify(f):
    """f：whiteboard_to_wireframe.features() 的结果；图片路线由 agent 直接填 visual。"""
    texts = f["texts"]
    pg = f["geo"]
    title_raw = ""
    big_values = [t for t in texts if t[1] >= 24 and NUMERIC.match(t[0].replace(" ", ""))]
    labels = [t for t in texts if t not in big_values]
    if labels:
        top = [t for t in labels if t[2][1] <= pg[1] + max(60, pg[3] * 0.3)]
        title_raw = max(top or labels, key=lambda t: (t[1], -t[2][1]))[0]
    evidence, kw = [], None
    for vis, pat in KEYWORDS:
        if title_raw and re.search(pat, title_raw):
            kw = vis
            evidence.append("标题含「%s」" % re.search(pat, title_raw).group(0))
            break
    mark = None
    rects = f["rects"]
    if big_values:
        mark = "kpi"
        evidence.append("有大号数字「%s」" % big_values[0][0])
    elif f["polylines"]:
        mark = "line"
        evidence.append("有折线%s" % ("和坐标轴" if f["h_lines"] or f["v_lines"] else ""))
    elif len(f["polygons"]) >= 2 and sorted(f["polygons"], key=lambda g: g[1]) == sorted(f["polygons"], key=lambda g: -g[2]):
        mark = "funnel"
        evidence.append("有 %d 层上宽下窄的梯形" % len(f["polygons"]))
    elif f["circles"] >= 8:
        mark = "scatter"
        evidence.append("有 %d 个散点" % f["circles"])
    elif f["circles"]:
        mark = "donut"
        evidence.append("有圆 / 圆环")
    elif len(rects) >= 12 and len({(round(r[2]), round(r[3])) for r in rects}) <= 3:
        mark = "heatmap"
        evidence.append("有 %d 个等大小方格" % len(rects))
    elif len(rects) >= 3:
        lefts = {round(r[0] / 4) for r in rects}
        bottoms = {round((r[1] + r[3]) / 4) for r in rects}
        if len(lefts) == 1 and len({round(r[2]) for r in rects}) > 1:
            mark = "bar"
            evidence.append("有 %d 根左对齐、长短不一的横条" % len(rects))
        elif len(bottoms) == 1 and len({round(r[3]) for r in rects}) > 1:
            mark = "column"
            evidence.append("有 %d 根底对齐、高低不一的柱子" % len(rects))
    elif len(f["h_lines"]) >= 3 and f["v_lines"]:
        mark = "table"
        evidence.append("有 %d×%d 的表格网格" % (len(f["h_lines"]) + 1, len(f["v_lines"]) + 1))
    # 合并两路证据
    if mark and kw and mark != kw:
        if kw in ("table", "funnel", "heatmap") or (kw == "line" and mark == "column"):
            visual = "column" if (kw == "line" and mark == "column") else kw
        else:
            visual = mark
        confidence = 0.7
        evidence.append("标题与图形不一致，按「%s」处理" % VISUAL_LABEL[visual])
    elif mark or kw:
        visual = mark or kw
        confidence = 0.92 if (mark and kw) else (0.8 if mark else 0.65)
    else:
        visual, confidence = ("text", 0.6) if labels and len(" ".join(t[0] for t in labels)) > 30 else ("unknown", 0.3)
    hints = hints_from_title(title_raw) if title_raw else {}
    if big_values:
        hints["value"] = big_values[0][0]
        hints["format"] = format_from_value(big_values[0][0])
        if not hints.get("measure"):
            hints["measure"] = clean_title(title_raw)
    if visual == "table":
        header_y = min((t[2][1] for t in labels if t[0] != title_raw), default=None)
        if header_y is not None:
            hints["columns"] = [t[0] for t in sorted(labels, key=lambda t: t[2][0])
                                if t[0] != title_raw and abs(t[2][1] - header_y) < 12]
    notes = []
    if title_raw and clean_title(title_raw) != title_raw:
        notes.append("原标题：%s" % title_raw)
    return {
        "title": clean_title(title_raw) if title_raw else "",
        "visual": visual,
        "confidence": round(confidence, 2),
        "evidence": evidence,
        "hints": hints,
        "notes": notes,
    }


def assign_layout(wf, page_px=1500.0, row_px=104.0, row_pad=84.0):
    """画面坐标 → 12 栅格（x/w 按宽度比例；y/h 按目标页面像素换算成行）。"""
    c = wf["canvas"]
    W = c["w"] or 1.0
    scale = page_px / W
    for p in wf["panels"]:
        b = p["bbox"]
        x = int(round((b["x"] - c["x"]) / W * 12))
        w = max(1, int(round(b["w"] / W * 12)))
        if x + w > 12:
            w = 12 - x
        y = int(round((b["y"] - c["y"]) * scale / row_px))
        h = max(1, int(round((b["h"] * scale + row_pad) / row_px)))
        if p["visual"] == "kpi":
            h = max(h, 2)
        p["layout"] = {"x": max(0, x), "y": y, "w": max(1, w), "h": h}
    return wf


def render_preview(wf, cols=12, cell=6):
    """ASCII 线框 + 识别结果表，用于和用户确认。"""
    panels = wf["panels"]
    if not panels:
        return "（没有面板）"
    rows = max(p["layout"]["y"] + p["layout"]["h"] for p in panels)
    width = cols * cell + 1
    grid = [[" "] * width for _ in range(rows * 2 + 1)]
    for p in panels:
        L = p["layout"]
        x0, x1 = L["x"] * cell, (L["x"] + L["w"]) * cell
        y0, y1 = L["y"] * 2, (L["y"] + L["h"]) * 2
        for x in range(x0, x1 + 1):
            for y in (y0, y1):
                if 0 <= y < len(grid) and 0 <= x < width:
                    grid[y][x] = "─" if grid[y][x] in " ─" else "┼"
        for y in range(y0, y1 + 1):
            for x in (x0, x1):
                if 0 <= y < len(grid) and 0 <= x < width:
                    grid[y][x] = "│" if grid[y][x] in " │" else "┼"
        label = "%s %s" % (p["id"], VISUAL_LABEL.get(p["visual"], p["visual"]))
        ly = y0 + 1
        for i, ch in enumerate(label[: max(0, (x1 - x0 - 2) // 2)]):
            if ly < len(grid) and x0 + 2 + i * 2 < width:
                grid[ly][x0 + 2 + i * 2] = ch
                if x0 + 3 + i * 2 < width and ord(ch) < 128:
                    grid[ly][x0 + 3 + i * 2] = ""
    art = "\n".join("".join(r).rstrip() for r in grid)
    lines = ["%s（%d 个面板）" % (wf.get("title") or "线框稿", len(panels)), art, "",
             "| 面板 | 标题 | 识别为 | 置信度 | 依据 | 栅格 x,y,w,h |", "|---|---|---|---|---|---|"]
    for p in panels:
        L = p["layout"]
        flag = "🟢" if p["confidence"] >= 0.85 else ("🟡" if p["confidence"] >= 0.65 else "🔴")
        lines.append("| %s | %s | %s | %s %.2f | %s | %d,%d,%d,%d |" % (
            p["id"], p["title"] or "（无标题）", VISUAL_LABEL.get(p["visual"], p["visual"]), flag,
            p["confidence"], "；".join(p["evidence"]) or "—", L["x"], L["y"], L["w"], L["h"]))
    return "\n".join(lines)
