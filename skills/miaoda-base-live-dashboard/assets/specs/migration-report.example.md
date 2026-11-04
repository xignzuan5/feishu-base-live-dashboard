# 多维表格仪表盘 → 妙搭看板 迁移报告

- 源仪表盘：**经营仪表盘（多维表格原生）**（https://your-tenant.feishu.cn/base/<base_token>）
- 组件数：9，生成面板：9
- 生成时间：2026-11-03 23:03

## 组件 → 面板对照

| 组件 | 原类型 | 面板 | 默认图表 / 可切换 | 数据表 | 指标 | 维度 | 筛选 | 说明 |
|---|---|---|---|---|---|---|---|---|
| 实付营收 | statistics | kpi | — / — | 订单 | 实付金额(SUM) | — | 订单状态 isNot ['已退款']；订单状态 isNot ['已取消'] |  |
| 订单总数 | statistics | kpi | — / — | 订单 | 全部记录(COUNT) | — | — |  |
| 看板说明 | text | text | — / — | — | — | — | — |  |
| 每日营收趋势 | line | trend | line / line、area、bar | 订单 | 实付金额(SUM) | 下单时间 | 订单状态 isNot ['已退款']；订单状态 isNot ['已取消'] | 原图按时间点逐个分组（点过密），迁移后按天聚合；今日视图按小时 |
| 渠道营收 | column | category | column / column、bar、treemap、donut、segmented | 订单 | 实付金额(SUM) | 渠道 | 订单状态 isNot ['已退款']；订单状态 isNot ['已取消'] |  |
| 支付方式占比 | ring | category | donut / donut、segmented、bar、treemap | 订单 | 全部记录(COUNT) | 支付方式 | — |  |
| 门店营收 Top10 | ranking | category | bar / bar、column、treemap | 订单 | 实付金额(SUM) | 门店 | 订单状态 isNot ['已退款']；订单状态 isNot ['已取消'] |  |
| 会员等级分布 | bar | category | bar / bar、column、treemap、donut、segmented | 会员 | 全部记录(COUNT) | 会员等级 | — |  |
| 杯型 × 温度 | column | stacked | stacked / stacked、grouped、percent | 订单明细 | 数量(SUM) | 规格、温度 | — |  |

## 需要处理

- 🟢 用到的表和字段都已在同步计划内

## 迁移后的增强（原仪表盘没有）

- 实时：多维表格改数约 10 秒后看板自动刷新，无需手动刷新页面
- 3 套风格一键切换（深烘焙 / 燕麦白 / 霓虹大屏），可投屏
- 每个面板可切换图表类型；同一实体全局同色
- 可选：给面板加时间范围（见各面板 suggested_time_field），并补对比周期

## 核对

迁移完成后运行 `verify_spec_board.py`，逐个面板对比多维表格原值与看板接口返回值。
