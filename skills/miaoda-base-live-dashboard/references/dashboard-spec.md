# 看板需求说明（dashboard-spec.json）格式

一份需求说明 = 一个或多个看板 × 若干面板。**三种来源产出同一格式**：

| 来源 | 怎么产出 |
|---|---|
| 飞书会议 | 按 [requirements-from-meeting.md](requirements-from-meeting.md) 从纪要 / 逐字稿提炼，面板带 `provenance` 原话引用 |
| 多维表格原生仪表盘 | `scripts/import_base_dashboard.py` 自动迁移，面板带 `baseline` 原值快照 |
| 行业模板 / 现场问答 | `assets/specs/*.spec.json` 改改即用，或问完需求手写 |

编译与运行：`build_spec_bundle.py --pair <spec>:<同步计划>` → `server/modules/blueprint/spec.generated.ts` → 应用里 `/spec/<看板 key>` 直接可看，**不用写查询代码**。

## 顶层

```jsonc
{
  "version": 1,
  "title": "鹿野咖啡 · 经营看板",
  "source": { "type": "meeting | base-dashboard | template | manual", "base_url": "…", "base_token": "…" },
  "timezone": "Asia/Shanghai",
  "default_style": "espresso",            // 见 catalog.md「风格」
  "design_tone": "corporate",             // restrained / corporate / editorial / technical，决定推荐风格与版式
  "refresh_seconds": 5,
  "audience": ["管理层周会", "运营值守"],  // 谁看、在哪看：决定版式
  "entities": [["需求", "缺陷", "优化", "文档"]], // 实体固定配色组：同一取值在所有图里同色；维度的 order 会自动加入
  "boards": [ /* 见下 */ ],
  "schema": { /* 可选：多维表格表结构快照；迁移脚本自动写入，没有时编译脚本会现查 */ },
  "open_questions": ["“活跃客户”按 30 天还是 90 天口径？"]
}
```

## 看板

```jsonc
{
  "key": "work",                          // 路由 /spec/work，只用小写字母、数字、短横线
  "label": "工作管理",
  "description": "项目进度、任务完成与逾期、成员负载",
  "default_range": "30d",                 // today / 7d / month（本月，较上月同期）/ 30d / 90d；只对设了 time_field 的面板生效
  "layout": "executive",                  // 默认排版，见 catalog.md「排版」；用户在页面上可切换
  "panels": [ /* 见下 */ ]
}
```

## 面板

```jsonc
{
  "id": "done_rate",                      // 看板内唯一
  "kind": "kpi",                          // kpi / trend / category / stacked / table / text
  "title": "任务完成率",                   // 标题直接说清「量的是什么」
  "subtitle": "近 30 天截止的任务",         // 可选：口径说明
  "table": "任务",                         // 多维表格表名
  "measures": [
    { "agg": "COUNT", "label": "已完成", "where": [{ "field": "状态", "op": "is", "value": ["已完成"] }] },
    { "agg": "COUNT", "label": "全部" }
  ],
  "compute": "ratio",                     // 仅 kpi：取 m0 / m1
  "format": "percent",                    // currency / number / percent / decimal
  "good_when": "up",                      // 上升是好事还是坏事（逾期率填 down）
  "snapshot": false,                      // 仅 kpi：当前状态类指标（在手任务、库存、逾期总数）没有环比，标 true 并在 subtitle 写「当前」
  "dimensions": [],                       // 0~2 个；见下
  "filter": { "conjunction": "and", "conditions": [] },
  "time_field": "截止日期",                // 受看板时间范围控制；null = 全量
  "sort": { "by": "value", "order": "desc" },
  "limit": 10,
  "chart_types": ["bar", "column", "treemap"], // 用户可切换的图表类型，第一个之外用 default_chart 指定默认
  "default_chart": "bar",
  "layout": { "x": 0, "y": 0, "w": 3, "h": 2 }, // 可选：12 栅格（与多维表格仪表盘同构）；排版选「原始布局」时生效
  "text": "## 说明（仅 kind=text，Markdown）",
  "notes": ["迁移说明 / 口径说明"],
  "provenance": [{ "from": "meeting", "ref": "会议链接", "quote": "老板：逾期率要单独拎出来看" }]
}
```

### kind 与数据形状

