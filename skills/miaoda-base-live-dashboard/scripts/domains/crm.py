"""「云帆软件」B2B SaaS 销售 CRM 演示数据（领域包 crm，供 seed_base.py 使用）。

表（依赖顺序，关联全部单向）：销售人员 → 客户档案 → 商机 → 跟进记录 → 合同回款
注意：表名刻意不与关联字段同名（关联字段叫「客户」「销售」）。公式里 [客户].[行业] 遇到同名表时会解析成
「整张表」而不是「本行关联的记录」，查出来是全表行业拼接——已实测踩坑。
时间：Asia/Shanghai 本地时间，覆盖最近 120 天直到此刻；固定随机种子，同一天重复运行结果一致。

造数规则（看板上应能看出来的业务规律）：
- 漏斗逐级流失：线索 → 需求确认 → 方案报价 → 商务谈判 → 赢单，每一级都有输单，输单原因随阶段变化
  （前期多「无决策人 / 需求变化」，后期多「价格 / 竞品」）；
- 来源：转介绍、合作伙伴转化最好，电话外呼最差；行业：互联网 / 物流赢单率高，金融 / 医疗低且回款慢；
- 大客户部人少、单大、周期长；续约商机赢率高、周期短；新入职销售赢率偏低；
- 季度末（9 月下旬）签约冲刺、月末小高峰；周末与国庆假期活动明显减少；9 月中旬展会带来一波线索；
- 跟进节奏因人而异：几位销售习惯拖延，产生「下次跟进日期已过、仍未跟进」的超期客户；
- 回款滞后签约 15–60 天（金融 / 医疗 / 大客户更慢），部分合同分两期回款，少量合同迟迟未回款。

字段口径：
- 商机「结单日期」= 赢单或输单的关闭日期（赢单率按它统计）；在途商机为空；
- 跟进记录「下次跟进状态」：待跟进 = 计划的下次跟进还没发生（日期已过即超期）；已完成 = 之后已有新跟进；
  无需跟进 = 客户已流失不再跟进。
"""
import random
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

TZ = "Asia/Shanghai"
SEED = 20261104
WINDOW_DAYS = 120

BASE_NAME = "云帆软件 · 客户管理（CRM）"


def now_local():
    if ZoneInfo:
        return datetime.now(ZoneInfo(TZ)).replace(tzinfo=None)
    return datetime.utcnow() + timedelta(hours=8)


def opt(*names_hues):
    return [{"name": n, "hue": h, "lightness": "Light"} for n, h in names_hues]


CNY0 = {"type": "currency", "precision": 0, "currency_code": "CNY"}
DATE_STYLE = {"format": "yyyy-MM-dd"}

# --------------------------------------------------------------------------- catalogs
TEAM_CITIES = [
    ("华东一组", ["上海", "杭州"]),
    ("华东二组", ["南京", "苏州", "宁波", "合肥"]),
    ("华南组", ["深圳", "广州", "东莞", "厦门", "长沙"]),
    ("华北组", ["北京", "天津", "济南", "青岛", "郑州"]),
    ("大客户部", ["上海", "北京", "深圳", "广州", "杭州"]),
]
CITY_HUES = [("上海", "Blue"), ("杭州", "Green"), ("南京", "Turquoise"), ("苏州", "Wathet"), ("宁波", "Lime"),
             ("合肥", "Yellow"), ("深圳", "Purple"), ("广州", "Orange"), ("东莞", "Carmine"), ("厦门", "Wathet"),
             ("长沙", "Red"), ("北京", "Red"), ("天津", "Gray"), ("济南", "Yellow"), ("青岛", "Blue"), ("郑州", "Orange")]
INDUSTRIES = ["制造", "零售", "金融", "教育", "医疗", "互联网", "物流"]
SIZES = ["50人以下", "50-200", "200-1000", "1000以上"]
SOURCES = ["官网", "展会", "转介绍", "电话外呼", "合作伙伴", "内容营销"]
TIERS = ["A", "B", "C", "D"]
STAGES = ["线索", "需求确认", "方案报价", "商务谈判", "赢单", "输单"]
OPEN_STAGES = STAGES[:4]
PRODUCTS = ["云帆CRM", "云帆协同", "云帆HR", "云帆BI", "云帆客服"]
LOST_REASONS = ["价格", "竞品", "预算冻结", "需求变化", "无决策人"]
METHODS = ["电话", "拜访", "微信", "邮件", "线上会议"]
OUTCOMES = ["有进展", "待推进", "无响应"]

# --------------------------------------------------------------------------- schema
SALES_FIELDS = [
    {"type": "text", "name": "姓名"},
    {"type": "text", "name": "工号"},
    {"type": "select", "name": "团队", "multiple": False,
     "options": opt(("华东一组", "Blue"), ("华东二组", "Wathet"), ("华南组", "Purple"), ("华北组", "Red"),
                    ("大客户部", "Carmine"))},
    {"type": "select", "name": "职级", "multiple": False,
     "options": opt(("销售专员", "Gray"), ("高级销售", "Blue"), ("销售主管", "Purple"), ("大客户经理", "Carmine"))},
    {"type": "datetime", "name": "入职日期", "style": DATE_STYLE},
    {"type": "number", "name": "季度目标", "style": CNY0},
    {"type": "text", "name": "手机号", "style": {"type": "phone"}},
]

