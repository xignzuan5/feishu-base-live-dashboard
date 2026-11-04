# 实测踩坑与恢复办法

全部来自本 skill 的真实搭建过程（lark-cli 1.0.98，妙搭 nestjs-react-fullstack 模板）。

## 多维表格 → 应用数据库同步

| 现象 | 原因 | 处理 |
|---|---|---|
| `+db-sync-create` 建表报 `k_dl_4000001` | 新建的全栈应用是 dev / online 双环境，online 禁止建表 | 建表一律 `--environment dev`；online 等发布带过去表结构后用 `use_existing` |
| online 同步后某些列一直是空（如 `discount`） | `use_existing` 时服务端**按名字自动匹配列**，改过名的字段（优惠金额 → discount）匹配不上，被静默漏掉 | `sync_base_to_miaoda.py` 已自动用 dev 映射补齐并提示；手工补救用 `+db-sync-update`，`pg_field` 必须带完整类型（只给列名会报 `500002505 … Currency ->`） |
| 发布后线上看板是空的 | 发布只带表结构，不带数据 | 发布后给 online 再建一套同步：`--environment online --use-existing` |
| online 大表同步到一半，任务变成 `error`，`+db-sync-get` 不给原因 | online 环境首轮全量同步大表（上千行）会中途中断；小表不受影响 | 重新 `+db-sync-enable` 会**从断点续传**；`sync_base_to_miaoda.py --heal --environment online` 自动循环续传，直到数据库行数追平多维表格 |
| online 查询报 `remaining connection slots are reserved for roles with the SUPERUSER attribute` | online 数据库连接上限很小，同步任务、线上应用、调试查询、发布部署同时占连接 | 少开并发同步任务、调试查询用完即止、避开发布窗口；`--heal` 遇到它会自动下一轮重试。这很可能也是 online 首轮同步反复中断的原因 |
| online 首轮同步极慢（实测每 25 分钟只追几百行；同样数据 dev 1 分钟同步完） | online 环境的首轮全量同步吞吐低，并且会反复中断 | 演示 / 上线前**提前几小时**建好 online 同步并挂着 `--heal`；数据量大时先在 dev 演示，online 只放增量；同一时间不要并发建大量同步任务 |
| 门店表一行几千个 id、同步很慢 | 双向关联在对方表生成的「反向关联」字段也会同步 | 同步计划里 `exclude` 掉反向关联字段和重计算的公式 |
| 多选字段 SQL 报类型错 | 多选同步成 `text[]`，不是逗号字符串 | 用 `@>` / `&&` / `unnest`（引擎已处理） |
| 公式字段做 SUM 报错 | 公式同步成 `text` | `NULLIF(col::text,'')::numeric`（引擎已处理） |

关联字段同步后的形态：`{"link_record_ids": ["rec…"]}`；**未关联时是 `{"link_record_ids": null}`（JSON null）**，对它用 `jsonb_array_length` 会报 `22023`。判断是否有关联用 `(col->'link_record_ids'->>0) IS NOT NULL`。

## 多维表格建模

| 现象 | 原因 | 处理 |
|---|---|---|
| 公式 `[客户].[行业]` 返回整张表的所有行业拼在一起 | 公式里 `[客户]` 优先解析成**同名的表**，而关联字段默认就叫目标表名 | 关联字段和目标表不要同名（如表叫「客户档案」、字段叫「客户」）；或看板直接用 `via` 按关联表字段分组，不必写公式 |
| 「跟进超期」越积越多 | 只看「下次跟进日期 < 今天」，旧记录永远超期 | 加「下次跟进状态」字段（待跟进 / 已完成 / 无需跟进），只统计待跟进；演示时可配多维表格自动化：新增跟进时把上一条置为已完成 |
| 赢单率按日期统计不准 | 输单没有结单日期 | 赢单、输单都填「结单日期」 |

## SQL / Drizzle

| 现象 | 原因 | 处理 |
|---|---|---|
| `42803 column must appear in the GROUP BY clause` | 时区作为参数传入：SELECT 里是 `$1`、GROUP BY 里是 `$11`，PG 认为是两个不同表达式 | 时区校验后用 `sql.raw` 内联成字面量 |
| `ERR_INVALID_ARG_TYPE` | 在 `sql\`\`` 片段里直接传了 `Date` 对象 | 传 `date.toISOString()` 再 `::timestamptz` |
| `sql.identifier` 类型报错 TS2740 | 它返回 `Name` 不是 `SQL` | 包一层：`` sql`${sql.identifier(name)}` `` |
| `db-execute` 只读查询也要 `--yes` | CLI 对所有 SQL 一律做高危确认 | SELECT 可以直接加 `--yes` |

## 妙搭本地开发

| 现象 | 原因 | 处理 |
|---|---|---|
| `npm run dev` 同步完脚本就退出 | 启动时 `miaoda app sync` 改写了正在执行的 `dev.sh` | 直接 `npm run dev:local` |
| 3000 端口被占 | 本机其他服务 | `.env.local` 加 `SERVER_PORT=` / `CLIENT_DEV_PORT=`，不要改 vite / nest 配置 |
| curl 接口 403 | CSRF 双提交校验 | 带 `Cookie: suda-csrf-token=x` 和 `X-Suda-Csrf-Token: x`，走前端端口 + `CLIENT_BASE_PATH` 前缀 |
| ESLint 报「Controller 未在 module 里注册」，其实已注册 | `nestjs-typed` 插件把过滤串 `.spec.` 当正则，`/spec-board/` 目录被当成测试文件忽略 | 后端目录不要叫 `spec-xxx`（本模板用 `blueprint/`） |
| 新路由打开是「页面不存在」 | `app.tsx` 没更新 | `install_template.py` 会更新本模板装过的 `app.tsx`；自定义过的会写 `app.dashboard.example.tsx` 让你手动合并 |

## 多维表格仪表盘迁移

| 现象 | 原因 | 处理 |
|---|---|---|
| `+dashboard-block-get-data` 偶发 `API error [1]` | 服务端偶发 | 迁移脚本已退避重试 4 次 |
| 原仪表盘折线图按日期分组，数字对不上 | 原图按**时间点**逐个分组（几千个点），接口返回被截断 | 迁移后按天聚合；核对时识别截断，丢弃最后一个不完整分组 |
| 关联字段维度显示成 id | — | 引擎按对方表**主字段**显示，与多维表格一致（主字段来自 `+table-get` 的 `primary_field`） |

## 数据与展示

| 现象 | 处理 |
|---|---|
| 演示数据「不像真的」（某渠道客单价离谱、目标达成 900%） | 造数后算一遍核心指标的分布再上看板；目标按历史日均 × 0.95~1.12 校准 |
| 今日达成率虚高 | 今日目标按「近 4 周同时段营收占比」折算，而不是按营业时长线性折算 |
| 时间显示成浏览器本地时区 | 前端统一用业务时区格式化（`BUSINESS_TZ`） |
| 按天走势最后一天「跳水」 | 今天还没过完：最后一桶标为「今日」 |
| 同一品类在不同图里颜色不同 | 实体固定配色 `theme/entities.ts` |
