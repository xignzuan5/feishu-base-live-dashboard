---
name: miaoda-base-live-dashboard
description: 把飞书多维表格变成妙搭上的「实时」数据看板应用：多维表格流式同步进应用数据库，看板每 5 秒刷新，改表后 5~10 秒可见。需求可以来自飞书会议（从纪要和逐字稿提炼）、已有的多维表格仪表盘（一键迁移，并逐项核对数字）或行业模板（零售连锁、工作管理、客户管理）。提供 8 套风格、8 种排版，每个面板都能切换图表类型；有模板中心和投屏大屏，自带设计检查，保证专业、不像 AI 生成。当用户说「基于多维表格做看板 / 驾驶舱 / 大屏 / BI」「把多维表格仪表盘搬到妙搭」「根据会议需求做个看板」「妙搭看板」「工作管理 / 客户管理看板」「做个演示看板」时使用。只要在多维表格里加一个原生仪表盘、不需要独立应用时，改用 lark-base 的 Dashboard。
---

# 多维表格 → 妙搭实时看板

数据留在飞书多维表格，业务同学照常录入、改数。妙搭应用通过官方 Base 流式同步把表实时复制进应用数据库，看板每 5 秒轮询一次，新增或修改的记录 5~10 秒内上屏。

```
飞书会议纪要 ─┐
原生仪表盘 ────┼─► dashboard-spec.json ─► 看板引擎（不用写查询）─┐
行业模板 ─────┘                                                ├─► 妙搭看板：8 风格 × 8 排版 × 可切换图表
飞书多维表格 ──流式同步（秒级）──► 应用数据库 PG ──5 秒轮询────────┘
```

## 什么时候用它（对比多维表格「AI 页面」）

| | 多维表格 AI 页面 | 本 skill |
|---|---|---|
| 上手 | 一句话生成，最快 | 需要建应用、同步，约 20 分钟 |
| 数据量与性能 | 直接读表 | 同步进 PG，几万行聚合也是毫秒级 |
| 可改性 | 页面内调整 | 完整源码，可二次开发、接入其他系统 |
| 场景 | 单页展示 | 多看板、投屏大屏、行业模板、仪表盘迁移并核对口径、会议需求溯源 |

## 能力一览

| 能力 | 内容 | 详见 |
|---|---|---|
| 需求来源 | 飞书会议 / 原生仪表盘迁移 / 行业模板 / 现场问答，产出统一的 `dashboard-spec.json` | [dashboard-spec.md](references/dashboard-spec.md) |
| 行业模板 | 零售连锁（5 个精排看板 + 大屏）、工作管理、客户管理（各 2 个看板），带一键造数 | [catalog.md](references/catalog.md) |
| 风格 | 深烘焙、燕麦白、霓虹大屏、晴空、墨石、青瓷、深海、松针（配色都过色盲与对比度校验） | catalog.md |
| 排版 | 原始布局、管理层简报、指挥中心、分析工作台、个人工作台、记分对比、杂志式、单列聚焦 | catalog.md |
| 面板 | 指标卡、趋势、构成、堆叠、热力、散点、进度、订单流、明细表、文本；趋势 / 构成 / 堆叠可切换 3~5 种图表 | catalog.md |
| 质量 | 迁移口径逐项核对、需求说明设计检查、截图盲评 | [design-quality.md](references/design-quality.md) |

## 依赖

- `lark-cli` ≥ 1.0.98，已登录，用户身份有 `base:*`、`spark:app:*`（会议来源还需要 `vc` / `minutes` 读权限）。缺权限按 `lark-shared` 处理
- 执行前加载：**`lark-base`**（多维表格）、**`lark-apps`**（妙搭应用、同步、发布）；会议来源加载 **`lark-meeting`**；改配色加载 **`dataviz`**；设计评审用 **`frontend-design`**、**`ux-aesthetic-review`**
- 本地：`git`、Node ≥ 22、Python ≥ 3.9、`agent-browser`（截图自检）

## 开工前确认（一次问完，用选择框）

| 决策 | 选项 | 默认 |
|---|---|---|
| 需求从哪来 | 飞书会议 / 已有多维表格仪表盘 / 行业模板 / 现在聊 | 用户给了会议或仪表盘链接就用它 |
| 数据从哪来 | 用户的多维表格（给链接）/ 演示数据（零售连锁、工作管理、客户管理） | 没给链接就用演示数据 |
| 设计调性 | 克制 / 商务 / 人文 / 科技 → 决定风格和排版 | 按受众推：老板周会 → 商务，值守 → 克制，投屏 → 科技 |
| 是否发布上线 | 发布（线上链接默认仅本人可见）/ 只在本地预览 | 发布前单独确认一次 |

## 流程

`$SKILL` 为本 skill 目录，`$WORK` 为空工作目录（放状态文件和同步配置）。

### 1. 需求 → dashboard-spec.json

- **飞书会议**：按 [requirements-from-meeting.md](references/requirements-from-meeting.md)：定位会议 → 读逐字稿原话 → 按清单提炼 → 待定口径用选择框问 → 画 ASCII 线框图确认
- **原生仪表盘**：`python3 $SKILL/scripts/import_base_dashboard.py --base-url <链接> --dashboard <名称>`（不带 `--dashboard` 先列出全部），自动产出需求说明、迁移报告和原值快照
- **行业模板**：`assets/specs/{work,crm}.spec.json`，把表名、字段名换成用户的
- 检查：`python3 $SKILL/scripts/lint_spec.py dashboard-spec.json`，🔴 必须为 0

### 2. 准备数据