CUSTOMER_FIELDS = [
    {"type": "text", "name": "客户名称"},
    {"type": "select", "name": "行业", "multiple": False,
     "options": opt(("制造", "Orange"), ("零售", "Yellow"), ("金融", "Blue"), ("教育", "Green"), ("医疗", "Turquoise"),
                    ("互联网", "Purple"), ("物流", "Lime"))},
    {"type": "select", "name": "规模", "multiple": False,
     "options": opt(("50人以下", "Gray"), ("50-200", "Wathet"), ("200-1000", "Blue"), ("1000以上", "Purple"))},
    {"type": "select", "name": "来源", "multiple": False,
     "options": opt(("官网", "Blue"), ("展会", "Orange"), ("转介绍", "Green"), ("电话外呼", "Gray"),
                    ("合作伙伴", "Purple"), ("内容营销", "Turquoise"))},
    {"type": "select", "name": "客户等级", "multiple": False,
     "options": opt(("A", "Red"), ("B", "Orange"), ("C", "Blue"), ("D", "Gray"))},
    {"type": "select", "name": "客户状态", "multiple": False,
     "options": opt(("潜在客户", "Gray"), ("跟进中", "Blue"), ("已成交", "Green"), ("已流失", "Red"))},
    {"type": "link", "name": "负责销售", "link_table": "销售人员"},
    {"type": "select", "name": "所在城市", "multiple": False, "options": opt(*CITY_HUES)},
    {"type": "datetime", "name": "创建日期", "style": DATE_STYLE},
    {"type": "text", "name": "联系人"},
    {"type": "select", "name": "联系人职务", "multiple": False,
     "options": opt(("总经理", "Carmine"), ("CIO", "Purple"), ("IT负责人", "Blue"), ("销售副总", "Orange"),
                    ("HR负责人", "Green"), ("采购经理", "Gray"))},
]

DEAL_FIELDS = [
    {"type": "text", "name": "商机名称"},
    {"type": "link", "name": "客户", "link_table": "客户档案"},
    {"type": "link", "name": "负责销售", "link_table": "销售人员"},
    {"type": "select", "name": "产品线", "multiple": False,
     "options": opt(("云帆CRM", "Blue"), ("云帆协同", "Green"), ("云帆HR", "Orange"), ("云帆BI", "Purple"),
                    ("云帆客服", "Turquoise"))},
    {"type": "select", "name": "商机类型", "multiple": False,
     "options": opt(("新购", "Blue"), ("增购", "Purple"), ("续约", "Green"))},
    {"type": "select", "name": "阶段", "multiple": False,
     "options": opt(("线索", "Gray"), ("需求确认", "Wathet"), ("方案报价", "Blue"), ("商务谈判", "Purple"),
                    ("赢单", "Green"), ("输单", "Red"))},
    {"type": "number", "name": "预计金额", "style": CNY0},
    {"type": "number", "name": "赢率", "style": {"type": "progress", "percentage": True, "color": "Blue"}},
    {"type": "datetime", "name": "创建日期", "style": DATE_STYLE},
    {"type": "datetime", "name": "预计成交日期", "style": DATE_STYLE},
    {"type": "datetime", "name": "结单日期", "style": DATE_STYLE},
    {"type": "select", "name": "输单原因", "multiple": False,
     "options": opt(("价格", "Orange"), ("竞品", "Red"), ("预算冻结", "Gray"), ("需求变化", "Yellow"),
                    ("无决策人", "Purple"))},
]

FOLLOWUP_FIELDS = [
    {"type": "text", "name": "标题"},
    {"type": "link", "name": "客户", "link_table": "客户档案"},
    {"type": "link", "name": "销售", "link_table": "销售人员"},
    {"type": "select", "name": "方式", "multiple": False,
     "options": opt(("电话", "Blue"), ("拜访", "Carmine"), ("微信", "Green"), ("邮件", "Gray"), ("线上会议", "Purple"))},
    {"type": "datetime", "name": "跟进时间", "style": {"format": "yyyy-MM-dd HH:mm"}},
    {"type": "datetime", "name": "下次跟进日期", "style": DATE_STYLE},
    {"type": "select", "name": "下次跟进状态", "multiple": False,
     "options": opt(("待跟进", "Orange"), ("已完成", "Green"), ("无需跟进", "Gray"))},
    {"type": "select", "name": "跟进结果", "multiple": False,
     "options": opt(("有进展", "Green"), ("待推进", "Yellow"), ("无响应", "Red"))},
    {"type": "text", "name": "跟进纪要"},
]

CONTRACT_FIELDS = [
    {"type": "text", "name": "合同编号"},
    {"type": "link", "name": "客户", "link_table": "客户档案"},
    {"type": "link", "name": "商机", "link_table": "商机"},
    {"type": "link", "name": "销售", "link_table": "销售人员"},
    {"type": "number", "name": "合同金额", "style": CNY0},
    {"type": "datetime", "name": "签约日期", "style": DATE_STYLE},
    {"type": "select", "name": "付款方式", "multiple": False,
     "options": opt(("一次性付清", "Blue"), ("分两期", "Purple"))},
    {"type": "number", "name": "已回款金额", "style": CNY0},
    {"type": "datetime", "name": "最近回款日期", "style": DATE_STYLE},
    {"type": "select", "name": "回款状态", "multiple": False,
     "options": opt(("未回款", "Red"), ("部分回款", "Orange"), ("已回清", "Green"))},
]

TABLES = [
    ("销售人员", SALES_FIELDS),
    ("客户档案", CUSTOMER_FIELDS),
    ("商机", DEAL_FIELDS),
    ("跟进记录", FOLLOWUP_FIELDS),
    ("合同回款", CONTRACT_FIELDS),
]

# 数据写完后再建公式：把关联表的字段「带」到本表，看板才能按行业 / 团队拆分（引擎维度只能用本表字段）
FORMULAS = {
    "商机": [
        {"type": "formula", "name": "客户行业", "expression": "[客户].[行业].ARRAYJOIN(\",\")"},
        {"type": "formula", "name": "加权金额", "expression": "ROUND([预计金额]*[赢率], 0)"},
    ],
    "跟进记录": [
        {"type": "formula", "name": "所属团队", "expression": "[销售].[团队].ARRAYJOIN(\",\")"},
    ],
    "合同回款": [
        {"type": "formula", "name": "待回款金额", "expression": "[合同金额]-[已回款金额]"},
        {"type": "formula", "name": "所属团队", "expression": "[销售].[团队].ARRAYJOIN(\",\")"},
    ],
}

