# 不同页面怎么抓

## 1. 静态页面里的表格 / 列表（最常见）

`scrape_page.py` 直接处理：`<table>`（含多级表头、合并单元格、维基百科脚注清理）、JSON-LD 结构化数据、重复列表项。

## 2. 前端渲染页面（HTML 里几乎没有正文）

用浏览器打开后，在页面里取数据。示例用 `agent-browser`（本机没有时，可用 Playwright 等）：

```bash
agent-browser open "<网址>"
agent-browser wait 3000
# 把页面里的第一张表转成 rows.json 需要的结构
agent-browser eval "JSON.stringify((() => {
  const t = document.querySelector('table');
  const head = [...t.querySelectorAll('thead th, tr:first-child th')].map(x => x.innerText.trim());
  const rows = [...t.querySelectorAll('tbody tr')].map(tr =>
    Object.fromEntries([...tr.children].map((td, i) => [head[i] || ('列' + (i + 1)), td.innerText.trim()])));
  return { source_url: location.href, fetched_at: new Date().toISOString(), columns: head, rows };
})())" > rows.json
```

卡片列表把 `table` / `tr` 换成卡片的选择器即可。拿到 `rows.json` 后从流程 ④ 继续。

## 3. 页面背后有数据接口

在浏览器开发者工具的「网络」面板里，如果能看到返回 JSON 的公开接口（不带登录凭证），直接请求接口通常比解析页面稳定。仍然要遵守 robots.txt、网站条款和请求频率；接口需要登录凭证的不要用。

## 4. 翻页 / 加载更多

- 网址里有页码（`?page=2`）：逐页跑 `scrape_page.py --pick`，合并成一个 `rows.json`；页与页之间保持 ≥ 2 秒间隔，先问用户要抓几页
- 需要点「加载更多」：浏览器路线里循环点击，每次等待 2 秒，设置上限（例如最多 20 次）

## 定期更新

把两条命令写进一个脚本：

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 $SKILL/scripts/scrape_page.py --url "<网址>" --pick t1 --drop-rows "合计|总计" --out rows.json --refresh
python3 $SKILL/scripts/rows_to_base.py --rows rows.json --key <主键列> --base-url <多维表格链接> --table <表名>
```

按频率选一种运行方式：

| 方式 | 适合 |
|---|---|
| 本机 / 服务器定时任务（cron、launchd） | 最简单；电脑要开着 |
| Claude Code 的定时任务（`/schedule` 或 `/loop`） | 已经在用 Claude Code；可以顺便检查页面结构有没有变 |
| 妙搭应用的定时触发器（`lark-cli apps +automation-*`） | 已经有妙搭应用（比如看板应用），想在云端跑 |

页面结构变化（数据块对不上、列名变了、行数骤减）时，脚本会因为找不到数据块或主键列报错退出，不会写入错误数据；把报错告诉用户，重新走 ③ 识别数据块。