- **用户的多维表格**：`lark-cli base +url-resolve`、`+table-list`、`+field-list` 摸清表结构
- **演示数据**（约 5 分钟，可断点续跑）：
  ```bash
  cd $WORK && python3 $SKILL/scripts/seed_coffee_base.py          # 零售连锁：6 表 2.1 万行
  python3 $SKILL/scripts/seed_base.py --domain work               # 工作管理
  python3 $SKILL/scripts/seed_base.py --domain crm                # 客户管理
  ```

### 3. 建妙搭全栈应用

```bash
lark-cli apps +create --as user --name "<看板名>" --app-type full_stack --description "<一句话>"
lark-cli apps +init --as user --app-id <app_id> --dir ./<app-dir>
```

### 4. 同步：多维表格 → 应用数据库

写同步计划（模板：`assets/sync-plan.coffee.json`、`assets/sync-plans/*.plan.json`），每张表写源表、目标表、排除字段、列名改名。多个多维表格进同一个应用时，目标表加前缀。

```bash
cd $WORK
python3 $SKILL/scripts/sync_base_to_miaoda.py sync-plan.json --preview   # 逐表看映射
python3 $SKILL/scripts/sync_base_to_miaoda.py sync-plan.json --yes       # 建 streaming 任务（dev）
```

排除反向关联字段和重计算的公式；建表只能在 dev。同步后的数据形态与报错恢复见 [pitfalls.md](references/pitfalls.md)。

### 5. 安装模板并编译看板

```bash
cd <app-dir> && npm run gen:db-schema
python3 $SKILL/scripts/install_template.py <app-dir> --title "<看板标题>" --base-url "<多维表格链接>"
python3 $SKILL/scripts/build_spec_bundle.py --pair dashboard-spec.json:sync-plan.json --app <app-dir>   # 多份 spec 就多个 --pair
npm run type:check && npx eslint server client/src/dashboard client/src/pages/dashboard --quiet
```

`build_spec_bundle.py` 不能有 ⚠。升级已安装过的模板时加 `--force`（否则改过的文件会被跳过，并打印提示）。用户的看板需要跨表复杂计算时，按 [adapt-to-your-base.md](references/adapt-to-your-base.md) 的路线 B 精细定制。

### 6. 本地验证与设计把关

```bash
# 端口被占就在 .env.local 加 SERVER_PORT= / CLIENT_DEV_PORT=
npm run dev:local
# 迁移来的看板：逐面板核对数字（与原仪表盘一致才算完成）
python3 $SKILL/scripts/verify_spec_board.py --spec dashboard-spec.json --url http://localhost:<CLIENT_DEV_PORT>/app/<app_id>
```

按 [design-quality.md](references/design-quality.md) 过四关：定调 → 线框确认 → 机检 → **每个看板 × 选定风格截图自检**（`?style=<风格>` 可直接指定风格）。两套方案拿不准时用 `ux-aesthetic-review` 做盲评。不要只看接口返回就交付。

### 7. 演示「实时」

```bash
cd $WORK && python3 $SKILL/scripts/simulate_orders.py --interval 5     # 零售演示：每 ~5 秒下一单
```

最有说服力的演示：现场在多维表格里改一单的金额或状态，几秒后看板跟着变。

### 8. 发布上线（需用户确认一次）

```bash
git add <本次文件> && git commit -m "feat: 多维表格实时看板" && git push origin sprint/default
lark-cli apps +release-create --as user --app-id <app_id> --branch sprint/default --apply-reason "<已确认的理由>"
lark-cli apps +release-get --as user --app-id <app_id> --release-id <release_id>     # 轮询到 finished 拿 online_url
# 发布只带表结构不带数据：给 online 建同步，并续传到行数追平
python3 $SKILL/scripts/sync_base_to_miaoda.py sync-plan.json --yes --environment online --use-existing
python3 $SKILL/scripts/sync_base_to_miaoda.py sync-plan.json --heal --environment online
```

线上链接默认仅创建者可见，给别人看先 `lark-cli apps +access-scope-set`。

## 交付时汇报

多维表格链接、应用开发态链接 `https://miaoda.feishu.cn/app/<app_id>`、线上链接、同步任务（dev / online）及行数是否追平、端到端实测延迟、迁移核对结果、设计检查结果、截图路径，以及本次的取舍（排除了哪些字段、哪些口径待确认）。

## 文件清单

| 路径 | 作用 |
|---|---|
| `scripts/import_base_dashboard.py` | 原生仪表盘 → 需求说明 + 迁移报告 + 原值快照 |
| `scripts/verify_spec_board.py` | 迁移口径核对（原值 vs 新看板） |
| `scripts/lint_spec.py` | 需求说明设计检查 |
| `scripts/build_spec_bundle.py` | 需求说明 → 看板引擎配置 |
| `scripts/sync_base_to_miaoda.py` | 逐表建同步（dev / online）、`--heal` 续传 |
| `scripts/install_template.py` | 把模板装进妙搭全栈仓库（幂等） |
| `scripts/seed_base.py` + `domains/*.py` | 行业演示数据（工作管理、客户管理） |
| `scripts/seed_coffee_base.py` + `coffee_demo.py` | 零售连锁演示数据 |
| `scripts/simulate_orders.py` | 实时下单模拟器 |
| `template/server/modules/blueprint/` | 配置驱动看板引擎（需求说明 → SQL） |
| `template/server/modules/dashboard/` | 零售连锁精排看板的查询与组装 |
| `template/client/src/dashboard/` | 组件库：8 风格、8 排版、实体配色、全部面板、外壳 |
| `template/client/src/pages/dashboard/` | 内置看板、配置驱动看板页、模板中心 |
| `assets/specs/`、`assets/sync-plans/` | 行业模板需求说明与同步计划 |
| `references/` | 需求格式、目录、会议梳理、设计质量、改造指南、踩坑 |