# --------------------------------------------------------------------------- people
# (姓名, 团队, 职级, 入职：日期字符串或「距今天数」, 赢单能力, 跟进习惯 high/mid/low)
SALES_ROSTER = [
    ("林予舟", "华东一组", "销售主管", "2020-03-16", 1.04, "high"),
    ("周书瑶", "华东一组", "高级销售", "2021-07-05", 1.13, "high"),
    ("王启航", "华东一组", "高级销售", "2022-02-21", 1.02, "mid"),
    ("赵思琪", "华东一组", "销售专员", "2023-09-04", 0.98, "mid"),
    ("孙浩辰", "华东一组", "销售专员", "2024-05-13", 0.95, "low"),
    ("李沐阳", "华东一组", "销售专员", 86, 0.86, "mid"),
    ("吴雨桐", "华东二组", "销售主管", "2019-11-11", 1.05, "high"),
    ("郑子墨", "华东二组", "高级销售", "2021-03-01", 1.03, "mid"),
    ("钱若溪", "华东二组", "高级销售", "2022-08-15", 1.06, "high"),
    ("冯一鸣", "华东二组", "销售专员", "2024-02-26", 0.97, "mid"),
    ("何清扬", "华东二组", "销售专员", "2025-04-07", 0.93, "low"),
    ("沈雨萱", "华南组", "销售主管", "2020-06-01", 1.03, "high"),
    ("韩博然", "华南组", "高级销售", "2021-10-18", 1.11, "high"),
    ("唐依然", "华南组", "高级销售", "2023-03-13", 1.00, "mid"),
    ("高子骞", "华南组", "销售专员", "2024-09-02", 0.96, "low"),
    ("邓佳音", "华南组", "销售专员", 47, 0.85, "mid"),
    ("彭晓岚", "华北组", "销售主管", "2019-08-19", 1.04, "high"),
    ("萧逸川", "华北组", "高级销售", "2020-12-07", 1.02, "mid"),
    ("田书恒", "华北组", "高级销售", "2022-05-09", 1.05, "high"),
    ("蒋思远", "华北组", "销售专员", "2023-11-20", 0.92, "low"),
    ("罗雅琪", "华北组", "销售专员", "2025-06-16", 0.97, "mid"),
    ("梁晨曦", "大客户部", "销售主管", "2018-10-08", 1.06, "high"),
    ("宋明轩", "大客户部", "大客户经理", "2020-04-20", 1.10, "high"),
    ("夏语冰", "大客户部", "大客户经理", "2021-09-13", 1.02, "mid"),
    ("程知远", "大客户部", "大客户经理", "2023-06-26", 0.97, "mid"),
]
FORGET = {"high": 0.01, "mid": 0.03, "low": 0.09}  # 每次跟进后「忘了再跟」的概率 → 超期客户
SLIP = {  # 计划跟进日 → 实际跟进日的拖延天数
    "high": [-1, 0, 0, 0, 0, 1, 1, 2],
    "mid": [0, 0, 1, 1, 2, 3, 5, 9],
    "low": [0, 2, 4, 7, 10, 15, 21, 30],
}
REP_WEIGHT = {"销售主管": 0.55, "高级销售": 1.25, "销售专员": 1.0, "大客户经理": 1.0}

SURNAMES = list("王李张刘陈杨黄赵吴周徐孙马朱胡郭何林罗高郑梁谢宋唐许韩冯邓曹彭曾萧田董潘袁蔡蒋余杜叶程苏魏吕丁沈")
GIVEN = ["伟", "芳", "敏", "静", "磊", "军", "洋", "勇", "艳", "杰", "娟", "涛", "明", "超", "霞", "平", "刚", "桂英",
         "建华", "晓东", "海燕", "志强", "文静", "国庆", "春梅", "立新", "建军", "雪梅", "宏伟", "丽娜", "子豪", "思远",
         "佳琪", "梦瑶", "俊杰", "雨涵", "浩然", "欣怡", "文博", "诗雨"]

NAME_A = list("恒博拓锦鸿睿澜沐晟泓沛誉卓朗峻昊铭宸熙衡")
NAME_B = list("岳远川程泰达新智源邦润诚航峰宁辰益盛合信")
NAME_BLOCK = {"恒泰", "恒信", "鸿达", "朗新", "恒盛", "锦程", "恒源", "鸿源", "博信", "宸信", "恒达", "鸿信"}
BIZ = {
    "制造": ["精密制造", "机械", "新材料", "智能装备", "电子"],
    "零售": ["优选商贸", "连锁超市", "生活百货", "鲜品零售"],
    "金融": ["融资租赁", "财富管理", "保险代理", "商业保理"],
    "教育": ["教育科技", "职业培训", "文化教育", "学堂"],
    "医疗": ["医疗器械", "健康管理", "医药连锁", "口腔医院"],
    "互联网": ["网络科技", "信息技术", "数字科技", "软件"],
    "物流": ["供应链", "物流", "仓储", "冷链运输"],
}

