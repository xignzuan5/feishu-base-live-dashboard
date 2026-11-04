#!/usr/bin/env python3
"""把 skill 自带的看板模板装进一个妙搭全栈应用仓库（apps +init 拉下来的目录）。

用法：
    python3 install_template.py <app_repo_dir> [--title "xx 实时看板"] [--base-url https://...] [--force]

做的事（幂等，可重复执行）：
  1. 拷贝 template/ 下的文件到仓库同路径：
       shared/dashboard.interface.ts            前后端数据契约
       server/modules/dashboard/**              NestJS 看板接口（查询层按业务表写）
       client/src/dashboard/**                  通用看板组件库：3 套风格、全部面板、外壳、hooks
       client/src/pages/dashboard/**            5 种看板页面
       client/src/api/dashboard.ts              前端请求
  2. client/src/app.tsx：仍是脚手架占位（含 Welcome）时直接替换；否则写成 app.dashboard.example.tsx 并提示手动合并
  3. server/app.module.ts 注册 DashboardModule（放在 ViewModule 之前）
  4. shared/api.interface.ts 追加 `export * from './dashboard.interface'`
  5. client/src/api/index.ts 追加 `export * as dashboardApi from './dashboard'`
  6. 可选：改写 dashboard.config.ts 里的标题 / 数据源链接
"""
import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.normpath(os.path.join(HERE, "..", "template"))

COPY_ITEMS = [
    "shared/dashboard.interface.ts",
    "shared/spec-board.interface.ts",
    "server/modules/dashboard",
    "server/modules/blueprint",
    "client/src/dashboard",
    "client/src/pages/dashboard",
    "client/src/api/dashboard.ts",
    "client/src/api/spec-board.ts",
]
# 编译产物：已存在时永不覆盖（由 build_spec_bundle.py 维护）
GENERATED = {"server/modules/blueprint/spec.generated.ts"}


def copy_item(rel, repo, force):
    src = os.path.join(TEMPLATE, rel)
    dst = os.path.join(repo, rel)
    if os.path.isdir(src):
        for root, _dirs, files in os.walk(src):
            for f in files:
                s = os.path.join(root, f)
                d = os.path.join(dst, os.path.relpath(s, src))
                os.makedirs(os.path.dirname(d), exist_ok=True)
                rel_d = os.path.relpath(d, repo)
                if rel_d in GENERATED and os.path.exists(d):
                    continue
                if os.path.exists(d) and not force and open(s, "rb").read() != open(d, "rb").read():
                    print("  ! 跳过已修改的文件（加 --force 覆盖）：%s" % os.path.relpath(d, repo))
                    continue
                shutil.copy2(s, d)
    else:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst) and not force and open(src, "rb").read() != open(dst, "rb").read():
            print("  ! 跳过已修改的文件（加 --force 覆盖）：%s" % rel)
            return
        shutil.copy2(src, dst)
    print("  ✓ %s" % rel)


def patch_app_module(repo):
    p = os.path.join(repo, "server/app.module.ts")
    s = open(p, encoding="utf-8").read()
    for mod, path in (("DashboardModule", "./modules/dashboard/dashboard.module"),
                      ("SpecBoardModule", "./modules/blueprint/blueprint.module")):
        if mod in s:
            continue
        s = s.replace(
            "import { ViewModule } from './modules/view/view.module';",
            "import { ViewModule } from './modules/view/view.module';\n"
            "import { %s } from '%s';" % (mod, path),
        )
        marker = "// ====== @route-section: business-modules END ======"
        if marker in s:
            s = s.replace(marker, "%s,\n    %s" % (mod, marker))
        else:
            s = re.sub(r"(\n\s*)ViewModule,", r"\1%s,\1ViewModule," % mod, s, count=1)
        print("  ✓ app.module.ts 注册 %s" % mod)
    open(p, "w", encoding="utf-8").write(s)


def append_once(path, line):
    s = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    if line in s:
        return False
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(("\n" if s and not s.endswith("\n") else "") + line + "\n")
    return True


def patch_app_tsx(repo, force):
    p = os.path.join(repo, "client/src/app.tsx")
    src = os.path.join(TEMPLATE, "client/src/app.tsx")
    cur = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    tpl = open(src, encoding="utf-8").read()
    if cur == tpl:
        print("  · app.tsx 已是最新看板路由")
        return
    # 脚手架占位 / 之前由本模板安装（含 DashboardShell）→ 直接更新；其他业务路由 → 只给示例
    if force or "Welcome" in cur or not cur or "DashboardShell" in cur:
        shutil.copy2(src, p)
        print("  ✓ app.tsx 替换为看板路由")
    else:
        ex = os.path.join(repo, "client/src/app.dashboard.example.tsx")
        shutil.copy2(src, ex)
        print("  ! app.tsx 已有业务路由，未覆盖；参考 client/src/app.dashboard.example.tsx 手动合并")


def patch_config(repo, title, base_url):
    p = os.path.join(repo, "server/modules/dashboard/dashboard.config.ts")
    s = open(p, encoding="utf-8").read()
    if title:
        s = re.sub(r"title: '.*?',", "title: '%s'," % title.replace("'", "\\'"), s, count=1)
    if base_url:
        s = re.sub(r"baseUrl: '.*?',", "baseUrl: '%s'," % base_url, s, count=1)
    open(p, "w", encoding="utf-8").write(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--title")
    ap.add_argument("--base-url")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    if not os.path.exists(os.path.join(repo, ".spark/meta.json")):
        sys.exit("不是妙搭应用仓库（缺 .spark/meta.json）：%s" % repo)
    print("安装看板模板 → %s" % repo)
    for item in COPY_ITEMS:
        copy_item(item, repo, args.force)
    patch_app_tsx(repo, args.force)
    patch_app_module(repo)
    if append_once(os.path.join(repo, "shared/api.interface.ts"), "export * from './dashboard.interface';"):
        print("  ✓ shared/api.interface.ts 导出看板契约")
    if append_once(os.path.join(repo, "shared/api.interface.ts"), "export * from './spec-board.interface';"):
        print("  ✓ shared/api.interface.ts 导出配置看板契约")
    if append_once(os.path.join(repo, "client/src/api/index.ts"), "export * as dashboardApi from './dashboard';"):
        print("  ✓ client/src/api/index.ts 导出 dashboardApi")
    if append_once(os.path.join(repo, "client/src/api/index.ts"), "export * as specBoardApi from './spec-board';"):
        print("  ✓ client/src/api/index.ts 导出 specBoardApi")
    if args.title or args.base_url:
        patch_config(repo, args.title, args.base_url)
        print("  ✓ dashboard.config.ts 标题 / 数据源已更新")
    print("完成。下一步：npm run gen:db-schema → npm run type:check → npm run dev")


if __name__ == "__main__":
    main()
