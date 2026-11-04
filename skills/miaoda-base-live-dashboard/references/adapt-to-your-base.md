# 换成你自己的多维表格

两条路，**优先走配置驱动**：

| 路线 | 适合 | 要写代码吗 |
|---|---|---|
| A. 配置驱动（Spec Board） | 绝大多数看板：指标卡、趋势、构成、排行、堆叠、明细 | 不用。写 / 生成 `dashboard-spec.json` → 编译 |
| B. 精细定制（像内置的鹿野咖啡看板） | 需要跨表复杂计算（目标按历史时段折算、价格 × 毛利散点、实时订单流）或特殊交互 | 要。改 `server/modules/dashboard/` 的查询和 `client/src/pages/dashboard/` 的页面 |

## 路线 A：配置驱动

1. **同步**：写同步计划（每张表：`source` 多维表格表名、`target` 数据库表名、`exclude`、`rename`），跑 `sync_base_to_miaoda.py --preview` 看映射，再 `--yes`。多个多维表格同步进同一个应用时，目标表名加前缀（`crm_`、`work_`）。
2. **需求说明**：三选一
   - 有原生仪表盘：`import_base_dashboard.py --base-url … --dashboard … --sync-plan sync-plan.json`
   - 有需求会：按 [requirements-from-meeting.md](requirements-from-meeting.md) 提炼
   - 套行业模板：复制 `assets/specs/<领域>.spec.json`，把表名、字段名换成你的
3. **检查**：`lint_spec.py dashboard-spec.json`，🔴 必须为 0。
4. **编译**：`build_spec_bundle.py --pair dashboard-spec.json:sync-plan.json --app <应用目录>`，输出不能有 ⚠。多份 spec 用多个 `--pair` 一起编译。
5. **核对**：迁移来的看板跑 `verify_spec_board.py`，逐面板对比原仪表盘的数字。
6. 打开 `/spec/<看板 key>`，在模板中心挑风格和排版。

字段类型对应（引擎自动处理）：

| 多维表格 | 数据库 | 作维度时 | 作指标时 |
|---|---|---|---|
| 文本、单选、电话、链接 | text | 按值分组 | 计数 |
| 多选 | text[] | `enumerated` 每个选项各计一次 | 计数 |
| 数字、货币、评分、进度 | numeric / int8 | 不建议 | SUM / AVG / MAX / MIN |
| 日期 | timestamptz / date | 今日按小时，多日按天 | — |
| 关联 | jsonb | 显示对方表主字段 | `COUNT_DISTINCT` 去重计数 |
| 复选框 | bool | 是 / 否 | 用 `where` 计数 |
| 公式 | text / numeric | 按值分组 | 数值公式可 SUM |

## 路线 B：精细定制

改这几处（都在 `template/` 同路径，安装后在应用仓库里）：

| 文件 | 改什么 |
|---|---|
| `server/modules/dashboard/dashboard.config.ts` | 标题、时区、数据源链接、无效状态、营业时段 |
| `client/src/dashboard/theme/entities.ts` | 实体固定配色：你的品类 / 渠道 / 阶段取值 |
| `server/modules/dashboard/dashboard.repository.ts` | 查询：按你的表写聚合（关联写法 `linkId(col) = target.baseRecordId`） |
| `server/modules/dashboard/dashboard.service.ts` | 把查询结果组装成标准数据形状（`shared/dashboard.interface.ts`） |
| `client/src/pages/dashboard/*.tsx` | 页面编排：从 `components/ChartPanels`、`ListPanels`、`KpiTile` 里挑面板 |
| `client/src/dashboard/boards.ts` | 导航、默认时间范围、说明 |

前端面板只认标准数据形状（KPI、趋势、构成、堆叠、热力、散点、进度、订单流、表格），后端按形状吐数据，前端几乎不用动。改完：`npm run gen:db-schema` → `npm run type:check` → 截图自检。