# 漏斗：每一级推进概率（其余为该级输单）与停留天数
P_ADV = [0.71, 0.77, 0.75, 0.73]
P_ADV_RENEW = [0.96, 0.95, 0.93, 0.90]
DWELL = [(7, 24), (7, 20), (6, 18), (5, 16)]
STAGE_PROB = [0.10, 0.25, 0.50, 0.75]
SOURCE_MOD = {"转介绍": 1.16, "合作伙伴": 1.08, "展会": 1.0, "官网": 1.0, "内容营销": 0.97, "电话外呼": 0.86}
INDUSTRY_MOD = {"互联网": 1.10, "物流": 1.07, "零售": 1.02, "制造": 0.98, "教育": 0.95, "医疗": 0.90, "金融": 0.87}
TIER_MOD = {"A": 1.06, "B": 1.02, "C": 0.98, "D": 0.90}
LOST_BY_STAGE = [
    [("无决策人", 35), ("需求变化", 35), ("预算冻结", 30)],
    [("需求变化", 35), ("预算冻结", 30), ("无决策人", 20), ("价格", 15)],
    [("价格", 45), ("竞品", 35), ("预算冻结", 12), ("需求变化", 8)],
    [("竞品", 40), ("价格", 35), ("预算冻结", 20), ("无决策人", 5)],
]
LOST_INDUSTRY_BIAS = {"制造": "价格", "零售": "价格", "金融": "预算冻结", "医疗": "预算冻结", "互联网": "竞品",
                      "教育": "预算冻结", "物流": "竞品"}
AMOUNT_BY_SIZE = {"50人以下": (30000, 80000), "50-200": (60000, 180000), "200-1000": (150000, 500000),
                  "1000以上": (400000, 1500000)}
PRODUCT_MOD = {"云帆CRM": 1.0, "云帆协同": 0.8, "云帆HR": 0.7, "云帆BI": 1.3, "云帆客服": 0.9}
TYPE_MOD = {"新购": 1.0, "增购": 0.45, "续约": 0.85}

TOPICS = {
    "潜在": ["初次电话沟通", "发送产品资料", "邀约产品演示", "了解数字化现状"],
    "线索": ["需求摸底", "初次拜访", "发送行业案例", "确认对接人"],
    "需求确认": ["需求调研", "产品演示", "梳理业务流程", "确认采购预算"],
    "方案报价": ["方案讲解", "报价沟通", "POC 试用反馈", "技术答疑"],
    "商务谈判": ["价格谈判", "合同条款确认", "采购流程推进", "法务审核跟进"],
    "已成交": ["上线回访", "使用情况回访", "培训安排", "续费沟通", "增购需求沟通"],
    "流失": ["挽回沟通", "了解输单原因"],
}
NOTES = {
    "有进展": ["客户认可方案，约定下周推进", "已拉通业务负责人，需求更清晰", "客户主动询问上线周期", "对接人同意安排高层会面"],
    "待推进": ["客户内部还在评估，需再跟", "等待客户反馈预算", "客户关注价格，需准备优惠方案", "需补充同行案例"],
    "无响应": ["电话未接通，已留言", "微信未回复", "对接人出差，暂无反馈", "邮件未回复"],
}


# --------------------------------------------------------------------------- helpers
def wchoice(rng, pairs):
    total = sum(w for _, w in pairs)
    r = rng.random() * total
    for v, w in pairs:
        r -= w
        if r <= 0:
            return v
    return pairs[-1][0]


def is_holiday(d):
    return d.month == 10 and 1 <= d.day <= 7  # 国庆


def is_workday(d):
    return d.weekday() < 5 and not is_holiday(d)


def day_weight(d):
    if is_holiday(d):
        return 0.06
    if d.weekday() >= 5:
        return 0.15
    return 1.0


def next_workday(d):
    while not is_workday(d):
        d += timedelta(days=1)
    return d


def prev_workday(d):
    while not is_workday(d):
        d -= timedelta(days=1)
    return d


def followup_day(rng, d):
    """跟进日落在周末 / 假期：少量照常（发微信、打电话），其余挪到前一个或后一个工作日。"""
    if is_workday(d):
        return d
    if not is_holiday(d):
        if rng.random() < 0.12:
            return d
        if rng.random() < 0.5:
            return prev_workday(d)
    return next_workday(d)


def spread_workday(rng, d, after):
    """业务动作落在非工作日：周末一半提前到周五、一半顺延到周一；长假后分散到节后几天。结果总晚于 after。"""
    if not is_workday(d):
        if is_holiday(d):
            d = next_workday(next_workday(d) + timedelta(days=rng.randint(0, 4)))
        elif rng.random() < 0.5:
            d = prev_workday(d)
        else:
            d = next_workday(d)
    return d if d > after else next_workday(after + timedelta(days=1))


def pick_day(rng, lo, hi, trend=0.0, boost=None):
    """在 [lo, hi] 按「工作日 × 增长趋势」权重抽一天。"""
    days, weights = [], []
    n = max(1, (hi - lo).days)
    d = lo
    while d <= hi:
        w = day_weight(d) * (1.0 + trend * (d - lo).days / n)
        if boost:
            w *= boost(d)
        days.append(d)
        weights.append(w)
        d += timedelta(days=1)
    return rng.choices(days, weights)[0]


def dstr(d):
    return d.strftime("%Y-%m-%d 00:00")


def round_amount(x):
    return int(round(x, -3)) if x >= 20000 else int(round(x, -2))


# --------------------------------------------------------------------------- generators
def gen_sales(rng, today):
    reps = []
    for i, (name, team, level, hired, skill, habit) in enumerate(SALES_ROSTER):
        hired_on = today - timedelta(days=hired) if isinstance(hired, int) else datetime.strptime(hired, "%Y-%m-%d")
        reps.append({"name": name, "no": "YF%04d" % (1001 + i * 7), "team": team, "level": level, "hired": hired_on,
                     "skill": skill, "habit": habit, "new_hire": isinstance(hired, int),
                     "phone": "139%08d" % (rng.randint(0, 99999999))})
    return reps


def _unique_company(rng, used, city, industry, size):
    for _ in range(200):
        core = rng.choice(NAME_A) + rng.choice(NAME_B)
        if core in NAME_BLOCK:
            continue
        biz = rng.choice(BIZ[industry])
        suffix = rng.choice(["集团有限公司", "股份有限公司"]) if size == "1000以上" else "有限公司"
        name = city + core + biz + suffix
        if name not in used:
            used.add(name)
            return name, core + biz[:2]
    raise RuntimeError("公司名用尽")


