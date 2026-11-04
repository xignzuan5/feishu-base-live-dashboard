"""「鹿野咖啡」连锁经营演示数据：表结构 + 有业务规律的数据生成器。

所有时间均为 Asia/Shanghai 本地时间（与 Base 时区一致），写入格式 `YYYY-MM-DD HH:mm`。
生成是确定性的（固定随机种子），同一天重复运行得到同一份数据，便于断点续传。
"""
import math
import random
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

TZ = "Asia/Shanghai"
DAYS = 45
SEED = 20261104
BASE_ORDERS_PER_STORE_DAY = 6.0


def now_local():
    if ZoneInfo:
        return datetime.now(ZoneInfo(TZ)).replace(tzinfo=None)
    return datetime.utcnow() + timedelta(hours=8)


def fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M")


def opt(*names_hues):
    return [{"name": n, "hue": h, "lightness": "Light"} for n, h in names_hues]


CNY0 = {"type": "currency", "precision": 0, "currency_code": "CNY"}
CNY2 = {"type": "currency", "precision": 2, "currency_code": "CNY"}

# --------------------------------------------------------------------------- schema
CITY_INFO = {
    # 城市: (大区, lng, lat, [门店后缀])
    "上海": ("华东", 121.4737, 31.2304, ["静安嘉里", "陆家嘴滨江", "徐家汇", "张江科学城", "新天地"]),
    "北京": ("华北", 116.4074, 39.9042, ["三里屯", "国贸", "中关村", "望京SOHO"]),
    "杭州": ("华东", 120.1551, 30.2741, ["西湖湖滨", "滨江星光", "未来科技城"]),
    "深圳": ("华南", 114.0579, 22.5431, ["南山科技园", "福田CBD", "前海"]),
    "广州": ("华南", 113.2644, 23.1291, ["天河太古汇", "珠江新城"]),
    "成都": ("西南", 104.0665, 30.5723, ["太古里", "高新天府"]),
    "武汉": ("华中", 114.3054, 30.5931, ["光谷", "江汉路"]),
    "南京": ("华东", 118.7969, 32.0603, ["新街口", "河西万达"]),
}
CBD_STORES = {"陆家嘴滨江", "国贸", "福田CBD", "珠江新城", "南山科技园", "张江科学城", "中关村", "望京SOHO"}

