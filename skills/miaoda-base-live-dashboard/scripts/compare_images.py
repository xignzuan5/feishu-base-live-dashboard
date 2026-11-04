#!/usr/bin/env python3
"""把「输入草图 / 截图」和「生成的看板截图」左右拼成一张对照图，交付时给用户确认还原度。

用法：
    python3 compare_images.py --left whiteboard-preview.jpg --right board.png --out compare.jpg \
        [--left-label 画板草图] [--right-label 生成的看板]
依赖 Pillow；没有时生成一个并排展示的 HTML（compare.html），用 agent-browser 截图即可。
"""
import argparse
import html
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--left", required=True)
    ap.add_argument("--right", required=True)
    ap.add_argument("--out", default="compare.jpg")
    ap.add_argument("--left-label", default="输入：草图")
    ap.add_argument("--right-label", default="输出：生成的看板")
    ap.add_argument("--height", type=int, default=900, help="两张图统一缩放到的高度")
    args = ap.parse_args()
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        out = os.path.splitext(args.out)[0] + ".html"
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("<html><body style='margin:0;display:flex;gap:24px;background:#f4f6f9;font-family:sans-serif'>")
            for src, label in ((args.left, args.left_label), (args.right, args.right_label)):
                fh.write("<figure style='margin:16px'><figcaption>%s</figcaption><img src='%s' style='height:%dpx'></figure>"
                         % (html.escape(label), html.escape(os.path.abspath(src)), args.height))
            fh.write("</body></html>")
        print("未安装 Pillow，已生成 %s，用浏览器截图即可" % out)
        return
    imgs = []
    for path in (args.left, args.right):
        im = Image.open(path).convert("RGB")
        ratio = args.height / im.height
        imgs.append(im.resize((int(im.width * ratio), args.height)))
    pad, head = 32, 64
    W = sum(i.width for i in imgs) + pad * 3
    H = args.height + head + pad
    canvas = Image.new("RGB", (W, H), (244, 246, 249))
    draw = ImageDraw.Draw(canvas)
    font = None
    for cand in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"):
        if os.path.exists(cand):
            font = ImageFont.truetype(cand, 28)
            break
    x = pad
    for im, label in zip(imgs, (args.left_label, args.right_label)):
        draw.text((x, 18), label, fill=(31, 35, 41), font=font)
        canvas.paste(im, (x, head))
        draw.rectangle([x - 1, head - 1, x + im.width, head + im.height], outline=(220, 224, 230))
        x += im.width + pad
    canvas.save(args.out, quality=85)
    print("已生成对照图 %s（%dx%d）" % (args.out, W, H))


if __name__ == "__main__":
    main()