def gen_customers(rng, reps, today, start):
    customers, used = [], set()
    team_w = [("华东一组", 25), ("华东二组", 20), ("华南组", 21), ("华北组", 21), ("大客户部", 8)]
    cities = dict(TEAM_CITIES)
    expo = (datetime(today.year, 9, 16), datetime(today.year, 9, 20))
    plan = [("old", 185), ("new", 315)]
    for kind, n in plan:
        for _ in range(n):
            team = wchoice(rng, team_w)
            big = team == "大客户部"
            if kind == "old":
                created = pick_day(rng, today - timedelta(days=620), start - timedelta(days=1))
            else:
                created = pick_day(rng, start, today, trend=0.35)
            # 9 月中旬「数字化转型峰会」展会线索
            if kind == "new" and not big and rng.random() < 0.07 and expo[1] <= today:
                created = pick_day(rng, expo[0], expo[1])
                source = "展会"
            elif big:
                source = wchoice(rng, [("合作伙伴", 30), ("转介绍", 25), ("展会", 22), ("官网", 10), ("内容营销", 8),
                                       ("电话外呼", 5)])
            else:
                source = wchoice(rng, [("官网", 24), ("电话外呼", 22), ("内容营销", 19), ("合作伙伴", 13),
                                       ("转介绍", 12), ("展会", 10)])
            if big:
                industry = wchoice(rng, [("制造", 28), ("金融", 22), ("医疗", 14), ("零售", 12), ("互联网", 10),
                                         ("物流", 10), ("教育", 4)])
                size = wchoice(rng, [("1000以上", 75), ("200-1000", 25)])
            else:
                industry = wchoice(rng, [("制造", 21), ("互联网", 21), ("零售", 16), ("物流", 13), ("教育", 11),
                                         ("医疗", 9), ("金融", 9)])
                size = wchoice(rng, [("50-200", 38), ("50人以下", 34), ("200-1000", 22), ("1000以上", 6)])
            tier = {
                "1000以上": lambda: wchoice(rng, [("A", 62), ("B", 30), ("C", 8)]),
                "200-1000": lambda: wchoice(rng, [("A", 24), ("B", 46), ("C", 26), ("D", 4)]),
                "50-200": lambda: wchoice(rng, [("A", 5), ("B", 30), ("C", 47), ("D", 18)]),
                "50人以下": lambda: wchoice(rng, [("B", 12), ("C", 48), ("D", 40)]),
            }[size]()
            if source == "转介绍" and tier != "A" and rng.random() < 0.3:
                tier = TIERS[TIERS.index(tier) - 1]
            if source == "电话外呼" and tier != "D" and rng.random() < 0.25:
                tier = TIERS[TIERS.index(tier) + 1]
            pool = [r for r in reps if r["team"] == team and r["hired"] <= created]
            if not pool:
                pool = [r for r in reps if r["team"] == team and not r["new_hire"]]
            owner = wchoice(rng, [(r, REP_WEIGHT[r["level"]] * (0.6 if r["new_hire"] else 1.0)) for r in pool])
            city = rng.choice(cities[team])
            name, short = _unique_company(rng, used, city, industry, size)
            title = wchoice(rng, [("总经理", 40), ("IT负责人", 18), ("销售副总", 16), ("HR负责人", 10), ("采购经理", 10),
                                  ("CIO", 6)]) if size in ("50人以下", "50-200") else \
                wchoice(rng, [("CIO", 26), ("IT负责人", 30), ("采购经理", 16), ("销售副总", 12), ("HR负责人", 10),
                              ("总经理", 6)])
            customers.append({
                "key": "C%04d" % (len(customers) + 1), "name": name, "short": short, "kind": kind,
                "team": team, "big": big, "industry": industry, "size": size, "source": source, "tier": tier,
                "owner": owner, "city": city, "created": created,
                "contact": rng.choice(SURNAMES) + rng.choice(GIVEN), "contact_title": title,
                "hist_won": kind == "old" and rng.random() < 0.6,
            })
    customers.sort(key=lambda c: (c["created"], c["key"]))
    for i, c in enumerate(customers):
        c["key"] = "C%04d" % (i + 1)
    return customers


def _month_end(d):
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def _quarter_push(rng, won_at, entered_neg, today):
    """季度末冲刺 / 月末小高峰：把临近的成交往前拉（或在月内往月末推）。"""
    q_end = datetime(won_at.year, 9, 30)
    earliest = entered_neg + timedelta(days=2)
    # 本该 10 月成交的单子，一半被拉进 9 月最后一周冲季度业绩
    if q_end < won_at <= q_end + timedelta(days=31) and rng.random() < 0.6:
        cand = prev_workday(q_end - timedelta(days=rng.randint(0, 7)))
        if cand >= earliest:
            return cand
    # 月初成交的一部分被拉到上月末冲月度目标
    if won_at.day <= 6 and rng.random() < 0.3:
        cand = prev_workday(won_at.replace(day=1) - timedelta(days=1 + rng.randint(0, 4)))
        if cand >= earliest:
            return cand
    # 月中下旬的一部分拖到月末才签
    if won_at.day >= 18 and rng.random() < 0.15:
        cand = prev_workday(_month_end(won_at) - timedelta(days=rng.randint(0, 5)))
        if won_at <= cand <= today:
            return cand
    return won_at


