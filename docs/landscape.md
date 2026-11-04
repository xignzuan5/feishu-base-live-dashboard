# 同类项目与定位

调研时间：2026-11（星数与活跃度为当时数据）。

## 结论

开源社区里**没有**一个项目覆盖「飞书多维表格 → 流式同步进 Postgres → 实时看板 → 部署在飞书妙搭」整条链路。

- **独有**：多维表格原生仪表盘一键迁移并**逐面板核对数字**；多维表格实时同步 + 5 秒刷新；从会议逐字稿提炼需求并溯源；面向中国企业的行业领域包（含造数）；需求说明设计检查；以 Agent Skill 形式交付
- **通用能力**（别家也有）：ECharts 渲染、指标卡、主题风格、大屏模板、JSON 配置看板、轮询刷新

## 飞书 / 多维表格方向

| 项目 | 做什么 | 与本项目的关系 |
|---|---|---|
| [XX78/feishu-dashboard-starter](https://github.com/XX78/feishu-dashboard-starter) | 飞书**电子表格** → 静态 JSON → React + ECharts → 妙搭托管 | 最接近；不实时、单场景。值得借鉴：无账号也能用 mock 数据本地预览 |
| [Lark-Base-Team](https://github.com/Lark-Base-Team) 的仪表盘插件模板、[lark-base-mcp-node-server](https://github.com/Lark-Base-Team/lark-base-mcp-node-server) | 多维表格仪表盘**插件**开发模板；Base MCP | 可以把本项目的面板反向打包成 Base 插件 |
| 社区单图插件（雷达图、波士顿矩阵、热力图等） | 每个只做一种图 | 社区还没有「整板方案」 |
| [luotwo/amazon-product-search](https://github.com/luotwo/amazon-product-search) | Claude Code skill：拉数据 → 建多维表格 → 建原生仪表盘 | 走原生仪表盘路线；本项目是独立应用 + 实时同步 |
| [lzyscg/feishu-bitable-sync](https://github.com/lzyscg/feishu-bitable-sync) | 配置驱动的多维表格同步，带预演 | 同步前预演的做法值得借鉴（本项目已有 `--preview`） |
| [larksuite/cli](https://github.com/larksuite/cli)、[lark-openapi-mcp](https://github.com/larksuite/lark-openapi-mcp)、[cso1z/Feishu-MCP](https://github.com/cso1z/Feishu-MCP) | 官方 CLI / MCP | 本项目的底座（lark-base、lark-apps skill） |
| 妙搭部署类 skill（miaoda-agent-kit、codex-miaoda-driver、miaoda-deploy-skill） | 只管部署和驱动 | 本项目在其上做看板领域 |

产品层面的直接对手是**多维表格「AI 页面」**（官方，一句话生成页面）：上手更快；本项目胜在数据量、可二次开发、大屏、行业模板、迁移核对。

## 表格型数据库 + 看板

[Baserow](https://github.com/baserow/baserow)（已内置 Dashboards）、[Teable](https://github.com/teableio/teable)（底层 Postgres）、[NocoDB](https://github.com/nocodb/nocodb)、[Grist](https://github.com/gristlabs/grist-core)、[notion-charts](https://github.com/mathix420/notion-charts)：说明「表格 + 看板」是刚需，但都绑定各自的表格产品。

## 配置驱动看板 / BI（参照系）

| 项目 | 可借鉴 |
|---|---|
| [Rill](https://github.com/rilldata/rill)、[Cube](https://github.com/cube-js/cube) | **指标层**：口径定义一次，面板只引用指标 |
| [Grafana](https://github.com/grafana/grafana) | 看板 JSON、**全局变量**、**告警** |
| [Evidence](https://github.com/evidence-dev/evidence)、[Vizro](https://github.com/mckinsey/vizro)、[Lightdash](https://github.com/lightdash/lightdash) | 看板即代码；Vizro 的「先线框后实现」已吸收进本项目 |
| [DataEase](https://github.com/dataease/dataease)、[JimuReport](https://github.com/jeecgboot/jimureport)、[DataRoom](https://github.com/gcpaas/DataRoom)、[GoView](https://github.com/dromara/go-view) | 国产 BI / 大屏；JimuReport、DataRoom 的「一句话生成 / 对话修改」 |
| [WrenAI](https://github.com/Canner/WrenAI)、[DB-GPT](https://github.com/eosphoros-ai/DB-GPT)、[Vanna](https://github.com/vanna-ai/vanna)、[SuperSonic](https://github.com/tencentmusic/supersonic) | ChatBI / GenBI |
| [antvis/mcp-server-chart](https://github.com/antvis/mcp-server-chart)、[apache/echarts-mcp](https://github.com/apache/echarts-mcp)、[VisActor/skills](https://github.com/VisActor/skills) | 图表生成 MCP / skill |

## 路线图（从调研里来）

1. **指标层**：在需求说明里单独定义指标（口径、分子分母），面板只引用指标 id；设计检查、数字核对、以后的问答都复用
2. **全局变量与阈值告警**：门店、日期范围等变量；阈值触发时推送飞书群卡片
3. **对话改看板**：自然语言只改需求说明，先给出差异预览，再检查、编译
4. **无账号体验**：mock 数据 + 本地 Postgres（docker compose），不登录飞书也能跑起来看效果
5. **反向导出**：把面板打包成多维表格仪表盘插件，嵌回多维表格
