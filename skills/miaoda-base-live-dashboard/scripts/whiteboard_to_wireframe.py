#!/usr/bin/env python3
"""飞书画板里的看板草图 → 线框稿 wireframe.json（面板位置、识别出的图表类型、标题、证据、置信度）。

用法：
    python3 whiteboard_to_wireframe.py --whiteboard-token <画板 token> [--out wireframe.json]
    python3 whiteboard_to_wireframe.py --nodes nodes.json            # 已导出的原生节点
画板 token：文档里画板块的 block_token（`docs +fetch` 可见），或画板链接里的 token。

识别方法（两路证据，一致则高置信）：
  1. 标题关键词：趋势 / 排行 / 占比 / 漏斗 / 明细 / 指标……
  2. 图形特征：大号数字 → 指标卡；折线 + 坐标轴 → 趋势；左对齐的长短条 → 条形；底对齐 → 柱状；
     圆 / 圆环 → 占比；上宽下窄的梯形 → 漏斗；横竖线网格 → 明细表；成片小方格 → 热力；散点 → 散点
同时导出预览图（--preview），供视觉复核或做「草图 vs 成品」对照。
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wireframe_lib as wl  # noqa: E402


def export(token, kind, out):
    cmd = ["lark-cli", "whiteboard", "+export", "--whiteboard-token", token, "--output-type", kind,
           "--output", out, "--overwrite", "--as", "user"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit("导出画板失败：%s" % (proc.stdout or proc.stderr)[:400])
    m = re.search(r'"output_path":\s*"([^"]+)"', proc.stdout)
    path = m.group(1) if m else out
    if not os.path.exists(path):  # 预览图的扩展名由接口返回的 Content-Type 决定
        base = os.path.basename(out)
        hits = [f for f in os.listdir(os.path.dirname(out) or ".") if f.startswith(base + ".")]
        if hits:
            path = os.path.join(os.path.dirname(out), hits[0])
    return path


def geo(n):
    return (float(n.get("x") or 0), float(n.get("y") or 0), float(n.get("width") or 0), float(n.get("height") or 0))


def inside(inner, outer, slack=2.0):
    x, y, w, h = inner
    X, Y, W, H = outer
    cx, cy = x + w / 2, y + h / 2
    return X - slack <= cx <= X + W + slack and Y - slack <= cy <= Y + H + slack


def area(g):
    return g[2] * g[3]


def node_kind(n):
    t = n.get("type")
    if t == "text_shape":
        return "text"
    if t == "connector":
        shape = (n.get("connector") or {}).get("shape", "")
        return "polyline" if shape not in ("straight",) else "line"
    if t == "image":
        svg = str((n.get("image") or {}).get("token", ""))
        if "<circle" in svg or "<ellipse" in svg:
            return "circle"
        if "<polygon" in svg:
            return "polygon"
        if "<polyline" in svg or "<path" in svg:
            return "polyline"
        return "image"
    if t == "composite_shape":
        sub = (n.get("composite_shape") or {}).get("type", "")
        if sub in ("ellipse", "circle"):
            return "circle"
        if sub in ("trapezoid", "triangle", "flowchart_manual_operation"):
            return "polygon"
        return "rect"
    if t in ("sticky_note", "section", "frame"):
        return "rect"
    return t or "other"


def text_of(n):
    return ((n.get("text") or {}).get("text") or "").strip()


def font_of(n):
    try:
        return float((n.get("text") or {}).get("font_size") or 14)
    except (TypeError, ValueError):
        return 14.0


def find_panels(nodes):
    """面板 = 带边框、面积够大、本身不被别的候选面板包含的形状（去掉铺满全画布的背景）。"""
    shapes = [n for n in nodes if node_kind(n) == "rect"]
    if not shapes:
        return [], (0, 0, 1, 1)
    xs = [geo(n)[0] for n in nodes] + [geo(n)[0] + geo(n)[2] for n in nodes]
    ys = [geo(n)[1] for n in nodes] + [geo(n)[1] + geo(n)[3] for n in nodes]
    canvas = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    big = [n for n in shapes if area(geo(n)) >= 0.012 * area(canvas) and area(geo(n)) < 0.85 * area(canvas)]
    panels = [n for n in big if not any(o is not n and area(geo(o)) > area(geo(n)) and inside(geo(n), geo(o))
                                       for o in big)]
    if not panels:
        return [], canvas
    px = [geo(n)[0] for n in panels] + [geo(n)[0] + geo(n)[2] for n in panels]
    py = [geo(n)[1] for n in panels] + [geo(n)[1] + geo(n)[3] for n in panels]
    return panels, (min(px), min(py), max(px) - min(px), max(py) - min(py))


def features(panel, nodes):
    pg = geo(panel)
    members = [n for n in nodes if n is not panel and inside(geo(n), pg) and area(geo(n)) < area(pg)]
    texts = [n for n in members if node_kind(n) == "text"]
    own = text_of(panel)
    if own:
        texts.append({"text": {"text": own, "font_size": font_of(panel)}, "x": pg[0], "y": pg[1], "width": pg[2], "height": 20})
    texts.sort(key=lambda n: (geo(n)[1], geo(n)[0]))
    marks = [n for n in members if node_kind(n) != "text"]
    rects = [geo(n) for n in marks if node_kind(n) == "rect"]
    lines = [geo(n) for n in marks if node_kind(n) == "line"]
    return {
        "texts": [(text_of(n), font_of(n), geo(n)) for n in texts if text_of(n)],
        "polylines": sum(1 for n in marks if node_kind(n) == "polyline"),
        "circles": sum(1 for n in marks if node_kind(n) == "circle"),
        "polygons": [geo(n) for n in marks if node_kind(n) == "polygon"],
        "rects": rects,
        "h_lines": [g for g in lines if g[3] < 2 and g[2] > 0.3 * pg[2]],
        "v_lines": [g for g in lines if g[2] < 2 and g[3] > 0.2 * pg[3]],
        "geo": pg,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--whiteboard-token")
    ap.add_argument("--nodes", help="已导出的原生节点 JSON（+export --output-type raw）")
    ap.add_argument("--out", default="wireframe.json")
    ap.add_argument("--preview", default="whiteboard-preview", help="同时导出的预览图路径（不含扩展名）")
    args = ap.parse_args()
    if not args.nodes and not args.whiteboard_token:
        sys.exit("需要 --whiteboard-token 或 --nodes")
    nodes_path = args.nodes or export(args.whiteboard_token, "raw", "whiteboard-nodes.json")
    preview = None
    if args.whiteboard_token:
        preview = export(args.whiteboard_token, "preview", args.preview)
    data = json.load(open(nodes_path, encoding="utf-8"))
    nodes = data.get("nodes", data) if isinstance(data, dict) else data
    panels, canvas = find_panels(nodes)
    if not panels:
        sys.exit("没有识别到面板：画板里的看板草图需要用矩形（或便签、分区）框出每个面板")
    title_text = max((n for n in nodes if node_kind(n) == "text" and not any(inside(geo(n), geo(p)) for p in panels)),
                     key=font_of, default=None)
    out_panels = []
    for i, p in enumerate(sorted(panels, key=lambda n: (round(geo(n)[1] / 20), geo(n)[0])), 1):
        f = features(p, nodes)
        rec = wl.classify(f)
        rec["id"] = "w%d" % i
        rec["bbox"] = dict(zip(("x", "y", "w", "h"), [round(v, 1) for v in f["geo"]]))
        out_panels.append(rec)
    wf = {
        "version": 1,
        "source": {"type": "whiteboard", "whiteboard_token": args.whiteboard_token, "preview": preview},
        "title": text_of(title_text) if title_text else "",
        "canvas": dict(zip(("x", "y", "w", "h"), [round(v, 1) for v in canvas])),
        "panels": out_panels,
    }
    wl.assign_layout(wf)
    json.dump(wf, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(wl.render_preview(wf))
    print("\n已写入 %s%s" % (args.out, "；预览图 %s" % preview if preview else ""))


if __name__ == "__main__":
    main()