def simulate_deal(rng, deal, cust, rep, today):
    renew = deal["type"] == "续约"
    cyc = 1.0
    if cust["big"]:
        cyc *= 1.6
    if renew:
        cyc *= 0.5
    elif deal["type"] == "增购":
        cyc *= 0.8
    mods = (SOURCE_MOD[cust["source"]] ** 0.9) * INDUSTRY_MOD[cust["industry"]] * TIER_MOD[cust["tier"]] * rep["skill"]
    if deal["type"] == "增购":
        mods *= 1.08
    t = deal["created"]
    history = [(t, 0)]  # (进入日期, 阶段下标)
    deal["expected"] = next_workday(t + timedelta(days=int(sum((a + b) / 2.0 for a, b in DWELL) * cyc
                                                         * rng.uniform(0.55, 0.95))))
    for s in range(4):
        dwell = rng.uniform(*DWELL[s]) * cyc
        t_next = spread_workday(rng, t + timedelta(days=int(round(dwell))), t)
        if t_next > today:
            deal["stage"] = STAGES[s]
            deal["history"] = history
            return
        base = (P_ADV_RENEW if renew else P_ADV)[s]
        p = min(0.96, base * (mods if not renew else mods ** 0.3))
        if rng.random() < p:
            t = t_next
            if s < 3:
                history.append((t, s + 1))
            continue
        deal["stage"] = "输单"
        deal["closed"] = t_next
        deal["lost_at"] = s
        pairs = list(LOST_BY_STAGE[s])
        bias = LOST_INDUSTRY_BIAS.get(cust["industry"])
        pairs = [(r, w * (1.7 if r == bias else 1.0)) for r, w in pairs]
        deal["lost_reason"] = wchoice(rng, pairs)
        deal["history"] = history
        return
    won_at = _quarter_push(rng, t, history[-1][0], today)
    deal["stage"] = "赢单"
    deal["closed"] = max(won_at, history[-1][0])
    deal["history"] = history


def gen_deals(rng, customers, reps, today, start):
    deals = []
    horizon = today - timedelta(days=150)
    by_team = {}
    for r in reps:
        by_team.setdefault(r["team"], []).append(r)

    def add(cust, created, dtype, product):
        if created > today:
            return
        owner = cust["owner"]
        if rng.random() < 0.06:  # 少量商机由同组其他人负责（协作 / 交接）
            pool = [r for r in by_team[cust["team"]] if r["hired"] <= created]
            owner = rng.choice(pool) if pool else owner
        lo, hi = AMOUNT_BY_SIZE[cust["size"]]
        if cust["big"] and cust["size"] == "1000以上":
            lo, hi = 600000, 2200000
        amount = rng.uniform(lo, hi) * PRODUCT_MOD[product] * TYPE_MOD[dtype]
        d = {"key": "OP%04d" % (len(deals) + 1), "customer": cust["key"], "cust": cust, "owner": owner,
             "product": product, "type": dtype, "created": created, "amount": round_amount(amount)}
        simulate_deal(rng, d, cust, owner, today)
        deals.append(d)

    for c in customers:
        products = list(PRODUCTS)
        rng.shuffle(products)
        if c["kind"] == "new":
            p_opp = {"转介绍": 0.93, "合作伙伴": 0.88, "展会": 0.78, "官网": 0.8, "内容营销": 0.74, "电话外呼": 0.6}[c["source"]]
            if rng.random() < p_opp:
                first = next_workday(c["created"] + timedelta(days=rng.randint(0, 8)))
                add(c, first, "新购", products[0])
                if rng.random() < (0.4 if c["size"] in ("200-1000", "1000以上") else 0.2):
                    add(c, next_workday(first + timedelta(days=rng.randint(10, 45))), "新购", products[1])
        else:
            if c["hist_won"]:
                c["owned"] = products[:rng.randint(1, 2)]
                for p in c["owned"]:
                    if rng.random() < 0.55:  # 年度续约（到期月份落在近 5 个月内）
                        add(c, pick_day(rng, horizon, today - timedelta(days=3)), "续约", p)
                for _ in range(rng.choice([1, 1, 2, 2, 3])):
                    add(c, pick_day(rng, horizon, today, trend=0.25), "增购", rng.choice(c["owned"]))
                for p in products[len(c["owned"]):len(c["owned"]) + rng.choice([0, 1, 1, 2])]:
                    add(c, pick_day(rng, horizon, today, trend=0.25), "新购", p)
            else:
                for p in products[:rng.choice([1, 2, 2, 3, 3])]:
                    add(c, pick_day(rng, horizon, today, trend=0.25), "新购", p)
    deals.sort(key=lambda d: (d["created"], d["key"]))
    for i, d in enumerate(deals):
        d["key"] = "OP%04d" % (i + 1)
    for d in deals:
        if d["stage"] in OPEN_STAGES:
            s = OPEN_STAGES.index(d["stage"])
            d["prob"] = round(min(0.95, max(0.05, STAGE_PROB[s] + rng.uniform(-0.05, 0.05))), 2)
        else:
            d["prob"] = 1.0 if d["stage"] == "赢单" else 0.0
        d["name"] = "%s · %s%s" % (d["cust"]["short"], d["product"], d["type"])
    return deals


def _stage_on(deal, day):
    """商机在某天所处阶段（None = 尚未创建或已结单后）。"""
    if day < deal["created"]:
        return None
    if deal.get("closed") and day > deal["closed"]:
        return "已结单"
    cur = STAGES[0]
    for t, s in deal["history"]:
        if t <= day:
            cur = STAGES[s]
    return cur


