"""「星河科技」工作管理（项目 / 任务管理）演示数据：表结构 + 有业务规律的数据生成器。

四张表：成员 → 项目 → 任务 / 里程碑（只用单向关联，表结构干净）。
时间均为 Asia/Shanghai 本地日期，写入格式 `YYYY-MM-DD 00:00`；只依赖「今天」这个日期，
同一天重复运行得到同一份数据（固定随机种子），便于 seed_base.py --resume 断点续跑。

内置的业务规律（看板上能看出来）：
  - 每个项目按 规划 → 设计 → 开发 → 测试 → 上线 → 已结项 推进；任务量与类型随阶段变化
  - 上线后 1~2 周缺陷集中爆发（6 个项目在近 90 天内上线，双 11 大促保障 3 天前刚上线）
  - 双周迭代：每隔一周的周五是迭代结束日，需求 / 优化在迭代末集中验收完成；周一集中建任务
  - P0 任务截止紧、完成快；P3 拖得久
  - 少数成员同时挂在多个项目上、任务明显偏多，交付也更慢 → 逾期集中在这些人身上
  - 已延期 / 有风险的项目卡住的任务多；约 1 成任务逾期（计划截止已过且未完成）
  - 缺陷的实际工时相对预估偏差最大（修 bug 难估）
"""
import math
import random
from datetime import date, datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

TZ = "Asia/Shanghai"
DAYS = 90
SEED = 20261103
TASK_SCALE = 0.84
SPRINT_ANCHOR = date(2026, 1, 2)  # 某个迭代结束日（周五）；之后每 14 天一个

BASE_NAME = "星河科技 · 工作管理（演示）"


def now_local():
    if ZoneInfo:
        return datetime.now(ZoneInfo(TZ)).replace(tzinfo=None)
    return datetime.utcnow() + timedelta(hours=8)


def opt(*names_hues):
    return [{"name": n, "hue": h, "lightness": "Light"} for n, h in names_hues]


def dstr(d):
    return d.strftime("%Y-%m-%d 00:00")


# --------------------------------------------------------------------------- schema
DEPTS = ["研发", "产品", "设计", "测试", "运营"]
DEPT_OPTS = opt(("研发", "Blue"), ("产品", "Purple"), ("设计", "Carmine"), ("测试", "Orange"), ("运营", "Green"))
ROLES = [
    ("前端工程师", "Blue"), ("后端工程师", "Wathet"), ("移动端工程师", "Turquoise"), ("架构师", "Purple"),
    ("技术经理", "Carmine"), ("产品经理", "Orange"), ("产品总监", "Red"), ("数据分析师", "Lime"),
    ("交互设计师", "Yellow"), ("视觉设计师", "Green"), ("设计负责人", "Carmine"), ("测试工程师", "Gray"),
    ("测试开发", "Wathet"), ("测试负责人", "Purple"), ("运营专员", "Lime"), ("内容运营", "Yellow"), ("运营经理", "Red"),
]
LEVELS = ["初级", "中级", "高级", "资深", "专家"]
STAGES = ["规划", "设计", "开发", "测试", "上线", "已结项"]
PRIORITIES = ["P0", "P1", "P2", "P3"]
PRIO_OPTS = opt(("P0", "Red"), ("P1", "Orange"), ("P2", "Blue"), ("P3", "Gray"))
TASK_TYPES = ["需求", "缺陷", "优化", "文档"]
TASK_STATUSES = ["待开始", "进行中", "待验收", "已完成", "已取消"]
MS_TYPES = ["需求评审", "设计评审", "开发提测", "上线发布"]
MS_STATUSES = ["未开始", "进行中", "已达成", "已延期"]
TAGS = [("前端", "Blue"), ("后端", "Wathet"), ("移动端", "Turquoise"), ("接口", "Purple"), ("性能", "Orange"),
        ("安全", "Red"), ("体验", "Yellow"), ("数据", "Lime"), ("技术债", "Gray"), ("线上问题", "Carmine")]

MEMBER_FIELDS = [
    {"type": "text", "name": "姓名"},
    {"type": "text", "name": "工号"},
    {"type": "select", "name": "部门", "multiple": False, "options": DEPT_OPTS},
    {"type": "select", "name": "角色", "multiple": False, "options": opt(*ROLES)},
    {"type": "select", "name": "职级", "multiple": False,
     "options": opt(("初级", "Lime"), ("中级", "Green"), ("高级", "Blue"), ("资深", "Purple"), ("专家", "Carmine"))},
    {"type": "datetime", "name": "入职日期", "style": {"format": "yyyy-MM-dd"}},
]