STORE_FIELDS = [
    {"type": "text", "name": "门店名称"},
    {"type": "text", "name": "门店编码"},
    {"type": "select", "name": "城市", "multiple": False,
     "options": opt(("上海", "Blue"), ("北京", "Red"), ("杭州", "Green"), ("深圳", "Purple"),
                    ("广州", "Orange"), ("成都", "Carmine"), ("武汉", "Turquoise"), ("南京", "Yellow"))},
    {"type": "select", "name": "大区", "multiple": False,
     "options": opt(("华东", "Blue"), ("华北", "Red"), ("华南", "Purple"), ("西南", "Carmine"), ("华中", "Turquoise"))},
    {"type": "select", "name": "门店类型", "multiple": False,
     "options": opt(("旗舰店", "Carmine"), ("标准店", "Blue"), ("快取店", "Green"), ("校园店", "Orange"))},
    {"type": "select", "name": "经营状态", "multiple": False,
     "options": opt(("营业中", "Green"), ("试营业", "Wathet"), ("装修升级", "Gray"))},
    {"type": "datetime", "name": "开业日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "text", "name": "店长"},
    {"type": "text", "name": "联系电话", "style": {"type": "phone"}},
    {"type": "number", "name": "座位数", "style": {"type": "plain", "precision": 0}},
    {"type": "number", "name": "月租金", "style": CNY0},
    {"type": "number", "name": "日营收目标", "style": CNY0},
    {"type": "number", "name": "口碑评分", "style": {"type": "plain", "precision": 1}},
    {"type": "checkbox", "name": "支持外卖"},
    {"type": "location", "name": "门店位置"},
]

PRODUCT_FIELDS = [
    {"type": "text", "name": "商品名称"},
    {"type": "text", "name": "商品编码"},
    {"type": "select", "name": "品类", "multiple": False,
     "options": opt(("意式咖啡", "Orange"), ("手冲精品", "Carmine"), ("茶饮", "Green"),
                    ("轻食", "Lime"), ("烘焙", "Yellow"), ("周边", "Purple"))},
    {"type": "number", "name": "售价", "style": CNY2},
    {"type": "number", "name": "成本", "style": CNY2},
    {"type": "select", "name": "标签", "multiple": True,
     "options": opt(("招牌", "Red"), ("季节限定", "Orange"), ("新品", "Green"), ("低糖", "Turquoise"),
                    ("燕麦奶", "Lime"), ("可做冰", "Wathet"), ("联名", "Purple"), ("高毛利", "Carmine"))},
    {"type": "checkbox", "name": "是否新品"},
    {"type": "datetime", "name": "上市日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "number", "name": "热量kcal", "style": {"type": "plain", "precision": 0}},
    {"type": "select", "name": "销售状态", "multiple": False,
     "options": opt(("在售", "Green"), ("季节下架", "Gray"), ("售罄", "Red"))},
]

CAMPAIGN_FIELDS = [
    {"type": "text", "name": "活动名称"},
    {"type": "select", "name": "活动类型", "multiple": False,
     "options": opt(("新品尝鲜", "Green"), ("会员日", "Purple"), ("第二杯半价", "Orange"), ("满减", "Red"),
                    ("品牌联名", "Carmine"), ("节日限定", "Yellow"), ("时段套餐", "Blue"))},
    {"type": "datetime", "name": "开始日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "datetime", "name": "结束日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "number", "name": "活动预算", "style": CNY0},
    {"type": "number", "name": "折扣力度", "style": {"type": "plain", "precision": 0, "percentage": True}},
    {"type": "select", "name": "活动状态", "multiple": False,
     "options": opt(("进行中", "Green"), ("已结束", "Gray"), ("未开始", "Blue"))},
    {"type": "text", "name": "活动说明"},
]

MEMBER_FIELDS = [
    {"type": "text", "name": "会员昵称"},
    {"type": "text", "name": "会员卡号"},
    {"type": "select", "name": "会员等级", "multiple": False,
     "options": opt(("青铜", "Orange"), ("白银", "Gray"), ("黄金", "Yellow"), ("黑金", "Purple"))},
    {"type": "select", "name": "性别", "multiple": False, "options": opt(("女", "Red"), ("男", "Blue"), ("未知", "Gray"))},
    {"type": "select", "name": "年龄段", "multiple": False,
     "options": opt(("18-24", "Green"), ("25-30", "Blue"), ("31-40", "Purple"), ("41+", "Orange"))},
    {"type": "datetime", "name": "注册日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "select", "name": "注册渠道", "multiple": False,
     "options": opt(("小程序", "Green"), ("门店扫码", "Blue"), ("外卖平台", "Orange"), ("企业团购", "Purple"))},
    {"type": "link", "name": "归属门店", "link_table": "门店"},
    {"type": "text", "name": "手机号", "style": {"type": "phone"}},
    {"type": "select", "name": "口味偏好", "multiple": True,
     "options": opt(("燕麦奶", "Lime"), ("少糖", "Turquoise"), ("冰饮", "Wathet"), ("手冲", "Carmine"),
                    ("甜品控", "Red"), ("早餐党", "Yellow"), ("低咖啡因", "Gray"))},
    {"type": "number", "name": "储值余额", "style": CNY2},
    {"type": "number", "name": "积分", "style": {"type": "plain", "precision": 0, "thousands_separator": True}},
]

ORDER_FIELDS = [
    {"type": "text", "name": "订单号"},
    {"type": "datetime", "name": "下单时间", "style": {"format": "yyyy-MM-dd HH:mm"}},
    {"type": "link", "name": "门店", "link_table": "门店", "bidirectional": True, "bidirectional_link_field_name": "订单记录"},
    {"type": "link", "name": "会员", "link_table": "会员"},
    {"type": "link", "name": "营销活动", "link_table": "营销活动"},
    {"type": "select", "name": "渠道", "multiple": False,
     "options": opt(("堂食", "Blue"), ("到店自提", "Green"), ("小程序外送", "Turquoise"), ("美团外卖", "Yellow"),
                    ("饿了么", "Wathet"), ("企业团购", "Purple"))},
    {"type": "select", "name": "支付方式", "multiple": False,
     "options": opt(("微信支付", "Green"), ("支付宝", "Blue"), ("会员储值", "Purple"), ("银行卡", "Orange"), ("平台代收", "Gray"))},
    {"type": "select", "name": "订单状态", "multiple": False,
     "options": opt(("制作中", "Orange"), ("配送中", "Wathet"), ("已完成", "Green"), ("已退款", "Red"), ("已取消", "Gray"))},
    {"type": "number", "name": "订单金额", "style": CNY2},
    {"type": "number", "name": "优惠金额", "style": CNY2},
    {"type": "number", "name": "实付金额", "style": CNY2},
    {"type": "number", "name": "杯数", "style": {"type": "plain", "precision": 0}},
    {"type": "checkbox", "name": "是否新客"},
    {"type": "number", "name": "评价星级", "style": {"type": "rating", "icon": "star", "min": 1, "max": 5}},
    {"type": "text", "name": "顾客备注"},
]

ITEM_FIELDS = [
    {"type": "text", "name": "明细编号"},
    {"type": "link", "name": "订单", "link_table": "订单", "bidirectional": True, "bidirectional_link_field_name": "商品明细"},
    {"type": "link", "name": "商品", "link_table": "商品", "bidirectional": True, "bidirectional_link_field_name": "销售明细"},
    {"type": "number", "name": "数量", "style": {"type": "plain", "precision": 0}},
    {"type": "number", "name": "单价", "style": CNY2},
    {"type": "select", "name": "规格", "multiple": False,
     "options": opt(("中杯", "Blue"), ("大杯", "Purple"), ("超大杯", "Carmine"), ("标准", "Gray"))},
    {"type": "select", "name": "温度", "multiple": False,
     "options": opt(("热", "Red"), ("冰", "Wathet"), ("少冰", "Turquoise"), ("常温", "Gray"))},
    {"type": "select", "name": "甜度", "multiple": False,
     "options": opt(("标准糖", "Orange"), ("少糖", "Yellow"), ("半糖", "Lime"), ("无糖", "Green"))},
]

# 数据写完后再建公式，避免逐批写入时反复重算
FORMULAS = {
    "门店": [
        {"type": "formula", "name": "累计营收", "expression": "[订单记录].[实付金额].SUM()"},
        {"type": "formula", "name": "累计订单数", "expression": "[订单记录].[订单号].COUNTA()"},
    ],
    "商品": [
        {"type": "formula", "name": "毛利率", "expression": "IF([售价]>0, ROUND(([售价]-[成本])/[售价], 4), 0)"},
        {"type": "formula", "name": "累计销量", "expression": "[销售明细].[数量].SUM()"},
    ],
    "订单": [
        {"type": "formula", "name": "优惠率", "expression": "IF([订单金额]>0, ROUND([优惠金额]/[订单金额], 4), 0)"},
        {"type": "formula", "name": "下单时段", "expression": "HOUR([下单时间])"},
    ],
    "订单明细": [
        {"type": "formula", "name": "小计", "expression": "[数量]*[单价]"},
    ],
}

TABLES = [
    ("门店", STORE_FIELDS),
    ("商品", PRODUCT_FIELDS),
    ("营销活动", CAMPAIGN_FIELDS),
    ("会员", MEMBER_FIELDS),
    ("订单", ORDER_FIELDS),
    ("订单明细", ITEM_FIELDS),
]

# --------------------------------------------------------------------------- catalogs
# (名称, 品类, 售价, 成本, 标签, 是否新品, 热量, 人气权重, 是否饮品)
PRODUCTS = [
    ("美式", "意式咖啡", 22, 4.5, ["招牌", "可做冰", "高毛利"], False, 15, 14, True),
    ("拿铁", "意式咖啡", 28, 7.0, ["招牌", "可做冰"], False, 190, 18, True),
    ("燕麦拿铁", "意式咖啡", 30, 8.5, ["燕麦奶", "可做冰"], False, 170, 10, True),
    ("澳白", "意式咖啡", 30, 7.5, ["招牌"], False, 160, 8, True),
    ("卡布奇诺", "意式咖啡", 28, 7.0, [], False, 150, 6, True),
    ("摩卡", "意式咖啡", 32, 8.5, [], False, 290, 4, True),
    ("焦糖玛奇朵", "意式咖啡", 32, 8.0, [], False, 250, 5, True),
    ("生椰拿铁", "意式咖啡", 30, 8.0, ["可做冰"], False, 210, 9, True),
    ("桂花拿铁", "意式咖啡", 32, 8.5, ["季节限定", "新品"], True, 220, 9, True),
    ("南瓜香料拿铁", "意式咖啡", 32, 8.5, ["季节限定", "新品"], True, 240, 6, True),
    ("冷萃", "意式咖啡", 26, 5.0, ["低糖", "可做冰", "高毛利"], False, 10, 5, True),
    ("耶加雪菲手冲", "手冲精品", 38, 10.0, ["低糖"], False, 5, 3, True),
    ("瑰夏手冲", "手冲精品", 58, 18.0, ["招牌"], False, 5, 1.5, True),
    ("云南保山手冲", "手冲精品", 32, 8.0, ["低糖", "高毛利"], False, 5, 2, True),
    ("抹茶拿铁", "茶饮", 30, 8.0, ["可做冰"], False, 230, 5, True),
    ("伯爵红茶拿铁", "茶饮", 28, 7.0, [], False, 200, 3, True),
    ("柠檬冰茶", "茶饮", 22, 4.0, ["低糖", "高毛利"], False, 80, 4, True),
    ("白桃乌龙", "茶饮", 24, 5.0, ["低糖"], False, 60, 4, True),
    ("牛油果鸡胸三明治", "轻食", 32, 13.0, [], False, 420, 4, False),
    ("芝士火腿可颂", "轻食", 26, 9.0, [], False, 380, 5, False),
    ("凯撒沙拉", "轻食", 35, 14.0, [], False, 260, 2, False),
    ("全麦贝果", "轻食", 18, 6.0, ["低糖"], False, 280, 3, False),
    ("黄油可颂", "烘焙", 16, 5.0, ["招牌"], False, 300, 6, False),
    ("肉桂卷", "烘焙", 22, 6.5, [], False, 380, 3, False),
    ("巴斯克芝士蛋糕", "烘焙", 32, 10.0, ["招牌"], False, 420, 3, False),
    ("提拉米苏", "烘焙", 34, 11.0, [], False, 450, 2, False),
    ("布朗尼", "烘焙", 20, 6.0, [], False, 360, 2, False),
    ("鹿野马克杯", "周边", 89, 28.0, [], False, 0, 0.4, False),
    ("鹿野随行杯", "周边", 129, 42.0, [], False, 0, 0.3, False),
    ("挂耳咖啡礼盒", "周边", 79, 25.0, ["高毛利"], False, 0, 0.6, False),
    ("鹿野拼配咖啡豆250g", "周边", 98, 32.0, [], False, 0, 0.5, False),
    ("故宫联名帆布袋", "周边", 69, 20.0, ["联名", "新品"], True, 0, 0.5, False),
]

SURNAMES = list("王李张刘陈杨黄赵吴周徐孙马朱胡郭何林罗高郑梁谢宋唐许韩冯邓曹彭曾萧田董潘袁蔡蒋余")
NICK_A = ["早八人", "拿铁星人", "咖啡续命的", "燕麦控", "手冲爱好者", "爱喝冰美式的", "打工人", "周末探店的",
          "社恐的", "猫奴", "跑步的", "画画的", "加班的", "在读研的", "做设计的", "写代码的", "带娃的", "旅行中的"]
NICK_B = ["小王", "阿杰", "Lily", "Kevin", "小鹿", "团子", "大橙子", "Coco", "小林", "Momo", "阿北", "Yuki",
          "老陈", "Echo", "小满", "Jason", "布丁", "阿May", "七七", "Leo", "小雨", "Tina", "豆豆", "Max"]
MANAGERS = ["陈思远", "林晓雯", "王浩然", "赵一鸣", "周可欣", "吴子涵", "郑雨桐", "孙嘉怡", "李泽宇", "黄诗琪",
            "刘梓萱", "张博文", "徐欣然", "马俊杰", "胡佳宁", "郭天佑", "何雨萌", "高子轩", "罗静怡", "梁浩宇",
            "宋婉清", "唐文博", "许晴", "韩一诺"]
REMARKS = ["少冰谢谢", "请放前台", "燕麦奶替换", "多给一个吸管", "不要糖浆", "打包带走", "放到门卫处",
           "温度烫一点", "需要发票", "生日快乐卡片", "麻烦快一点赶会议"]

CHANNELS = [("堂食", 30), ("到店自提", 26), ("小程序外送", 14), ("美团外卖", 15), ("饿了么", 11), ("企业团购", 3)]
HOUR_WEIGHTS = {7: 3, 8: 9, 9: 10, 10: 7, 11: 6, 12: 8, 13: 8, 14: 6, 15: 7, 16: 6, 17: 5, 18: 4, 19: 3, 20: 3, 21: 2}
DRINK_CATS = {"意式咖啡", "手冲精品", "茶饮"}


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
    return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))