def gen_followups(rng, customers, deals, reps, today, now, start):
    deals_by_c = {}
    for d in deals:
        deals_by_c.setdefault(d["customer"], []).append(d)
    managers = {r["team"]: r for r in reps if r["level"] == "销售主管"}
    hours = [(9, 6), (10, 12), (11, 10), (12, 2), (13, 4), (14, 11), (15, 12), (16, 10), (17, 7), (18, 3), (19, 1)]
    out = []
    for c in customers:
        # 每个客户独立的随机流：跟进记录截止到「此刻」，同一天稍后续跑只会在末尾多出今天的新记录，不影响其他客户
        rng = random.Random("%d:%s" % (SEED, c["key"]))
        ds = deals_by_c.get(c["key"], [])
        won = [d for d in ds if d["stage"] == "赢单"]
        open_ = [d for d in ds if d["stage"] in OPEN_STAGES]
        lost_all = bool(ds) and not won and not open_
        status = "已成交" if (won or c["hist_won"]) else ("跟进中" if open_ else ("已流失" if lost_all else "潜在客户"))
        c["status"] = status
        # 起点：客户创建（新客）或窗口内第一个商机 / 随机一天（老客）
        if c["kind"] == "new":
            t = next_workday(c["created"] + timedelta(days=rng.randint(0, 2)))
        else:
            firsts = [d["created"] for d in ds if d["created"] >= start]
            if firsts and rng.random() < 0.6:
                t = min(firsts)
            elif c["hist_won"] or ds:
                t = pick_day(rng, start, start + timedelta(days=40))
            else:
                if rng.random() < 0.75:
                    continue
                t = pick_day(rng, start, today)
        last_activity = max([d.get("closed") or today for d in ds] or [c["created"] + timedelta(days=40)])
        if not ds and c["kind"] == "new":
            last_activity = c["created"] + timedelta(days=rng.choice([10, 20, 35, 60, 120]))
        prev = None
        while t <= today:
            # 当天所处情境
            stages = [s for s in (_stage_on(d, t) for d in ds) if s and s != "已结单"]
            order = {"线索": 0, "需求确认": 1, "方案报价": 2, "商务谈判": 3}
            ctx = max(stages, key=lambda s: order[s]) if stages else (
                "已成交" if (c["hist_won"] or any(d["stage"] == "赢单" and d["closed"] <= t for d in ds)) else
                ("流失" if lost_all and t > last_activity else "潜在"))
            when = t + timedelta(hours=wchoice(rng, hours), minutes=rng.randint(0, 59))
            if when > now:
                break
            rep = c["owner"]
            if ctx in ("方案报价", "商务谈判") and c["tier"] in ("A", "B") and rng.random() < 0.12:
                rep = managers[c["team"]]
            if rep["hired"] > t:
                rep = managers[c["team"]]
            if not is_workday(t):
                method = wchoice(rng, [("微信", 70), ("电话", 30)])
            elif c["big"] or ctx in ("方案报价", "商务谈判"):
                method = wchoice(rng, [("拜访", 30), ("线上会议", 30), ("微信", 20), ("电话", 15), ("邮件", 5)])
            else:
                method = wchoice(rng, [("电话", 32), ("微信", 30), ("线上会议", 16), ("拜访", 12), ("邮件", 10)])
            # 结果：接下来一段时间阶段有推进 → 有进展；潜在 / 流失 → 多无响应
            advanced = any(_stage_on(d, t) != _stage_on(d, t + timedelta(days=12)) and
                           _stage_on(d, t + timedelta(days=12)) not in (None, "已结单") for d in ds)
            closing_lost = any(d["stage"] == "输单" and t <= d["closed"] <= t + timedelta(days=12) for d in ds)
            if advanced:
                outcome = wchoice(rng, [("有进展", 72), ("待推进", 24), ("无响应", 4)])
            elif closing_lost:
                outcome = wchoice(rng, [("有进展", 6), ("待推进", 44), ("无响应", 50)])
            elif ctx in ("潜在", "流失"):
                outcome = wchoice(rng, [("有进展", 12), ("待推进", 40), ("无响应", 48)])
            elif ctx == "已成交":
                outcome = wchoice(rng, [("有进展", 40), ("待推进", 50), ("无响应", 10)])
            else:
                outcome = wchoice(rng, [("有进展", 34), ("待推进", 46), ("无响应", 20)])
            rec = {"key": "FU%05d" % (len(out) + 1), "customer": c["key"], "cust": c, "rep": rep, "when": when,
                   "method": method, "outcome": outcome, "ctx": ctx,
                   "title": "%s · %s" % (c["short"], rng.choice(TOPICS.get(ctx, TOPICS["潜在"]))),
                   "note": rng.choice(NOTES[outcome])}
            if prev is not None:
                prev["next_status"] = "已完成"
            out.append(rec)
            prev = rec
            # 是否还要跟：客户流失 / 潜在客户冷却后不再跟
            if t >= last_activity and (lost_all or (not ds and c["kind"] == "new")) and not c["hist_won"]:
                rec["next_status"] = "无需跟进"
                rec["next"] = None
                break
            if ctx == "商务谈判":
                gap = rng.choice([5, 7, 10, 10])
            elif ctx in ("方案报价", "需求确认"):
                gap = rng.choice([10, 14, 14, 21])
            elif ctx == "线索":
                gap = rng.choice([10, 14, 21])
            elif ctx == "已成交":
                gap = rng.choice([45, 60, 60, 90])
            else:
                gap = rng.choice([21, 30, 45])
            planned = next_workday(t + timedelta(days=gap))
            rec["next"] = planned
            rec["next_status"] = "待跟进"
            if rng.random() < FORGET[c["owner"]["habit"]]:
                break
            slip = rng.choice(SLIP[c["owner"]["habit"]])
            nxt = followup_day(rng, max(t + timedelta(days=1), planned + timedelta(days=slip)))
            t = nxt if nxt > t else next_workday(t + timedelta(days=1))
    out.sort(key=lambda r: (r["when"], r["key"]))
    for i, r in enumerate(out):
        r["key"] = "FU%05d" % (i + 1)
    return out