| kind | 维度 | 指标 | 渲染组件 | 可选 chart_types |
|---|---|---|---|---|
| `kpi` | 0 | 1（`compute: ratio` 时 2） | 指标卡（带环比） | — |
| `trend` | 第 1 个是日期；可加第 2 个拆系列 | 1~N | 趋势面板 | `line` `area` `bar` |
| `category` | 1 | 1 | 构成 / 排行面板 | `bar` `column` `treemap` `donut` `segmented` |
| `stacked` | 2（分类 × 系列），或 1 维 + 多指标 | 1~N | 多系列面板 | `stacked` `grouped` `percent` |
| `table` | 0~2 | 1~N | 汇总表（可排序） | — |
| `table` + `columns` | — | — | **记录清单**：逐条列出 `columns` 里的字段，配合 `filter` / `sort: {"by": "field", "field": "计划截止"}` / `limit`（默认 20） | — |
| `text` | — | — | Markdown 说明 | — |

### 指标 measures

- `agg`：`SUM` `AVERAGE` `MAX` `MIN` `COUNT`（行数，可不写 field）`COUNT_DISTINCT`（去重计数，关联字段按关联记录去重）
- `where`：条件聚合，语法同下方筛选条件。用它做「已完成数 / 逾期数 / 赢单数」，再配 `compute: ratio` 出比率

### 维度 dimensions

- 普通字段：按值分组；**关联字段**：显示对方表主字段（如「门店」显示门店名称）
- **多选字段**：`mode: enumerated` 每个选项各计一次
- **日期字段**：今日按小时，7 天 / 30 天按天
- `order: ["线索", "需求确认", "方案报价", "商务谈判", "赢单"]`：固定顺序（漏斗、优先级、阶段）

### 筛选 filter / where 条件

`{ "field": "状态", "op": "isNot", "value": ["已完成"] }`

| op | 说明 |
|---|---|
| `is` `isNot` | 等于 / 不等于；单选、文本传数组或字符串；复选框传 true/false |
| `contains` `doesNotContain` | 文本模糊匹配；多选字段为「包含任一」 |
| `isEmpty` `isNotEmpty` | 为空 / 不为空（关联、多选也适用） |
| `isGreater` `isGreaterEqual` `isLess` `isLessEqual` | 数字或日期比较 |

日期取值：`{"relative": "today"}`、`{"relative": "now"}`、`{"relative": "-7d"}`、`{"relative": "+3d"}`（按业务时区自然日）；或 `{"exact_date_ms": 1793000000000}`。

字段对字段（同一张表）：`{"field": "实际完成日期", "op": "isLessEqual", "value": {"field": "计划截止"}}`，支持 `is` `isNot` `isGreater` `isGreaterEqual` `isLess` `isLessEqual`。

例：**逾期任务** = `截止日期 isLess today` 且 `状态 isNot 已完成`；**按期完成** = `状态 is 已完成` 且 `实际完成日期 isLessEqual {field: 计划截止}`。

### 比率与两个维度

- `compute: "ratio"`：指标卡取 m0 ÷ m1；**构成 / 多系列面板也可用**，每一行各自取 m0 ÷ m1（如各类型「实际 ÷ 预估工时」），此时 `format` 设 `percent` 或 `decimal`
- 两个维度时：系列（第二维度）按 `dimensions[1].order` 固定顺序，没给就按合计降序；`limit` 取的是**第一维度按合计的 Top N**（不是组合对）
- 维度可以按**关联表的字段**分组：`{"field": "客户", "via": "行业"}`（商机按客户行业）；筛选条件仍只能用本表字段
- 时间范围：`today` / `7d` / `month`（本月 1 日至今，对比上月同期）/ `30d` / `90d`。会上说「本月」「这个月」就用 `month`，不要拿 `30d` 代替

## 设计约束（`scripts/lint_spec.py` 会检查）

- 每个看板 **4~9 个指标卡**之外再放 **3~8 个图表面板**；总面板 ≤ 14
- 指标卡要有参照：有日期字段就设 `time_field`（出环比），比率类写清 `good_when`
- `donut` 只用于 ≤ 5 个分类；分类超过 6 个的面板默认 `bar`
- 同一看板的 `time_field` 口径一致；标题不重复；不允许空看板
- 量级差很大的指标不放在同一面板（不做双 Y 轴）
