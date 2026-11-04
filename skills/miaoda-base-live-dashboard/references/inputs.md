# 四种输入 → 一份需求说明

用户可能拿着不同的东西来：一场需求会、一个现成的多维表格仪表盘、一块画了样子的飞书画板，或者一张图片（手绘拍照、别家 BI 截图、设计稿）。四种输入都收敛到 `dashboard-spec.json`，后面的同步、编译、发布流程完全一样。

| 输入 | 识别什么 | 走哪条路 | 产出 |
|---|---|---|---|
| 飞书会议（纪要 / 逐字稿） | 受众、决策、指标口径、预警、风格偏好 | [requirements-from-meeting.md](requirements-from-meeting.md)，agent 提炼 | spec（带原话溯源） |
| 多维表格原生仪表盘 | 组件类型、表、指标、维度、筛选、布局 | `import_base_dashboard.py`（确定性） | spec + 原值快照 + 迁移报告 |
| 飞书画板 | 每个框的位置、标题、图形特征 | `whiteboard_to_wireframe.py`（确定性）→ `wireframe_to_spec.py` | wireframe → spec 草稿 + 待确认 |
| 图片 | 同上，靠视觉识别 | agent 读图写 `wireframe.json`（按下方规则）→ `wireframe_to_spec.py` | wireframe → spec 草稿 + 待确认 |

> 画板优先读**原生节点**（`+export --output-type raw`）：坐标、文字、形状都是精确值，比看图准。画板里贴的是图片（拍照、截图）时，再走图片路线。

## 画板 / 图片的统一流程

```
输入 ──识别──► wireframe.json ──对字段──► spec 草稿 ──确认──► spec ──lint──► 编译 ──截图──► 对照图
         （类型、位置、标题、证据）  （表、指标、维度、时间）  （选择框）                       （草图 vs 成品）
```

```bash
# 画板：token 是文档里画板块的 block_token，或画板链接里的 token
python3 $SKILL/scripts/whiteboard_to_wireframe.py --whiteboard-token <token> --out wireframe.json
# 图片：agent 读图后按规则写 wireframe.json（可只给 bbox，栅格坐标会自动换算）
# 两者之后相同：
python3 $SKILL/scripts/wireframe_to_spec.py --wireframe wireframe.json --base-url <多维表格链接> --out dashboard-spec.json
```

## 识别规则（画板脚本内置；图片路线由 agent 照此判断）

两路证据：**标题关键词** + **图形特征**。两路一致置信度 ≥ 0.9；只有图形 0.8；只有标题 0.65；冲突时按下表的优先项处理，并降到 0.7、写明原因。

| 识别为 | 图形特征 | 标题关键词 | 生成的面板 |
|---|---|---|---|
| 指标卡 kpi | 框里有大号数字（字号 ≥ 24，含 ¥、%、万） | 总数、总额、……率 | 指标卡；`¥` → 金额，`%` → 比率（追问分子分母） |
| 折线 line / 面积 area | 折线 + 坐标轴；多条线 = 多个系列 | 趋势、走势、每日、每周、按月 | 趋势；多条线按不同日期统计时追问是否拆开 |
| 柱状 column | 底边对齐、高低不一的柱子 | 柱状、对比 | 构成（柱状）；横轴标签作为维度取值的线索 |
| 条形 / 排行 bar | 左边对齐、长短不一的横条 | 排行、排名、Top N、榜 | 构成（条形），`Top N` → `limit` |
| 环形 / 饼 donut | 圆、圆环、扇形 | 占比、构成、比例、结构 | 构成（环形），超过 5 类建议默认条形 |
| 漏斗 funnel | 上宽下窄的梯形叠放 | 漏斗、转化 | 条形 + 阶段固定顺序（取单选字段的选项顺序），追问是否只看进行中的阶段 |
| 明细表 table | 横竖线网格；表头一行小字 | 明细、清单、列表、名单、台账 | 「清单」→ **记录清单**（逐条列字段、筛选、排序）；表头是「次数 / 金额」这类 → 汇总表 |
| 热力 heatmap | 成片等大小方格 | 热力 | 堆叠图（配置看板暂无热力，需要时走精排路线） |
| 散点 scatter | 很多小圆点 | 散点、气泡、相关 | 柱状（同上） |
| 进度 meter | 半圆 / 圆环进度、仪表盘 | 达成、完成度、进度 | 比率指标卡 |
| 地图 map | 地图轮廓 | 地图 | 按地区的条形 |
| 文字 text | 一段说明文字 | 说明、备注 | Markdown 文本 |