def gen_contracts(rng, deals, today):
    won = sorted([d for d in deals if d["stage"] == "赢单"], key=lambda d: (d["closed"], d["key"]))
    out, seq = [], {}
    for d in won:
        c = d["cust"]
        signed = d["closed"]
        ym = signed.strftime("%Y%m")
        seq[ym] = seq.get(ym, 0) + 1
        amount = round_amount(d["amount"] * rng.uniform(0.86, 1.0))
        slow = (c["industry"] in ("金融", "医疗")) * 10 + c["big"] * 10
        lag1 = rng.randint(15, 30) + slow + (rng.randint(0, 10) if c["size"] == "1000以上" else 0)
        terms = "分两期" if rng.random() < (0.45 if c["big"] or amount >= 400000 else 0.18) else "一次性付清"
        bad = rng.random() < 0.05
        pays = []
        if terms == "一次性付清":
            pays.append((next_workday(signed + timedelta(days=lag1)), amount))
        else:
            first = round_amount(amount * 0.5)
            p1 = next_workday(signed + timedelta(days=lag1))
            pays.append((p1, first))
            pays.append((next_workday(p1 + timedelta(days=rng.randint(20, 45))), amount - first))
        if bad:
            pays = pays[:0] if terms == "一次性付清" else pays[:1]
        got = [(t, a) for t, a in pays if t <= today]
        received = sum(a for _, a in got)
        status = "已回清" if received >= amount else ("部分回款" if received > 0 else "未回款")
        out.append({"key": "YF-HT-%s-%03d" % (ym, seq[ym]), "deal": d, "customer": c["key"], "rep": d["owner"],
                    "amount": amount, "signed": signed, "terms": terms, "received": received,
                    "last_paid": got[-1][0] if got else None, "status": status})
    return out


def calibrate_targets(reps, contracts, today, start):
    """季度目标 ≈（本人 + 同类岗位人均）近 120 天签约额折算到一个季度 × 1.1，取整到万；主管打 6 折，新人减半。"""
    by_rep = {}
    for k in contracts:
        if k["signed"] >= start:
            by_rep[k["rep"]["name"]] = by_rep.get(k["rep"]["name"], 0) + k["amount"] * 91.0 / WINDOW_DAYS
    group = {}
    for r in reps:
        if not r["new_hire"] and r["level"] != "销售主管":
            group.setdefault(r["team"] == "大客户部", []).append(by_rep.get(r["name"], 0))
    for r in reps:
        vals = group.get(r["team"] == "大客户部") or [500000]
        avg = sum(vals) / float(len(vals))
        base = (by_rep.get(r["name"], 0) + avg) / 2.0 * 1.1
        if r["level"] == "销售主管":
            base = avg * 0.6
        if r["new_hire"]:
            base = avg * 0.5
        r["target"] = int(max(300000, round(base, -4)))


def generate_all(now=None):
    now = now or now_local()
    rng = random.Random(SEED)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=WINDOW_DAYS - 1)
    reps = gen_sales(rng, today)
    customers = gen_customers(rng, reps, today, start)
    deals = gen_deals(rng, customers, reps, today, start)
    followups = gen_followups(rng, customers, deals, reps, today, now, start)
    contracts = gen_contracts(rng, deals, today)
    calibrate_targets(reps, contracts, today, start)
    return {"now": now, "today": today, "start": start, "reps": reps, "customers": customers, "deals": deals,
            "followups": followups, "contracts": contracts}


# --------------------------------------------------------------------------- rows for seed_base.py
def _link(table, *keys):
    return {"$link": table, "keys": [k for k in keys if k]}


def generate(now=None):
    g = generate_all(now)
    sales = [{"$key": r["name"], "姓名": r["name"], "工号": r["no"], "团队": [r["team"]], "职级": [r["level"]],
              "入职日期": dstr(r["hired"]), "季度目标": r["target"], "手机号": r["phone"]} for r in g["reps"]]
    customers = [{"$key": c["key"], "客户名称": c["name"], "行业": [c["industry"]], "规模": [c["size"]],
                  "来源": [c["source"]], "客户等级": [c["tier"]], "客户状态": [c["status"]],
                  "负责销售": _link("销售人员", c["owner"]["name"]), "所在城市": [c["city"]],
                  "创建日期": dstr(c["created"]), "联系人": c["contact"], "联系人职务": [c["contact_title"]]}
                 for c in g["customers"]]
    deals = []
    for d in g["deals"]:
        row = {"$key": d["key"], "商机名称": d["name"], "客户": _link("客户档案", d["customer"]),
               "负责销售": _link("销售人员", d["owner"]["name"]), "产品线": [d["product"]], "商机类型": [d["type"]],
               "阶段": [d["stage"]], "预计金额": d["amount"], "赢率": d["prob"], "创建日期": dstr(d["created"]),
               "预计成交日期": dstr(d["expected"])}
        if d.get("closed"):
            row["结单日期"] = dstr(d["closed"])
        if d.get("lost_reason"):
            row["输单原因"] = [d["lost_reason"]]
        deals.append(row)
    followups = []
    for f in g["followups"]:
        row = {"$key": f["key"], "标题": f["title"], "客户": _link("客户档案", f["customer"]),
               "销售": _link("销售人员", f["rep"]["name"]), "方式": [f["method"]],
               "跟进时间": f["when"].strftime("%Y-%m-%d %H:%M"), "下次跟进状态": [f["next_status"]],
               "跟进结果": [f["outcome"]], "跟进纪要": f["note"]}
        if f.get("next"):
            row["下次跟进日期"] = dstr(f["next"])
        followups.append(row)
    contracts = []
    for k in g["contracts"]:
        row = {"$key": k["key"], "合同编号": k["key"], "客户": _link("客户档案", k["customer"]),
               "商机": _link("商机", k["deal"]["key"]), "销售": _link("销售人员", k["rep"]["name"]),
               "合同金额": k["amount"], "签约日期": dstr(k["signed"]), "付款方式": [k["terms"]],
               "已回款金额": k["received"], "回款状态": [k["status"]]}
        if k["last_paid"]:
            row["最近回款日期"] = dstr(k["last_paid"])
        contracts.append(row)
    return {"销售人员": sales, "客户档案": customers, "商机": deals, "跟进记录": followups, "合同回款": contracts}


if __name__ == "__main__":  # 干跑：python3 -m domains.crm（在 scripts/ 目录下）
    for _t, _rows in generate().items():
        print(_t, len(_rows))
