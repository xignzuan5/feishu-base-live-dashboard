#!/usr/bin/env python3
"""按「同步计划」把多维表格的多张表，逐表建成妙搭应用数据库的 streaming 同步任务。

为什么要脚本：`apps +db-sync-create` 一次只处理一张表，且要 preview → 调整映射 → create。
本脚本把每张表的这三步固化下来，并支持：
  - exclude：关掉不需要同步的字段（反向关联、重计算的公式等）
  - rename：把自动生成的英文列名改成你想要的（只在 action=create 时生效）
  - 断点续跑：已建好的表（plan 输出里有 task_id）自动跳过

用法（在任意目录运行；所有文件路径相对当前目录）：
    python3 sync_base_to_miaoda.py plan.json --preview        # 只预览，生成 resolved 配置供人审
    python3 sync_base_to_miaoda.py plan.json --yes            # 预览 + 正式创建
    python3 sync_base_to_miaoda.py plan.json --yes --environment online --use-existing
        # 发布后在 online 环境对已存在的表再建一套 streaming 任务

plan.json 例：
{
  "app_id": "app_xxx",
  "base_url": "https://xxx.feishu.cn/base/<base_token>",
  "tables": [
    {"source": "门店", "target": "stores", "exclude": ["订单记录"], "rename": {"日营收目标": "daily_target"}}
  ]
}
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import larkcli  # noqa: E402

OUT_DIR = "sync"


def preview(app_id, env, cfg, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    src = os.path.join(OUT_DIR, "%s.%s.request.json" % (name, env))
    with open(src, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
    data = larkcli.run(["apps", "+db-sync-create", "--app-id", app_id, "--environment", env,
                        "--config", "@" + src, "--preview"], payload=None)
    return data


def apply_plan(resolved, table):
    exclude = set(table.get("exclude", []))
    rename = table.get("rename", {})
    kept, dropped = [], []
    for fm in resolved.get("field_maps", []):
        bname = (fm.get("base_field") or {}).get("name")
        if bname in exclude:
            fm["enabled"] = False
            dropped.append(bname)
            continue
        if bname in rename:
            fm["pg_field"]["name"] = rename[bname]
        kept.append("%s→%s(%s)" % (bname, fm["pg_field"]["name"], fm["pg_field"].get("type")))
    return kept, dropped


def merge_dev_mappings(resolved, target):
    """use_existing 时服务端按名字自动匹配列；rename 过的字段（如 优惠金额→discount）会漏。
    用 dev 环境建表时的最终映射补齐：同一 Base 字段 → 同一列名。返回补上的字段名列表。"""
    dev_path = os.path.join(OUT_DIR, "%s.dev.final.json" % target)
    if not os.path.exists(dev_path):
        return []
    with open(dev_path, encoding="utf-8") as fh:
        dev = json.load(fh)
    have = {(fm.get("base_field") or {}).get("name") for fm in resolved.get("field_maps", [])}
    added = []
    for fm in dev.get("field_maps", []):
        name = (fm.get("base_field") or {}).get("name")
        if fm.get("enabled", True) is False or name in have:
            continue
        # pg_field 必须带完整类型信息（只给列名会报 500002505「Currency -> 」类型无法映射）
        entry = {"base_field": {"name": name}, "pg_field": dict(fm["pg_field"])}
        if fm.get("option_mappings"):
            entry["option_mappings"] = fm["option_mappings"]
        resolved.setdefault("field_maps", []).append(entry)
        added.append(name)
    return added


def base_counts(base_url):
    token = re.search(r"/base/([A-Za-z0-9]+)", base_url).group(1)
    data = larkcli.run(["base", "+table-list", "--base-token", token])
    return {t.get("name"): t.get("records_count") for t in (data.get("tables") or [])}


def db_count(app_id, env, table):
    data = larkcli.run(["apps", "+db-execute", "--app-id", app_id, "--environment", env, "--yes",
                        "--sql", "SELECT COUNT(*) AS n FROM %s" % table])
    rows = data if isinstance(data, list) else (larkcli.find_key(data, "rows") or [data])
    return int((rows[0] or {}).get("n", 0)) if rows else 0


def heal(plan, env, minutes):
    """大表首轮全量同步在 online 环境会中途变成 error，重新 enable 会从断点续传。
    循环：error 的任务就 enable，直到每张表的数据库行数追平多维表格记录数。"""
    tasks = plan.get("tasks_%s" % env) or {}
    deadline = time.time() + minutes * 60
    while True:
        try:
            expected = base_counts(plan["base_url"])
        except larkcli.LarkError as e:
            print("  ⚠ 读取多维表格行数失败，下一轮重试：%s" % str(e)[:120], flush=True)
            time.sleep(45)
            continue
        pending = []
        for t in plan["tables"]:
            tid = tasks.get(t["source"])
            if not tid:
                continue
            try:
                status = larkcli.find_key(larkcli.run(["apps", "+db-sync-get", "--app-id", plan["app_id"],
                                                       "--task-id", tid]), "status")
                have = db_count(plan["app_id"], env, t["target"])
            except larkcli.LarkError as e:
                # 线上库连接数很小（实测会报 remaining connection slots are reserved），临时失败下一轮再试
                print("  ⚠ %s 查询失败，下一轮重试：%s" % (t["source"], str(e)[:120]), flush=True)
                pending.append(t["source"])
                continue
            want = expected.get(t["source"]) or 0
            done = have >= want and status == "active"
            print("  %s %-8s %s → %s：%d / %d" % ("🟢" if done else "🟡", t["source"], status, t["target"], have, want), flush=True)
            if status == "error":
                larkcli.run(["apps", "+db-sync-enable", "--app-id", plan["app_id"], "--task-id", tid])
            if not done:
                pending.append(t["source"])
        if not pending:
            print("✅ %s 环境全部追平" % env)
            return True
        if time.time() > deadline:
            print("⏱ 超时仍未追平：%s（可再次运行 --heal 续传）" % "、".join(pending))
            return False
        time.sleep(45)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--environment", default="dev", choices=["dev", "online"])
    ap.add_argument("--use-existing", action="store_true", help="目标表已存在（如发布后的 online）")
    ap.add_argument("--preview", action="store_true", help="只预览不创建")
    ap.add_argument("--yes", action="store_true", help="确认创建同步任务（高危写操作）")
    ap.add_argument("--only", nargs="*", help="只处理这些 source 表")
    ap.add_argument("--heal", action="store_true", help="续传：error 的任务自动重新启用，直到行数追平")
    ap.add_argument("--heal-minutes", type=float, default=20)
    args = ap.parse_args()

    with open(args.plan, encoding="utf-8") as fh:
        plan = json.load(fh)
    if args.heal:
        sys.exit(0 if heal(plan, args.environment, args.heal_minutes) else 1)
    if not args.preview and not args.yes:
        sys.exit("需要 --preview 或 --yes")
    state_key = "tasks_%s" % args.environment
    plan.setdefault(state_key, {})
    action = "use_existing" if args.use_existing else "create"

    for table in plan["tables"]:
        src_name, target = table["source"], table["target"]
        if args.only and src_name not in args.only:
            continue
        if plan[state_key].get(src_name) and not args.preview:
            print("· %s 已有任务 %s，跳过" % (src_name, plan[state_key][src_name]))
            continue
        cfg = {
            "mode": "streaming",
            "source": {"type": "base", "base_url": plan["base_url"], "table": {"name": src_name}},
            "target": {"type": "postgresql", "table": {"name": target, "action": action}},
        }
        data = preview(plan["app_id"], args.environment, cfg, target)
        resolved = data.get("config") or {}
        if args.use_existing:
            patched = merge_dev_mappings(resolved, target)
            if patched:
                print("   ⚠ 自动匹配漏掉 %s（改过列名的字段按名字匹配不上），已按 dev 映射补齐" % patched)
        kept, dropped = apply_plan(resolved, table)
        final_path = os.path.join(OUT_DIR, "%s.%s.final.json" % (target, args.environment))
        with open(final_path, "w", encoding="utf-8") as fh:
            json.dump(resolved, fh, ensure_ascii=False, indent=2)
        summary = data.get("summary") or {}
        print("▶ %s → %s [%s] 预计 %s 行；同步 %d 列，排除 %s" % (
            src_name, target, action, summary.get("estimated_record_count"), len(kept), dropped or "无"))
        print("   " + "，".join(kept))
        if args.preview:
            continue
        created = larkcli.run(["apps", "+db-sync-create", "--app-id", plan["app_id"],
                               "--environment", args.environment, "--config", "@" + final_path, "--yes"])
        task_id = larkcli.find_key(created, "task_id") or larkcli.find_key(created, "id")
        plan[state_key][src_name] = task_id
        with open(args.plan, "w", encoding="utf-8") as fh:
            json.dump(plan, fh, ensure_ascii=False, indent=2)
        print("   ✅ 已创建同步任务 %s" % task_id)


if __name__ == "__main__":
    main()