# --------------------------------------------------------------------------- generators
def gen_stores(rng, today):
    stores = []
    idx = 0
    for city, (region, lng, lat, names) in CITY_INFO.items():
        for j, suffix in enumerate(names):
            idx += 1
            stype = "旗舰店" if j == 0 else ("快取店" if suffix in CBD_STORES and rng.random() < 0.5 else "标准店")
            stores.append({"city": city, "region": region, "suffix": suffix, "type": stype,
                           "lng": lng + rng.uniform(-0.06, 0.06), "lat": lat + rng.uniform(-0.05, 0.05)})
    stores.append({"city": "杭州", "region": "华东", "suffix": "浙大紫金港", "type": "校园店",
                   "lng": 120.0850, "lat": 30.3070})
    weight = {"旗舰店": 1.7, "标准店": 1.0, "快取店": 0.85, "校园店": 0.95}
    seats = {"旗舰店": (60, 110), "标准店": (24, 48), "快取店": (0, 8), "校园店": (30, 60)}
    rent = {"旗舰店": (90000, 160000), "标准店": (32000, 65000), "快取店": (15000, 28000), "校园店": (12000, 20000)}
    city_counter = {}
    for i, s in enumerate(stores):
        city_counter[s["city"]] = city_counter.get(s["city"], 0) + 1
        code_prefix = {"上海": "SH", "北京": "BJ", "杭州": "HZ", "深圳": "SZ", "广州": "GZ",
                       "成都": "CD", "武汉": "WH", "南京": "NJ"}[s["city"]]
        s["name"] = "鹿野咖啡·%s店" % s["suffix"]
        s["code"] = "%s-%03d" % (code_prefix, city_counter[s["city"]])
        s["weight"] = weight[s["type"]] * rng.uniform(0.85, 1.2)
        s["open_date"] = today - timedelta(days=rng.randint(200, 1500))
        s["status"] = "营业中"
        s["manager"] = MANAGERS[i % len(MANAGERS)]
        s["seats"] = rng.randint(*seats[s["type"]])
        s["rent"] = round(rng.randint(*rent[s["type"]]), -2)
        s["score"] = round(rng.uniform(4.3, 4.9), 1)
        s["delivery"] = s["type"] != "校园店"
        s["cbd"] = s["suffix"] in CBD_STORES
        s["closed_from"] = None
    # 两家新开门店（窗口期内开业，试营业）+ 一家装修升级（近 9 天停业）
    stores[7]["open_date"] = today - timedelta(days=24)   # 北京·望京SOHO
    stores[7]["status"] = "试营业"
    stores[13]["open_date"] = today - timedelta(days=12)  # 深圳·前海
    stores[13]["status"] = "试营业"
    stores[19]["status"] = "装修升级"                       # 成都·高新天府
    stores[19]["closed_from"] = today - timedelta(days=9)
    for s in stores:
        # 粗估日均营收（订单数 × 客单价 ≈ 75 元）再上浮 0~15% 作为目标；造数后可用 fix 脚本按真实均值校准
        s["target"] = int(round(BASE_ORDERS_PER_STORE_DAY * s["weight"] * 75 * rng.uniform(1.0, 1.15), -1))
    return stores