PROJECT_FIELDS = [
    {"type": "text", "name": "项目名称"},
    {"type": "text", "name": "项目编号"},
    {"type": "link", "name": "负责人", "link_table": "成员"},
    {"type": "select", "name": "所属部门", "multiple": False, "options": DEPT_OPTS},
    {"type": "select", "name": "阶段", "multiple": False,
     "options": opt(("规划", "Gray"), ("设计", "Purple"), ("开发", "Blue"), ("测试", "Orange"),
                    ("上线", "Green"), ("已结项", "Wathet"))},
    {"type": "select", "name": "健康度", "multiple": False,
     "options": opt(("正常", "Green"), ("有风险", "Yellow"), ("已延期", "Red"))},
    {"type": "select", "name": "优先级", "multiple": False, "options": PRIO_OPTS},
    {"type": "datetime", "name": "开始日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "datetime", "name": "计划结束日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "datetime", "name": "上线日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "number", "name": "预算", "style": {"type": "currency", "precision": 0, "currency_code": "CNY"}},
    {"type": "number", "name": "进度", "style": {"type": "progress", "percentage": True, "color": "Blue"}},
]

TASK_FIELDS = [
    {"type": "text", "name": "任务标题"},
    {"type": "text", "name": "任务编号"},
    {"type": "link", "name": "所属项目", "link_table": "项目"},
    {"type": "link", "name": "负责人", "link_table": "成员"},
    {"type": "select", "name": "负责部门", "multiple": False, "options": DEPT_OPTS,
     "description": "负责人所在部门（建任务时带出，便于按部门统计）"},
    {"type": "select", "name": "类型", "multiple": False,
     "options": opt(("需求", "Blue"), ("缺陷", "Red"), ("优化", "Green"), ("文档", "Gray"))},
    {"type": "select", "name": "优先级", "multiple": False, "options": PRIO_OPTS},
    {"type": "select", "name": "状态", "multiple": False,
     "options": opt(("待开始", "Gray"), ("进行中", "Blue"), ("待验收", "Orange"), ("已完成", "Green"), ("已取消", "Red"))},
    {"type": "datetime", "name": "创建日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "datetime", "name": "计划截止", "style": {"format": "yyyy-MM-dd"}},
    {"type": "datetime", "name": "实际完成日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "number", "name": "预估工时", "style": {"type": "plain", "precision": 1}},
    {"type": "number", "name": "实际工时", "style": {"type": "plain", "precision": 1}},
    {"type": "select", "name": "标签", "multiple": True, "options": opt(*TAGS)},
]

MILESTONE_FIELDS = [
    {"type": "text", "name": "名称"},
    {"type": "link", "name": "所属项目", "link_table": "项目"},
    {"type": "select", "name": "类型", "multiple": False,
     "options": opt(("需求评审", "Purple"), ("设计评审", "Carmine"), ("开发提测", "Blue"), ("上线发布", "Green"))},
    {"type": "datetime", "name": "计划日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "datetime", "name": "实际完成日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "select", "name": "状态", "multiple": False,
     "options": opt(("未开始", "Gray"), ("进行中", "Blue"), ("已达成", "Green"), ("已延期", "Red"))},
]

TABLES = [
    ("成员", MEMBER_FIELDS),
    ("项目", PROJECT_FIELDS),
    ("任务", TASK_FIELDS),
    ("里程碑", MILESTONE_FIELDS),
]

# 数据写完后再建（避免逐批写入时反复重算）；未完成的记 0，看板统计时只取已完成 / 已达成
FORMULAS = {
    "任务": [
        {"type": "formula", "name": "交付天数",
         "expression": "IF(ISBLANK([实际完成日期]), 0, DAYS([实际完成日期], [创建日期]))"},
    ],
    "里程碑": [
        {"type": "formula", "name": "延期天数",
         "expression": "IF(ISBLANK([实际完成日期]), 0, DAYS([实际完成日期], [计划日期]))"},
    ],
}

# --------------------------------------------------------------------------- catalogs
SURNAMES = list("王李张刘陈杨黄赵吴周徐孙马朱胡郭何林罗高郑梁谢宋唐许韩冯邓曹彭曾萧田董潘袁蔡蒋余叶程苏魏")
GIVEN = ["子涵", "雨桐", "浩然", "思远", "欣怡", "梓轩", "嘉怡", "一鸣", "晓雯", "泽宇", "诗琪", "博文", "可欣",
         "俊杰", "佳宁", "天佑", "雨萌", "子轩", "静怡", "浩宇", "婉清", "文博", "晴", "一诺", "明哲", "若曦",
         "景行", "书瑶", "宇航", "沐阳", "思彤", "承泽", "语嫣", "逸凡", "心悦", "皓轩", "梦琪", "振宇", "星辰",
         "安然", "嘉树", "知遥", "清和", "亦舒", "子墨", "南乔", "立诚", "芷若", "怀瑾", "晨曦"]

# 部门：[(角色, 人数)]
ORG = [
    ("研发", [("前端工程师", 7), ("后端工程师", 9), ("移动端工程师", 5), ("架构师", 1), ("技术经理", 2)]),
    ("产品", [("产品经理", 7), ("产品总监", 1), ("数据分析师", 1)]),
    ("设计", [("交互设计师", 3), ("视觉设计师", 4), ("设计负责人", 1)]),
    ("测试", [("测试工程师", 9), ("测试开发", 1), ("测试负责人", 1)]),
    ("运营", [("运营专员", 5), ("内容运营", 2), ("运营经理", 1)]),
]
LEAD_ROLES = {"架构师", "技术经理", "产品总监", "设计负责人", "测试负责人", "运营经理"}

# 项目：名称, 所属部门, 优先级, 阶段, 健康度, 阶段内进度参数, 模块, 团队需求(前端,后端,移动,测试,设计,运营)
#   阶段内进度参数：规划~测试 = 当前阶段已用掉计划时长的比例（>1 表示超期）；上线 = 上线后天数；已结项 = 结项后天数
PROJECTS = [
    ("星河云盘 3.0", "研发", "P0", "已结项", "正常", 12, ["文件上传", "分享链接", "回收站", "空间配额", "同步客户端"], (2, 3, 1, 2, 1, 0)),
    ("支付网关升级", "研发", "P0", "已结项", "正常", 30, ["渠道路由", "退款", "对账", "风控回调", "收银台"], (1, 3, 0, 2, 1, 0)),
    ("消息推送服务", "研发", "P2", "已结项", "正常", 48, ["推送通道", "模板管理", "送达统计", "免打扰策略"], (1, 2, 1, 1, 0, 0)),
    ("智能客服机器人", "研发", "P1", "上线", "正常", 16, ["意图识别", "知识库", "人工转接", "会话记录", "满意度评价"], (2, 2, 0, 2, 1, 1)),
    ("运营活动平台", "运营", "P1", "上线", "有风险", 9, ["活动配置", "优惠券", "抽奖", "报名表单", "活动数据"], (2, 2, 0, 1, 1, 2)),
    ("双 11 大促保障", "运营", "P0", "上线", "正常", 3, ["压测", "限流降级", "秒杀", "预案演练", "监控告警"], (1, 3, 1, 2, 0, 2)),
    ("移动端 App 5.0 改版", "研发", "P0", "测试", "有风险", 0.95, ["首页", "消息中心", "个人中心", "登录注册", "深色模式"], (1, 2, 3, 2, 2, 0)),
    ("风控引擎 2.0", "研发", "P0", "测试", "已延期", 1.55, ["规则引擎", "设备指纹", "黑名单", "实时特征", "审核后台"], (1, 3, 0, 2, 0, 0)),
    ("搜索推荐优化", "研发", "P1", "测试", "正常", 0.45, ["召回", "排序模型", "搜索建议", "AB 实验", "埋点"], (1, 2, 0, 1, 0, 0)),
    ("小程序商城", "产品", "P1", "测试", "有风险", 0.9, ["商品详情", "购物车", "下单支付", "订单列表", "售后"], (2, 2, 1, 2, 1, 1)),
    ("数据中台二期", "研发", "P1", "开发", "已延期", 1.45, ["数据同步", "指标口径", "数据血缘", "调度平台", "数据质量"], (1, 3, 0, 1, 0, 0)),
    ("会员积分体系", "产品", "P2", "开发", "正常", 0.5, ["积分规则", "积分商城", "等级权益", "积分流水"], (1, 2, 1, 1, 1, 1)),
    ("权限中心重构", "研发", "P1", "开发", "有风险", 0.92, ["角色管理", "数据权限", "审批流", "审计日志", "SSO 登录"], (1, 2, 0, 1, 1, 0)),
    ("官网全新改版", "设计", "P2", "开发", "正常", 0.35, ["首页", "产品页", "客户案例", "SEO", "多语言"], (2, 1, 0, 1, 2, 1)),
    ("Galaxy 设计系统", "设计", "P2", "开发", "正常", 0.6, ["组件库", "设计令牌", "图标库", "文档站"], (2, 0, 1, 1, 2, 0)),
    ("BI 自助报表", "产品", "P2", "设计", "正常", 0.55, ["数据集", "图表编辑器", "仪表盘", "行级权限"], (1, 2, 0, 1, 1, 0)),
    ("客户成功门户", "产品", "P3", "规划", "正常", 0.5, ["工单", "知识库", "客户健康度"], (1, 1, 0, 1, 1, 1)),
    ("性能监控平台", "研发", "P3", "规划", "正常", 0.3, ["前端监控", "APM", "告警规则", "监控大盘"], (1, 2, 0, 1, 0, 0)),
]

# 计划阶段时长（天）：规划、设计、开发、测试；上线后观察期
PHASE_DAYS = [14, 18, 42, 21]
POST_LAUNCH_DAYS = 21
SIZE = {"P0": 1.25, "P1": 1.05, "P2": 0.9, "P3": 0.8}
SLIP = {"正常": (0, 3), "有风险": (3, 8), "已延期": (8, 16)}

# 每日新建任务强度（按阶段）与类型构成
PHASE_LAMBDA = {0: 0.7, 1: 1.2, 2: 2.5, 3: 2.4, 4: 0.9, 5: 0.06}
PHASE_MIX = {
    0: [("文档", 60), ("需求", 40)],
    1: [("文档", 30), ("需求", 55), ("优化", 15)],
    2: [("需求", 58), ("优化", 20), ("缺陷", 14), ("文档", 8)],
    3: [("缺陷", 55), ("优化", 19), ("需求", 14), ("文档", 12)],
    4: [("缺陷", 62), ("优化", 22), ("需求", 8), ("文档", 8)],
    5: [("文档", 40), ("缺陷", 45), ("优化", 15)],
}
WEEKDAY_FACTOR = [1.45, 1.1, 1.0, 0.9, 0.75, 0.1, 0.06]

FEATS = ["批量操作", "导出 Excel", "按条件筛选", "消息提醒", "移动端适配", "权限控制", "操作日志", "草稿自动保存",
         "数据统计", "搜索", "多选删除", "定时任务", "二次确认", "状态流转"]
BUGS = ["偶现白屏", "数据不刷新", "分页错乱", "iOS 端闪退", "时间显示时区错误", "重复提交", "接口超时",
        "按钮点击无响应", "权限校验缺失", "导出数据缺列", "金额精度丢失", "列表排序不正确", "安卓低端机卡顿",
        "空状态展示异常", "弱网下重复请求"]
OPTS = ["接口性能优化", "首屏加载提速", "交互细节打磨", "慢查询治理", "缓存策略优化", "代码重构", "埋点补齐",
        "文案与提示优化", "日志与监控补齐", "单测覆盖率提升"]
DOCS = {0: ["PRD", "竞品分析", "需求调研"], 1: ["交互说明", "技术方案", "接口设计"], 2: ["接口文档", "技术方案"],
        3: ["测试用例", "测试报告"], 4: ["上线 checklist", "用户手册", "运维手册"], 5: ["项目复盘", "结项报告"]}


def wchoice(rng, pairs):
    total = sum(w for _, w in pairs)
    r = rng.random() * total
    for v, w in pairs:
        r -= w
        if r <= 0:
            return v
    return pairs[-1][0]


def poissonish(rng, lam):
    if lam <= 0:
        return 0
    if lam < 8:  # 小 λ 用真泊松（Knuth），避免高斯近似在低值时失真
        L, k, p = math.exp(-lam), 0, 1.0
        while True:
            p *= rng.random()
            if p <= L:
                return k
            k += 1
    return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))


def is_sprint_end(d):
    return (d - SPRINT_ANCHOR).days % 14 == 0


def next_sprint_end(d):
    k = (d - SPRINT_ANCHOR).days % 14
    return d + timedelta(days=(14 - k) % 14)


def to_weekday(d):
    if d.weekday() == 5:
        return d + timedelta(days=2)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


# --------------------------------------------------------------------------- generators
def gen_members(rng, today):
    names, used = [], set()
    pool = [s + g for s in SURNAMES for g in GIVEN]
    rng.shuffle(pool)
    for n in pool:
        if n not in used:
            used.add(n)
            names.append(n)
        if len(names) >= 60:
            break
    members, i = [], 0
    for dept, roles in ORG:
        for role, cnt in roles:
            for _ in range(cnt):
                if role in LEAD_ROLES:
                    level = wchoice(rng, [("资深", 60), ("专家", 40)])
                else:
                    level = wchoice(rng, [("初级", 16), ("中级", 40), ("高级", 30), ("资深", 12), ("专家", 2)])
                yrs = {"初级": (0, 1.5), "中级": (0.5, 3.5), "高级": (1.5, 5), "资深": (2.5, 7), "专家": (4, 8)}[level]
                join = today - timedelta(days=int(rng.uniform(*yrs) * 365) + rng.randint(0, 30))
                members.append({"name": names[i], "no": "XH%04d" % (1001 + i), "dept": dept, "role": role,
                                "level": level, "join": join, "weight": 1.0, "slow": 1.0, "projects": 0})
                i += 1
    # 3 位新同学：近 90 天入职
    for m, days in ((members[6], 40), (members[33], 70), (members[50], 20)):
        m["join"] = today - timedelta(days=days)
        m["level"] = "初级"
    # 被压垮的人：后端骨干 / 移动端骨干 / 测试骨干（任务多、交付慢）
    for idx, w, slow in ((7, 1.3, 1.5), (16, 1.5, 1.45), (45, 1.6, 1.5), (9, 1.35, 1.35)):
        members[idx]["weight"], members[idx]["slow"] = w, slow
        members[idx]["level"] = "高级" if members[idx]["level"] in ("初级", "中级") else members[idx]["level"]
    return members


def by_role(members, *roles):
    return [m for m in members if m["role"] in roles]


def gen_projects(rng, members, today):
    fe = by_role(members, "前端工程师")
    be = by_role(members, "后端工程师")
    mo = by_role(members, "移动端工程师")
    qa = by_role(members, "测试工程师", "测试开发")
    ds = by_role(members, "交互设计师", "视觉设计师")
    op = by_role(members, "运营专员", "内容运营")
    pm = by_role(members, "产品经理")
    owners = {"研发": by_role(members, "技术经理", "架构师"), "产品": pm + by_role(members, "产品总监"),
              "设计": by_role(members, "设计负责人"), "运营": by_role(members, "运营经理")}

    def pick(group, n):
        if n <= 0:
            return []
        # 已挂项目少的人优先，加权：骨干更容易被拉进来
        cands = sorted(group, key=lambda m: (m["projects"] / m["weight"], rng.random()))
        chosen = cands[:n]
        for m in chosen:
            m["projects"] += 1
        return chosen

    projects = []
    for idx, (name, dept, prio, stage, health, param, modules, need) in enumerate(PROJECTS):
        k = STAGES.index(stage)
        size = SIZE[prio] * rng.uniform(0.9, 1.1)
        dur = [max(5, int(round(d * size * rng.uniform(0.85, 1.15)))) for d in PHASE_DAYS]
        lo, hi = SLIP[health]
        # 计划里程碑日期（相对开始日）与实际累计滑期
        plan_off, acc, slip_acc = [], 0, []
        s = 0
        for d in dur:
            acc += d
            plan_off.append(acc)
            s += rng.randint(lo, hi)
            slip_acc.append(s)
        post = int(POST_LAUNCH_DAYS * rng.uniform(0.85, 1.2))
        # 反推开始日期，使「今天」恰好落在配置的阶段里
        if k <= 3:
            prev_actual = (plan_off[k - 1] + slip_acc[k - 1]) if k > 0 else 0
            into = int(round(param * dur[k]))
            start = today - timedelta(days=prev_actual + into)
        elif k == 4:
            start = today - timedelta(days=plan_off[3] + slip_acc[3] + int(param))
        else:
            start = today - timedelta(days=plan_off[3] + slip_acc[3] + post + int(param))
        planned = [start + timedelta(days=o) for o in plan_off]
        actual = [None] * 4
        for j in range(min(k, 4)):
            actual[j] = to_weekday(start + timedelta(days=plan_off[j] + slip_acc[j]))
            if actual[j] > today:
                actual[j] = today
        launch = actual[3]
        closed = launch + timedelta(days=post) if k == 5 else None
        plan_end = planned[3] + timedelta(days=POST_LAUNCH_DAYS)
        # 进度：按阶段 + 阶段内比例
        base = [0.0, 0.1, 0.25, 0.65, 0.85, 1.0][k]
        if k <= 3:
            span = [0.1, 0.15, 0.4, 0.2][k]
            progress = base + span * min(param, 0.97)
        elif k == 4:
            progress = min(0.98, 0.85 + 0.13 * min(1.0, param / post))
        else:
            progress = 1.0
        budget = int(round({"P0": rng.uniform(220, 360), "P1": rng.uniform(110, 220),
                            "P2": rng.uniform(55, 120), "P3": rng.uniform(25, 60)}[prio])) * 10000
        f, b, mb, q, d_, o = need
        team = {"fe": pick(fe, f), "be": pick(be, b), "mo": pick(mo, mb), "qa": pick(qa, q),
                "ds": pick(ds, d_), "op": pick(op, o)}
        team["pm"] = pick(pm, 1)
        if any(x in name for x in ("数据", "BI", "搜索")):
            team["pm"] += by_role(members, "数据分析师")
        if prio == "P0":
            team["qa"] += by_role(members, "测试负责人")
            team["pm"] += by_role(members, "产品总监")
        if dept == "产品":
            owner = by_role(members, "产品总监")[0] if prio == "P3" else team["pm"][0]
        else:
            owner = owners[dept][idx % len(owners[dept])]
        team["own"] = [owner]
        # 骨干「被压垮」：后端骨干挂到更多 P0/P1 项目，测试骨干挂到所有测试阶段项目
        heavy_be, heavy_qa, heavy_mo = members[7], members[45], members[16]
        if prio == "P0" and heavy_be not in team["be"]:
            team["be"].append(heavy_be)
        if k in (3, 4) and heavy_qa not in team["qa"]:
            team["qa"].append(heavy_qa)
        if name in ("移动端 App 5.0 改版", "小程序商城", "双 11 大促保障") and heavy_mo not in team["mo"]:
            team["mo"].append(heavy_mo)
        projects.append({
            "name": name, "code": "PRJ-2026-%03d" % (idx + 1), "dept": dept, "prio": prio, "stage": stage,
            "k": k, "health": health, "start": start, "planned": planned, "actual": actual, "launch": launch,
            "closed": closed, "plan_end": plan_end, "progress": round(min(progress, 1.0), 2), "budget": budget,
            "modules": modules, "team": team, "owner": owner, "size": size,
        })
    projects.sort(key=lambda p: p["start"])
    for i, p in enumerate(projects):
        p["code"] = "PRJ-2026-%03d" % (i + 1)
    return projects


def phase_on(p, d):
    """项目在某天所处阶段：0 规划 … 4 上线后观察 5 已结项；开始前返回 None。"""
    if d < p["start"]:
        return None, 0
    if p["closed"] and d >= p["closed"]:
        return 5, (d - p["closed"]).days
    for j in range(3, -1, -1):
        a = p["actual"][j]
        if a and d >= a:
            return j + 1, (d - a).days
    return 0, (d - p["start"]).days


def gen_milestones(rng, projects, today):
    out = []
    for p in projects:
        for j, mtype in enumerate(MS_TYPES):
            planned, actual = p["planned"][j], p["actual"][j]
            if actual:
                status = "已达成"
            elif planned < today:
                status = "已延期"
            elif j == p["k"] or (planned - today).days <= 10:
                status = "进行中"
            else:
                status = "未开始"
            out.append({"key": "%s-M%d" % (p["code"], j + 1), "name": "%s · %s" % (p["name"], mtype),
                        "project": p["code"], "type": mtype, "planned": planned, "actual": actual, "status": status})
    return out


def _assignee_pool(p, phase, ttype):
    t = p["team"]
    dev = t["fe"] + t["be"] + t["mo"]
    ops_heavy = p["dept"] == "运营"
    if ttype == "文档":
        groups = {0: [(t["pm"], 55), (t["own"], 20), (dev, 25)], 1: [(t["pm"], 35), (t["ds"], 30), (t["own"], 10), (dev, 25)],
                  2: [(dev, 60), (t["pm"], 25), (t["own"], 15)], 3: [(t["qa"], 80), (dev, 20)],
                  4: [(t["op"], 45), (t["pm"], 25), (t["qa"], 10), (dev, 20)], 5: [(t["pm"], 45), (t["own"], 25), (dev, 30)]}[phase]
    elif ttype == "缺陷":
        groups = [(dev, 90), (t["ds"], 3), (t["qa"], 4), (t["op"], 3)]
    elif ttype == "优化":
        groups = [(dev, 62), (t["ds"], 10), (t["qa"], 16), (t["op"], 12 if not ops_heavy else 25)]
    else:  # 需求
        groups = {0: [(t["pm"], 60), (t["own"], 15), (dev, 25)],
                  1: [(t["ds"], 50), (t["pm"], 25), (dev, 25)]}.get(
            phase, [(dev, 78), (t["ds"], 6), (t["op"], 6 if not ops_heavy else 30), (t["pm"], 6), (t["qa"], 4)])
    return [(g, w) for g, w in groups if g]


def _tags(rng, p, ttype, member, phase, module):
    tags = []
    role_tag = {"前端工程师": "前端", "后端工程师": "后端", "移动端工程师": "移动端"}.get(member["role"])
    if role_tag:
        tags.append(role_tag)
    if ttype == "缺陷" and phase in (4, 5):
        tags.append("线上问题")
    if any(x in module for x in ("权限", "风控", "黑名单", "设备指纹", "SSO", "审计")) and rng.random() < 0.6:
        tags.append("安全")
    if any(x in module for x in ("数据", "指标", "埋点", "统计", "报表", "血缘")) and rng.random() < 0.6:
        tags.append("数据")
    if ttype == "优化":
        tags.append(wchoice(rng, [("性能", 40), ("体验", 35), ("技术债", 25)]))
    elif ttype == "需求" and role_tag in ("后端",) and rng.random() < 0.4:
        tags.append("接口")
    elif ttype == "需求" and member["dept"] == "设计":
        tags.append("体验")
    out = []
    for x in tags:
        if x not in out:
            out.append(x)
    return out[:3]


def _title(rng, p, ttype, phase, module):
    if ttype == "需求":
        return "【%s】支持%s" % (module, rng.choice(FEATS))
    if ttype == "缺陷":
        return "【%s】%s" % (module, rng.choice(BUGS))
    if ttype == "优化":
        return "【%s】%s" % (module, rng.choice(OPTS))
    return "【%s】%s" % (module, rng.choice(DOCS[phase]))


EST = {"需求": (14.0, 0.55, 4, 60), "缺陷": (4.0, 0.6, 1, 16), "优化": (8.0, 0.5, 2, 32), "文档": (4.0, 0.45, 1, 16)}
LEAD = {"需求": 6.0, "缺陷": 2.6, "优化": 4.5, "文档": 3.5}
PRIO_LEAD = {"P0": 0.4, "P1": 0.7, "P2": 1.0, "P3": 1.45}
BUG_DUE = {"P0": 1, "P1": 3, "P2": 7, "P3": 14}
RATIO = {"需求": (0.10, 0.18), "缺陷": (0.22, 0.48), "优化": (0.05, 0.16), "文档": (0.0, 0.12)}  # ln(实际/预估) ~ N


def half(x):
    return max(0.5, round(x * 2) / 2.0)


def gen_tasks(rng, projects, today):
    tasks, seq = [], 0
    day0 = today - timedelta(days=DAYS - 1)
    for back in range(DAYS - 1, -1, -1):
        day = today - timedelta(days=back)
        wk = WEEKDAY_FACTOR[day.weekday()]
        sprint_start = day.weekday() == 0 and is_sprint_end(day - timedelta(days=3))
        for p in projects:
            phase, since = phase_on(p, day)
            if phase is None:
                continue
            lam = PHASE_LAMBDA[phase]
            mix = PHASE_MIX[phase]
            if phase == 4:  # 上线后缺陷爆发，按天衰减
                spike = 3.6 * math.exp(-since / 5.0)
                lam += spike
                mix = [("缺陷", 62 + 30 * spike), ("优化", 22), ("需求", 8), ("文档", 8)]
            if phase == 3 and p["health"] != "正常":
                lam *= 1.15
            lam *= p["size"] * wk * TASK_SCALE
            if sprint_start and phase in (1, 2, 3):
                lam *= 1.5
            for _ in range(poissonish(rng, lam)):
                seq += 1
                tasks.append(_make_task(rng, p, phase, since, day, today, seq, mix))
    return tasks, day0


def _make_task(rng, p, phase, since, created, today, seq, mix):
    ttype = wchoice(rng, mix)
    # 优先级：上线后的缺陷更急；项目优先级抬升
    if ttype == "缺陷" and phase in (4, 5):
        pr = [("P0", 14), ("P1", 36), ("P2", 36), ("P3", 14)]
    elif ttype == "缺陷":
        pr = [("P0", 6), ("P1", 30), ("P2", 46), ("P3", 18)]
    else:
        pr = [("P0", 4), ("P1", 24), ("P2", 50), ("P3", 22)]
    if p["prio"] == "P0":
        pr = [(k, w * (1.6 if k in ("P0", "P1") else 1.0)) for k, w in pr]
    prio = wchoice(rng, pr)
    group = wchoice(rng, _assignee_pool(p, phase, ttype))
    group = [m for m in group if m["join"] <= created] or group  # 新同学入职前不派活
    member = wchoice(rng, [(m, m["weight"]) for m in group])
    module = rng.choice(p["modules"])
    mu, sg, lo, hi = EST[ttype]
    est = half(min(hi, max(lo, mu * math.exp(rng.gauss(0, sg)))))

    # 计划截止
    if ttype == "缺陷":
        due = created + timedelta(days=BUG_DUE[prio])
    elif ttype == "文档":
        due = created + timedelta(days=rng.randint(4, 9))
    else:
        min_days = max(2, int(est / {"P0": 7, "P1": 5, "P2": 4, "P3": 3}[prio]))
        due = next_sprint_end(created + timedelta(days=min_days))
        if prio == "P0":
            due = min(due, created + timedelta(days=max(2, min_days)))
    due = to_weekday(due) if ttype != "缺陷" else due

    # 交付周期：类型 × 优先级 × 个人负载 × 项目健康；少量任务卡住
    lead = LEAD[ttype] * PRIO_LEAD[prio] * member["slow"] * math.exp(rng.gauss(0, 0.5))
    lead *= {"正常": 1.0, "有风险": 1.2, "已延期": 1.45}[p["health"]]
    # 卡住 / 被降级搁置的任务：低优先级、风险项目、忙不过来的人更容易
    stall_p = {"P0": 0.02, "P1": 0.09, "P2": 0.17, "P3": 0.32}[prio]
    stall_p += (0.08 if p["health"] != "正常" else 0) + (0.08 if member["slow"] > 1.3 else 0)
    if ttype == "缺陷":
        stall_p *= 0.5
    stalled = rng.random() < stall_p
    if stalled:
        lead *= rng.uniform(4, 12)
    done = created + timedelta(days=max(0, int(round(lead))))
    # 迭代末集中验收：需求 / 优化 自然完成日后 6 天内若有迭代结束日，大概率顺延到那天
    if ttype in ("需求", "优化"):
        se = next_sprint_end(done)
        if (se - done).days <= 6 and rng.random() < 0.7:
            done = se - timedelta(days=rng.choice([0, 0, 0, 1]))
    if done.weekday() == 5 and rng.random() < 0.5:
        done -= timedelta(days=1)  # 周六的活大多赶在周五收尾
    if done.weekday() >= 5 and rng.random() < 0.85:
        done = to_weekday(done)

    cancel_p = {0: 0.08, 1: 0.07}.get(phase, 0.025)
    ln_mu, ln_sg = RATIO[ttype]
    ratio = math.exp(rng.gauss(ln_mu, ln_sg))
    actual_done, act = None, None
    if rng.random() < cancel_p:
        status = "已取消"
        act = half(est * rng.uniform(0.1, 0.4)) if rng.random() < 0.4 else None
    elif done <= today:
        status, actual_done = "已完成", done
        act = half(est * ratio)
    else:
        total = max(1.0, (done - created).days)
        elapsed = (today - created).days
        frac = elapsed / total
        if frac < 0.2 or elapsed == 0 or (stalled and rng.random() < 0.35):
            status = "待开始"
        elif (done - today).days <= 2 and ttype in ("需求", "优化") and rng.random() < 0.65:
            status = "待验收"
            act = half(est * ratio * rng.uniform(0.85, 1.0))
        else:
            status = "进行中"
            act = half(est * ratio * min(0.95, max(0.1, frac)))
    return {
        "no": "XH-T%05d" % seq, "title": _title(rng, p, ttype, phase, module), "project": p["code"],
        "member": member["no"], "dept": member["dept"], "type": ttype, "prio": prio, "status": status,
        "created": created, "due": due, "done": actual_done, "est": est, "act": act,
        "tags": _tags(rng, p, ttype, member, phase, module),
    }


def _project_health(projects, tasks, milestones, today):
    """健康度以配置为主；计划结束已过还没上线的一律已延期。"""
    for p in projects:
        if p["k"] < 4 and p["plan_end"] < today:
            p["health"] = "已延期"


def generate_all(now=None):
    now = now or now_local()
    today = now.date() if isinstance(now, datetime) else now
    rng = random.Random(SEED)
    members = gen_members(rng, today)
    projects = gen_projects(rng, members, today)
    milestones = gen_milestones(rng, projects, today)
    tasks, _ = gen_tasks(rng, projects, today)
    _project_health(projects, tasks, milestones, today)
    return {"members": members, "projects": projects, "milestones": milestones, "tasks": tasks, "today": today}


# --------------------------------------------------------------------------- rows (Base CellValue)
def generate(now=None):
    d = generate_all(now)
    members = [{"$key": m["no"], "姓名": m["name"], "工号": m["no"], "部门": [m["dept"]], "角色": [m["role"]],
                "职级": [m["level"]], "入职日期": dstr(m["join"])} for m in d["members"]]
    projects = []
    for p in d["projects"]:
        row = {"$key": p["code"], "项目名称": p["name"], "项目编号": p["code"],
               "负责人": {"$link": "成员", "keys": [p["owner"]["no"]]}, "所属部门": [p["dept"]],
               "阶段": [p["stage"]], "健康度": [p["health"]], "优先级": [p["prio"]],
               "开始日期": dstr(p["start"]), "计划结束日期": dstr(p["plan_end"]),
               "预算": p["budget"], "进度": p["progress"]}
        if p["launch"]:
            row["上线日期"] = dstr(p["launch"])
        projects.append(row)
    tasks = []
    for t in d["tasks"]:
        row = {"$key": t["no"], "任务标题": t["title"], "任务编号": t["no"],
               "所属项目": {"$link": "项目", "keys": [t["project"]]},
               "负责人": {"$link": "成员", "keys": [t["member"]]}, "负责部门": [t["dept"]],
               "类型": [t["type"]], "优先级": [t["prio"]], "状态": [t["status"]],
               "创建日期": dstr(t["created"]), "计划截止": dstr(t["due"]), "预估工时": t["est"]}
        if t["done"]:
            row["实际完成日期"] = dstr(t["done"])
        if t["act"] is not None:
            row["实际工时"] = t["act"]
        if t["tags"]:
            row["标签"] = t["tags"]
        tasks.append(row)
    milestones = []
    for m in d["milestones"]:
        row = {"$key": m["key"], "名称": m["name"], "所属项目": {"$link": "项目", "keys": [m["project"]]},
               "类型": [m["type"]], "计划日期": dstr(m["planned"]), "状态": [m["status"]]}
        if m["actual"]:
            row["实际完成日期"] = dstr(m["actual"])
        milestones.append(row)
    return {"成员": members, "项目": projects, "任务": tasks, "里程碑": milestones}