图片上**看不清的字不要猜**：标题读不出来就写 `title: ""`、置信度 ≤ 0.5，让确认环节问。草图里的示意数字（「¥1,234 万」）只用来判断格式，不会被当成真实数据。

## wireframe.json（图片路线由 agent 手写）

```jsonc
{
  "version": 1,
  "source": { "type": "image", "image": "sketch.png", "recognized_by": "agent-vision" },
  "title": "项目周会看板",
  "canvas": { "x": 0, "y": 0, "w": 1400, "h": 900 },        // 图片像素尺寸
  "panels": [
    { "id": "i1", "title": "本周完成任务", "visual": "kpi", "confidence": 0.95,
      "evidence": ["大号数字「128」"], "bbox": { "x": 50, "y": 100, "w": 410, "h": 130 },
      "hints": { "value": "128", "format": "number" } },
    { "id": "i4", "title": "每周新建 vs 完成任务", "visual": "line", "confidence": 0.9,
      "evidence": ["两条折线 + 坐标轴"], "bbox": { "x": 50, "y": 260, "w": 820, "h": 300 },
      "hints": { "series": ["新建", "完成"] } },
    { "id": "i7", "title": "逾期任务清单", "visual": "table", "confidence": 0.93,
      "evidence": ["4 列表头 + 网格"], "bbox": { "x": 640, "y": 590, "w": 710, "h": 280 },
      "hints": { "columns": ["任务", "负责人", "计划截止", "逾期天数"] } }
  ]
}
```

`hints` 可选：`dimension`（各 X / 按 X / X 排行）、`measure`、`time_field`（按 X 日期）、`series`（多条线的名称）、`columns`（表头）、`categories`（横轴标签）、`value`、`format`。没写时转换器会从标题里推断。

## 字段对应怎么做（`wireframe_to_spec.py`）

1. **选表**：标题里的业务词 vs 表名和字段名（同义词 + 字面相似度）；证据弱时跟随看板上多数面板用的主表
2. **指标**：「额 / 金额 / 营收」→ 金额字段求和；「数 / 次数」→ 计数；「率」→ 比率（分子分母必问）；标题里的业务词能对上金额字段时（「签约排行」→ 合同金额）也按金额求和
3. **维度**：「各 X / 按 X / X 排行 / X 占比」→ 字段 X；没有线索时用标题匹配单选 / 关联字段（「商机阶段」→ 阶段）；清单的「任务」列 → 任务表主字段
4. **时间**：「按签约日期」直接用；否则按标题词匹配日期字段（「完成任务」→ 实际完成日期）
5. **状态词**：在途、在手、逾期、超期、待跟进 → 当前状态指标（`snapshot`），并追问筛选条件
6. 业务方言不在同义词里时，传 `--glossary glossary.json`（如 `{"GMV": ["实付金额"]}`）

对不上、拿不准的一律进 `open_questions`，**不要猜**。实测：画板草图 9 个面板生成 4 个问题，照片草图 8 个面板生成 7 个问题，答完后两份都 0 错误编译通过，指标与专家手写的模板数字一致。

## 输出：让用户快速确认

1. **识别结果**：脚本自动打印 ASCII 线框 + 识别表（面板、标题、识别为、置信度、依据、栅格）
2. **待确认问题**：用选择框逐条问。先报总数；低置信度（🔴 < 0.65）的类型问题放最前；每个问题给 2~4 个选项 + 「先按默认」
3. **生成后对照**：截图生成的看板，用 `compare_images.py` 和原图左右拼成一张对照图交给用户：
   ```bash
   python3 $SKILL/scripts/compare_images.py --left whiteboard-preview.jpg --right board.png --out compare.jpg \
     --left-label "输入：飞书画板草图" --right-label "输出：生成的看板"
   ```
4. 排版默认「原始布局」，保持草图的位置关系；用户可在页面右上角切换其他排版