def gen_campaigns(today):
    d = lambda n: today + timedelta(days=n)  # noqa: E731
    camps = [
        ("秋日桂花拿铁·新品尝鲜", "新品尝鲜", d(-44), d(-30), 9000, 20, "桂花拿铁/南瓜香料拿铁上新 8 折"),
        ("国庆咖啡续命计划", "节日限定", datetime(today.year, 10, 1), datetime(today.year, 10, 7), 6000, 25, "国庆 7 天第二杯 7.5 折"),
        ("周三会员日", "会员日", d(-44), d(30), 8000, 15, "每周三会员全场 85 折"),
        ("早八元气套餐", "时段套餐", d(-44), d(60), 12000, 18, "10 点前咖啡+烘焙组合立减"),
        ("第二杯半价", "第二杯半价", d(-28), d(-21), 3000, 25, "同单第二杯半价"),
        ("满50减8", "满减", d(-20), d(-10), 4000, 16, "实付满 50 立减 8 元"),
        ("鹿野×故宫文创联名", "品牌联名", d(-14), d(6), 10000, 10, "联名杯套+帆布袋，联名饮品 9 折"),
        ("双11囤券节", "节日限定", datetime(today.year, 11, 1), datetime(today.year, 11, 11), 8000, 30, "储值卡 7 折囤券"),
    ]
    out = []
    for name, ctype, start, end, budget, pct, desc in camps:
        status = "进行中" if start.date() <= today.date() <= end.date() else ("已结束" if end.date() < today.date() else "未开始")
        out.append({"name": name, "type": ctype, "start": start, "end": end, "budget": budget,
                    "pct": pct, "status": status, "desc": desc})
    return out


def gen_members(rng, stores, today, n=800):
    members, used = [], set()
    levels = [("青铜", 45), ("白银", 30), ("黄金", 18), ("黑金", 7)]
    for i in range(n):
        while True:
            nick = rng.choice(NICK_A) + rng.choice(NICK_B) if rng.random() < 0.7 else \
                rng.choice(SURNAMES) + rng.choice(["先生", "女士", "同学", "老师", "总"])
            if nick not in used:
                break
            nick += str(rng.randint(2, 99))
            if nick not in used:
                break
        used.add(nick)
        # 12% 会员是窗口期内注册的新会员
        if rng.random() < 0.12:
            reg = today - timedelta(days=rng.randint(0, DAYS - 1))
        else:
            reg = today - timedelta(days=rng.randint(DAYS, 900))
        home = rng.choice([s for s in stores if s["open_date"] <= reg] or stores)
        level = wchoice(rng, levels)
        prefs = rng.sample(["燕麦奶", "少糖", "冰饮", "手冲", "甜品控", "早餐党", "低咖啡因"], rng.randint(0, 3))
        members.append({
            "nick": nick, "card": "LY%08d" % (10000000 + i * 37 + rng.randint(0, 36)), "level": level,
            "gender": wchoice(rng, [("女", 58), ("男", 38), ("未知", 4)]),
            "age": wchoice(rng, [("18-24", 26), ("25-30", 38), ("31-40", 26), ("41+", 10)]),
            "reg": reg, "reg_channel": wchoice(rng, [("小程序", 50), ("门店扫码", 32), ("外卖平台", 12), ("企业团购", 6)]),
            "home": home, "phone": "1%d%09d" % (rng.choice([3, 5, 7, 8, 9]), rng.randint(0, 999999999)),
            "prefs": prefs, "balance": round(rng.choice([0, 0, 0, 50, 100, 200, 300, 500]) * rng.uniform(0.2, 1.0), 2),
            "points": rng.randint(0, 12000),
            "freq": {"青铜": 1, "白银": 2.2, "黄金": 4, "黑金": 7}[level],
        })
    return members


def _pick_items(rng, channel, hour, campaign_types):
    pool = [(p, p[7] * (1.6 if (p[5] and "新品尝鲜" in campaign_types) else 1.0) *
             (1.5 if "联名" in p[4] and "品牌联名" in campaign_types else 1.0) *
             (1.6 if p[1] in ("轻食", "烘焙") and hour < 10 else 1.0))
            for p in PRODUCTS]
    if channel == "企业团购":
        n_distinct = rng.randint(2, 4)
    else:
        n_distinct = wchoice(rng, [(1, 55), (2, 30), (3, 11), (4, 4)])
    picked = []
    names = set()
    while len(picked) < n_distinct:
        p = wchoice(rng, pool)
        if p[0] in names:
            continue
        names.add(p[0])
        qty = rng.randint(1, 3) if channel == "企业团购" else (2 if rng.random() < 0.12 else 1)
        picked.append((p, qty))
    return picked


def gen_order(rng, when, store, members_by_store, all_members, campaigns, seq, recent=False, month_cold=True):
    """生成一笔订单及其明细。返回 (order_dict, [item_dict])."""
    hour = when.hour
    channels = CHANNELS if store["delivery"] else [c for c in CHANNELS if c[0] in ("堂食", "到店自提", "企业团购")]
    if store["type"] == "快取店":
        channels = [(c, w * (0.2 if c == "堂食" else 1.0)) for c, w in channels]
    channel = wchoice(rng, channels)
    active = [c for c in campaigns if c["start"].date() <= when.date() <= c["end"].date()]
    if "周三会员日" in [c["name"] for c in active] and when.weekday() != 2:
        active = [c for c in active if c["name"] != "周三会员日"]
    if hour >= 10:
        active = [c for c in active if c["type"] != "时段套餐"]
    ctypes = {c["type"] for c in active}

    # 会员
    member = None
    if rng.random() < 0.58:
        local = members_by_store.get(store["name"]) or []
        cands = [m for m in (local if (local and rng.random() < 0.7) else all_members) if m["reg"] <= when]
        if cands:
            member = wchoice(rng, [(m, m["freq"]) for m in rng.sample(cands, min(25, len(cands)))])

    items = _pick_items(rng, channel, hour, ctypes)
    lines, total, cups = [], 0.0, 0
    for p, qty in items:
        name, cat, price, cost, tags, is_new, kcal, pop, is_drink = p
        spec = temp = sweet = None
        unit = float(price)
        if is_drink:
            spec = wchoice(rng, [("中杯", 50), ("大杯", 40), ("超大杯", 10)])
            unit += {"中杯": 0, "大杯": 3, "超大杯": 5}[spec]
            temp = wchoice(rng, [("热", 52 if month_cold else 25), ("冰", 28), ("少冰", 20)])
            sweet = wchoice(rng, [("标准糖", 35), ("少糖", 30), ("半糖", 15), ("无糖", 20)]) if cat != "手冲精品" else "无糖"
            cups += qty
        else:
            spec = "标准"
            temp = "常温" if cat in ("周边", "烘焙") else wchoice(rng, [("热", 60), ("常温", 40)])
        total += unit * qty
        lines.append({"product": name, "qty": qty, "unit": round(unit, 2), "spec": spec, "temp": temp, "sweet": sweet})

    # 优惠（只取一个最优活动）
    campaign, discount = None, 0.0
    if active and rng.random() < 0.55:
        c = rng.choice(active)
        if c["type"] == "会员日" and not member:
            c = None
        if c:
            if c["type"] == "满减":
                discount = 8.0 if total >= 50 else 0.0
            elif c["type"] == "第二杯半价":
                discount = (min(l["unit"] for l in lines) * 0.5) if cups >= 2 else 0.0
            elif c["type"] == "品牌联名":
                discount = total * 0.1
            else:
                discount = total * c["pct"] / 100.0 * rng.uniform(0.5, 1.0)
            if discount > 0:
                campaign = c
    discount = round(min(discount, total * 0.5), 2)
    paid = round(total - discount, 2)

    pay = "平台代收" if channel in ("美团外卖", "饿了么") else (
        "会员储值" if member and rng.random() < 0.35 else wchoice(rng, [("微信支付", 62), ("支付宝", 30), ("银行卡", 8)]))
    if channel == "企业团购":
        pay = "银行卡"

    if recent:
        status = "配送中" if channel in ("小程序外送", "美团外卖", "饿了么") else "制作中"
    else:
        status = wchoice(rng, [("已完成", 965), ("已退款", 20), ("已取消", 15)])
    rating = None
    if status == "已完成" and rng.random() < 0.35:
        rating = wchoice(rng, [(5, 60), (4, 28), (3, 8), (2, 3), (1, 1)])
    is_new = bool(member and member["reg"].date() == when.date()) or (not member and rng.random() < 0.06)
    order_no = "LY%s-%04d" % (when.strftime("%Y%m%d"), seq)
    order = {
        "no": order_no, "when": when, "store": store["name"], "member": member["card"] if member else None,
        "campaign": campaign["name"] if campaign else None, "channel": channel, "pay": pay, "status": status,
        "amount": round(total, 2), "discount": discount, "paid": paid, "cups": cups, "is_new": is_new,
        "rating": rating, "remark": rng.choice(REMARKS) if rng.random() < 0.12 else "",
    }
    for i, l in enumerate(lines):
        l["no"] = "%s-%d" % (order_no, i + 1)
        l["order"] = order_no
    return order, lines


def gen_orders(rng, stores, members, campaigns, now):
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    members_by_store = {}
    for m in members:
        members_by_store.setdefault(m["home"]["name"], []).append(m)
    orders, items = [], []
    for back in range(DAYS - 1, -1, -1):
        day = today - timedelta(days=back)
        trend = 0.88 + 0.24 * (DAYS - 1 - back) / (DAYS - 1)          # 期间整体增长约 25%
        weather = rng.uniform(0.85, 1.12)                                # 天气/随机波动
        golden_week = 0.75 if (day.month == 10 and 1 <= day.day <= 7) else 1.0
        seq = 0
        day_orders = []
        for s in stores:
            if s["open_date"] > day:
                continue
            if s["closed_from"] and day >= s["closed_from"]:
                continue
            wk = day.weekday()
            wfac = 1.0
            if wk >= 5:
                wfac = 0.55 if s["cbd"] else (0.5 if s["type"] == "校园店" else 1.18)
            newstore = 1.35 if (day - s["open_date"]).days < 7 else 1.0  # 开业首周热度
            gw = golden_week if s["cbd"] else (1.2 if day.month == 10 and day.day <= 7 else 1.0)
            lam = BASE_ORDERS_PER_STORE_DAY * s["weight"] * trend * weather * wfac * newstore * gw
            n = poissonish(rng, lam)
            for _ in range(n):
                hour = wchoice(rng, list(HOUR_WEIGHTS.items()))
                if s["cbd"] and wk >= 5:
                    hour = wchoice(rng, [(h, w) for h, w in HOUR_WEIGHTS.items() if h >= 10])
                when = day + timedelta(hours=hour, minutes=rng.randint(0, 59))
                if when > now:
                    continue
                day_orders.append((when, s))
        day_orders.sort(key=lambda x: x[0])
        for when, s in day_orders:
            seq += 1
            recent = (now - when) < timedelta(minutes=25)
            o, ls = gen_order(rng, when, s, members_by_store, members, campaigns, seq, recent=recent)
            orders.append(o)
            items.extend(ls)
    return orders, items


def generate_all(now=None):
    now = now or now_local()
    rng = random.Random(SEED)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    stores = gen_stores(rng, today)
    campaigns = gen_campaigns(today)
    members = gen_members(rng, stores, today)
    orders, items = gen_orders(rng, stores, members, campaigns, now)
    return {"stores": stores, "campaigns": campaigns, "members": members, "orders": orders, "items": items}


# --------------------------------------------------------------------------- row builders (Base CellValue)
def store_row(s):
    return {"门店名称": s["name"], "门店编码": s["code"], "城市": [s["city"]], "大区": [s["region"]],
            "门店类型": [s["type"]], "经营状态": [s["status"]], "开业日期": s["open_date"].strftime("%Y-%m-%d 00:00"),
            "店长": s["manager"], "联系电话": "1381%07d" % (sum(ord(ch) * 7919 for ch in s["code"]) % 10000000),
            "座位数": s["seats"], "月租金": s["rent"], "日营收目标": s["target"], "口碑评分": s["score"],
            "支持外卖": s["delivery"], "门店位置": {"lng": round(s["lng"], 6), "lat": round(s["lat"], 6)}}


def product_row(p, idx, today):
    name, cat, price, cost, tags, is_new, kcal, pop, is_drink = p
    launch = today - timedelta(days=(20 + idx * 3) if is_new else (200 + idx * 23))
    status = "在售"
    return {"商品名称": name, "商品编码": "SKU-%03d" % (idx + 1), "品类": [cat], "售价": price, "成本": cost,
            "标签": tags, "是否新品": is_new, "上市日期": launch.strftime("%Y-%m-%d 00:00"), "热量kcal": kcal,
            "销售状态": [status]}


def campaign_row(c, owner_open_id=None):
    row = {"活动名称": c["name"], "活动类型": [c["type"]], "开始日期": c["start"].strftime("%Y-%m-%d 00:00"),
           "结束日期": c["end"].strftime("%Y-%m-%d 00:00"), "活动预算": c["budget"], "折扣力度": c["pct"] / 100.0,
           "活动状态": [c["status"]], "活动说明": c["desc"]}
    return row


def member_row(m, store_ids):
    return {"会员昵称": m["nick"], "会员卡号": m["card"], "会员等级": [m["level"]], "性别": [m["gender"]],
            "年龄段": [m["age"]], "注册日期": m["reg"].strftime("%Y-%m-%d 00:00"), "注册渠道": [m["reg_channel"]],
            "归属门店": [{"id": store_ids[m["home"]["name"]]}], "手机号": m["phone"], "口味偏好": m["prefs"],
            "储值余额": m["balance"], "积分": m["points"]}


def order_row(o, store_ids, member_ids, campaign_ids):
    row = {"订单号": o["no"], "下单时间": fmt(o["when"]), "门店": [{"id": store_ids[o["store"]]}],
           "渠道": [o["channel"]], "支付方式": [o["pay"]], "订单状态": [o["status"]], "订单金额": o["amount"],
           "优惠金额": o["discount"], "实付金额": o["paid"], "杯数": o["cups"], "是否新客": o["is_new"]}
    if o["member"]:
        row["会员"] = [{"id": member_ids[o["member"]]}]
    if o["campaign"]:
        row["营销活动"] = [{"id": campaign_ids[o["campaign"]]}]
    if o["rating"]:
        row["评价星级"] = o["rating"]
    if o["remark"]:
        row["顾客备注"] = o["remark"]
    return row


def item_row(l, order_ids, product_ids):
    row = {"明细编号": l["no"], "订单": [{"id": order_ids[l["order"]]}], "商品": [{"id": product_ids[l["product"]]}],
           "数量": l["qty"], "单价": l["unit"], "规格": [l["spec"]], "温度": [l["temp"]]}
    if l["sweet"]:
        row["甜度"] = [l["sweet"]]
    return row
