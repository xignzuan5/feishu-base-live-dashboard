import { Injectable, Logger } from '@nestjs/common';

import type {
  CategoryData,
  CategoryItem,
  DashboardMeta,
  DashRange,
  FeedItem,
  HeatmapData,
  KpiItem,
  LiveBoard,
  MembersBoard,
  OverviewBoard,
  ProductsBoard,
  StackedData,
  StoresBoard,
  SyncStatus,
  TableData,
  TrendData,
  TrendSeries,
  ValueFormat,
} from '@shared/dashboard.interface';

import { DASHBOARD_CONFIG } from './dashboard.config';
import {
  DashboardRepository,
  type BucketRow,
  type DimRow,
  type ProductAggRow,
  type Scope,
  type StoreAggRow,
  type Summary,
} from './dashboard.repository';
import { buildWindow, elapsedBusinessRatio, nowInTz, toIso, type TimeWindow } from './dashboard.time';

const WEEKDAYS: string[] = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
const LEVELS: string[] = ['青铜', '白银', '黄金', '黑金'];
const AGES: string[] = ['18-24', '25-30', '31-40', '41+'];
const GENDERS: string[] = ['女', '男', '未知'];
const DRINK_CATEGORIES: string[] = ['意式咖啡', '手冲精品', '茶饮'];
const TEMPERATURES: string[] = ['热', '冰', '少冰'];
const PRODUCT_CATEGORIES: string[] = ['意式咖啡', '手冲精品', '茶饮', '轻食', '烘焙', '周边'];

const ratio = (a: number, b: number): number => (b > 0 ? a / b : 0);
const change = (cur: number, prev: number): number | null => (prev > 0 ? (cur - prev) / prev : null);
const round2 = (n: number): number => Math.round(n * 100) / 100;

interface KpiSpec {
  key: string;
  label: string;
  format: ValueFormat;
  goodWhen: 'up' | 'down';
  pick: (s: Summary) => number;
}

const ORDER_KPIS: KpiSpec[] = [
  { key: 'revenue', label: '实付营收', format: 'currency', goodWhen: 'up', pick: (s: Summary) => s.revenue },
  { key: 'orders', label: '有效订单', format: 'number', goodWhen: 'up', pick: (s: Summary) => s.orders },
  {
    key: 'avgTicket',
    label: '客单价',
    format: 'currency',
    goodWhen: 'up',
    pick: (s: Summary) => ratio(s.revenue, s.orders),
  },
  { key: 'cups', label: '出杯数', format: 'number', goodWhen: 'up', pick: (s: Summary) => s.cups },
  {
    key: 'memberShare',
    label: '会员订单占比',
    format: 'percent',
    goodWhen: 'up',
    pick: (s: Summary) => ratio(s.memberOrders, s.orders),
  },
  {
    key: 'refundRate',
    label: '退款率',
    format: 'percent',
    goodWhen: 'down',
    pick: (s: Summary) => ratio(s.refunds, s.allOrders),
  },
];

@Injectable()
export class DashboardService {
  private readonly logger = new Logger(DashboardService.name);

  constructor(private readonly repo: DashboardRepository) {}

  // ------------------------------------------------------------ helpers
  private scopes(w: TimeWindow, city?: string): { cur: Scope; prev: Scope } {
    return {
      cur: { start: w.start, end: w.end, city },
      prev: { start: w.prevStart, end: w.prevEnd, city },
    };
  }

  private kpis(specs: KpiSpec[], cur: Summary, prev: Summary, w: TimeWindow): KpiItem[] {
    return specs.map((spec: KpiSpec) => {
      const v: number = spec.pick(cur);
      const p: number = spec.pick(prev);
      const delta: number | null = spec.format === 'percent' ? v - p : change(v, p);
      return {
        key: spec.key,
        label: spec.label,
        value: round2(v * (spec.format === 'percent' ? 100 : 1)) / (spec.format === 'percent' ? 100 : 1),
        format: spec.format,
        delta,
        deltaLabel: w.deltaLabel,
        goodWhen: spec.goodWhen,
      };
    });
  }

  private bucketSeries(
    w: TimeWindow,
    cur: BucketRow[],
    prev: BucketRow[] | null,
    pick: (r: BucketRow) => number,
    names: [string, string],
  ): TrendSeries[] {
    const curMap = new Map<string, number>(cur.map((r: BucketRow) => [r.bucket, pick(r)]));
    const nowHour: number = nowInTz().hour();
    const keys: string[] =
      w.granularity === 'hour' ? w.bucketKeys.filter((k: string) => Number(k) <= nowHour) : w.bucketKeys;
    const series: TrendSeries[] = [
      {
        name: names[0],
        points: keys.map((k: string, i: number) => ({ x: w.bucketLabels[i], y: round2(curMap.get(k) ?? 0) })),
      },
    ];
    if (prev) {
      const prevMap = new Map<string, number>(prev.map((r: BucketRow) => [r.bucket, pick(r)]));
      series.push({
        name: names[1],
        compare: true,
        points: w.prevBucketKeys.map((k: string, i: number) => ({
          x: w.bucketLabels[i],
          y: round2(prevMap.get(k) ?? 0),
        })),
      });
    }
    return series;
  }

  private dimToCategory(rows: DimRow[], by: 'revenue' | 'orders', secondaryLabel: string): CategoryData {
    return {
      format: by === 'revenue' ? 'currency' : 'number',
      secondaryLabel,
      items: rows
        .map((r: DimRow) => ({
          name: r.name,
          value: round2(by === 'revenue' ? r.revenue : r.orders),
          secondary: by === 'revenue' ? r.orders : round2(r.revenue),
        }))
        .sort((a: CategoryItem, b: CategoryItem) => b.value - a.value),
    };
  }

  private async sync(): Promise<SyncStatus> {
    const s = await this.repo.syncStatus();
    return {
      lastRecordAt: toIso(s.lastRecordAt),
      lastSyncedAt: toIso(s.lastSyncedAt),
      serverTime: new Date().toISOString(),
      totalRecords: s.total,
    };
  }

  private async feed(limit: number, city?: string): Promise<FeedItem[]> {
    const rows = await this.repo.latestOrders(limit, city);
    const summaries = await this.repo.orderSummaries(rows.map((r) => r.id));
    return rows.map((r) => ({
      id: r.id,
      orderNo: r.orderNo,
      time: toIso(r.orderedAt) ?? '',
      store: r.store.replace('鹿野咖啡·', ''),
      city: r.city,
      channel: r.channel,
      amount: round2(r.amount),
      status: r.status,
      summary: summaries.get(r.id) ?? '',
      isMember: r.isMember,
    }));
  }

  /** 窗口目标：多日 = 日目标 × 天数；今日 = 日目标 × 截至此刻的历史营收占比 */
  private storeTarget(row: StoreAggRow, w: TimeWindow, todayShare: number): number {
    const days: number = w.granularity === 'hour' ? todayShare : w.days;
    return row.dailyTarget * days;
  }

  // ------------------------------------------------------------ boards
  async meta(): Promise<DashboardMeta> {
    const [cities, sync] = await Promise.all([this.repo.cities(), this.sync()]);
    return { title: DASHBOARD_CONFIG.title, cities, baseUrl: DASHBOARD_CONFIG.baseUrl, sync };
  }

  async overview(range: DashRange, city?: string): Promise<OverviewBoard> {
    const w: TimeWindow = buildWindow(range);
    const { cur, prev } = this.scopes(w, city);
    const heatWindow: TimeWindow = buildWindow('30d');
    const [sCur, sPrev, bCur, bPrev, channels, citiesRows, products, matrix, feed, sync] = await Promise.all([
      this.repo.summary(cur),
      this.repo.summary(prev),
      this.repo.buckets(cur, w.granularity),
      this.repo.buckets(prev, w.granularity),
      this.repo.byDimension(cur, this.repo.dims.channel),
      this.repo.byDimension(cur, this.repo.dims.city),
      this.repo.productAgg(cur),
      this.repo.weekHourMatrix({ start: heatWindow.start, end: heatWindow.end, city }),
      this.feed(20, city),
      this.sync(),
    ]);
    const catMap = new Map<string, { revenue: number; qty: number }>();
    for (const p of products) {
      const c = catMap.get(p.category) ?? { revenue: 0, qty: 0 };
      c.revenue += p.revenue;
      c.qty += p.qty;
      catMap.set(p.category, c);
    }
    const trend: TrendData = {
      granularity: w.granularity,
      format: 'currency',
      series: this.bucketSeries(w, bCur, bPrev, (r: BucketRow) => r.revenue, [
        '营收',
        range === 'today' ? '昨日' : '上一周期',
      ]),
    };
    return {
      kpis: this.kpis(ORDER_KPIS, sCur, sPrev, w),
      trend,
      channels: this.dimToCategory(channels, 'revenue', '订单数'),
      categories: {
        format: 'currency',
        secondaryLabel: '销量（件）',
        items: Array.from(catMap.entries())
          .map(([name, v]) => ({ name, value: round2(v.revenue), secondary: v.qty }))
          .sort((a: CategoryItem, b: CategoryItem) => b.value - a.value),
      },
      heatmap: this.heatmap(matrix),
      cities: this.dimToCategory(citiesRows, 'revenue', '订单数'),
      feed,
      sync,
    };
  }

  private heatmap(matrix: { dow: number; hour: number; orders: number }[]): HeatmapData {
    const { open, close } = DASHBOARD_CONFIG.businessHours;
    const hours: number[] = [];
    for (let h = open; h < close; h += 1) hours.push(h);
    const cells: [number, number, number][] = [];
    const lookup = new Map<string, number>(
      matrix.map((m: { dow: number; hour: number; orders: number }) => [`${m.dow}-${m.hour}`, m.orders]),
    );
    hours.forEach((h: number, x: number) => {
      WEEKDAYS.forEach((_d: string, y: number) => {
        cells.push([x, y, lookup.get(`${y + 1}-${h}`) ?? 0]);
      });
    });
    return {
      xLabels: hours.map((h: number) => `${String(h).padStart(2, '0')}时`),
      yLabels: WEEKDAYS,
      cells,
      format: 'number',
    };
  }

  async stores(range: DashRange, city?: string): Promise<StoresBoard> {
    const w: TimeWindow = buildWindow(range);
    const { cur, prev } = this.scopes(w, city);
    const [rows, prevRows, sync, share] = await Promise.all([
      this.repo.storeAgg(cur),
      this.repo.storeAgg(prev),
      this.sync(),
      w.granularity === 'hour' ? this.repo.timeOfDayShare(nowInTz().format('HH:mm:ss'), city) : Promise.resolve(1),
    ]);
    const todayShare: number = share ?? elapsedBusinessRatio();
    const open: StoreAggRow[] = rows.filter((r: StoreAggRow) => r.status !== '装修升级');
    const revenue: number = rows.reduce((a: number, r: StoreAggRow) => a + r.revenue, 0);
    const prevRevenue: number = prevRows.reduce((a: number, r: StoreAggRow) => a + r.revenue, 0);
    const target: number = open.reduce((a: number, r: StoreAggRow) => a + this.storeTarget(r, w, todayShare), 0);
    const prevTarget: number = target;
    const ordersN: number = rows.reduce((a: number, r: StoreAggRow) => a + r.orders, 0);
    const prevOrdersN: number = prevRows.reduce((a: number, r: StoreAggRow) => a + r.orders, 0);
    const avgRating: number = ratio(
      rows.reduce((a: number, r: StoreAggRow) => a + r.ratingScore, 0),
      rows.length,
    );
    const kpis: KpiItem[] = [
      {
        key: 'openStores', label: '营业门店', value: open.length, format: 'number',
        delta: null, deltaLabel: `共 ${rows.length} 家`, goodWhen: 'up',
      },
      {
        key: 'revenue', label: '门店总营收', value: round2(revenue), format: 'currency',
        delta: change(revenue, prevRevenue), deltaLabel: w.deltaLabel, goodWhen: 'up',
      },
      {
        key: 'perStore', label: '店均营收', value: round2(ratio(revenue, open.length)), format: 'currency',
        delta: change(ratio(revenue, open.length), ratio(prevRevenue, open.length)),
        deltaLabel: w.deltaLabel, goodWhen: 'up',
      },
      {
        key: 'achievement', label: '目标达成率', value: ratio(revenue, target), format: 'percent',
        delta: ratio(revenue, target) - ratio(prevRevenue, prevTarget), deltaLabel: w.deltaLabel, goodWhen: 'up',
      },
      {
        key: 'storeOrders', label: '门店订单', value: ordersN, format: 'number',
        delta: change(ordersN, prevOrdersN), deltaLabel: w.deltaLabel, goodWhen: 'up',
      },
      {
        key: 'rating', label: '平均口碑分', value: round2(avgRating), format: 'decimal',
        delta: null, deltaLabel: '满分 5.0', goodWhen: 'up',
      },
    ];
    const sorted: StoreAggRow[] = [...rows].sort((a: StoreAggRow, b: StoreAggRow) => b.revenue - a.revenue);
    const leaderboard: TableData = {
      columns: [
        { key: 'rank', label: '排名', format: 'number' },
        { key: 'name', label: '门店', format: 'text' },
        { key: 'city', label: '城市', format: 'text' },
        { key: 'storeType', label: '类型', format: 'text' },
        { key: 'status', label: '状态', format: 'status' },
        { key: 'revenue', label: '营收', format: 'currency', align: 'right' },
        { key: 'orders', label: '订单', format: 'number', align: 'right' },
        { key: 'avgTicket', label: '客单价', format: 'currency', align: 'right' },
        { key: 'achievement', label: '目标达成', format: 'meter' },
        { key: 'rating', label: '口碑', format: 'decimal', align: 'right' },
      ],
      rows: sorted.map((r: StoreAggRow, i: number) => ({
        rank: i + 1,
        name: r.name.replace('鹿野咖啡·', ''),
        city: r.city,
        storeType: r.storeType,
        status: r.status,
        revenue: round2(r.revenue),
        orders: r.orders,
        avgTicket: round2(ratio(r.revenue, r.orders)),
        achievement:
          r.status === '装修升级' ? null : round2(ratio(r.revenue, this.storeTarget(r, w, todayShare)) * 1000) / 1000,
        rating: r.ratingScore,
      })),
    };
    const regions: string[] = Array.from(new Set(rows.map((r: StoreAggRow) => r.region))).sort();
    const types: string[] = ['旗舰店', '标准店', '快取店', '校园店'];
    const regionByType: StackedData = {
      format: 'currency',
      categories: regions,
      series: types.map((t: string) => ({
        name: t,
        values: regions.map((rg: string) =>
          round2(rows.filter((r: StoreAggRow) => r.region === rg && r.storeType === t)
            .reduce((a: number, r: StoreAggRow) => a + r.revenue, 0)),
        ),
      })),
    };
    const top5: StoreAggRow[] = sorted.slice(0, 5);
    const buckets = await this.repo.storeBuckets(cur, w.granularity, top5.map((r: StoreAggRow) => r.id));
    const nowHour: number = nowInTz().hour();
    const keys: string[] =
      w.granularity === 'hour' ? w.bucketKeys.filter((k: string) => Number(k) <= nowHour) : w.bucketKeys;
    const topStoresTrend: TrendData = {
      granularity: w.granularity,
      format: 'currency',
      series: top5.map((s: StoreAggRow) => {
        const m = new Map<string, number>(
          buckets.filter((b) => b.storeId === s.id).map((b) => [b.bucket, b.revenue]),
        );
        return {
          name: s.name.replace('鹿野咖啡·', ''),
          points: keys.map((k: string, i: number) => ({ x: w.bucketLabels[i], y: round2(m.get(k) ?? 0) })),
        };
      }),
    };
    const typeItems: CategoryItem[] = types
      .map((t: string) => {
        const group: StoreAggRow[] = open.filter((r: StoreAggRow) => r.storeType === t);
        const total: number = group.reduce((a: number, r: StoreAggRow) => a + r.revenue, 0);
        return { name: t, value: round2(ratio(total, group.length)), secondary: group.length };
      })
      .filter((it: CategoryItem) => (it.secondary ?? 0) > 0);
    return {
      kpis,
      achievement: { label: '整体目标达成', value: round2(revenue), target: round2(target), format: 'currency' },
      leaderboard,
      regionByType,
      topStoresTrend,
      storeTypes: { format: 'currency', secondaryLabel: '门店数', items: typeItems },
      sync,
    };
  }

  async products(range: DashRange, city?: string): Promise<ProductsBoard> {
    const w: TimeWindow = buildWindow(range);
    const { cur, prev } = this.scopes(w, city);
    const [rows, prevRows, temp, hourly, sync] = await Promise.all([
      this.repo.productAgg(cur),
      this.repo.productAgg(prev),
      this.repo.itemCross(cur, this.repo.itemDims.category, this.repo.itemDims.temperature),
      this.repo.itemCross(cur, this.repo.itemDims.hour, this.repo.itemDims.category),
      this.sync(),
    ]);
    const sum = (list: ProductAggRow[], f: (p: ProductAggRow) => number): number =>
      list.reduce((a: number, p: ProductAggRow) => a + f(p), 0);
    const qty: number = sum(rows, (p: ProductAggRow) => p.qty);
    const prevQty: number = sum(prevRows, (p: ProductAggRow) => p.qty);
    const rev: number = sum(rows, (p: ProductAggRow) => p.revenue);
    const prevRev: number = sum(prevRows, (p: ProductAggRow) => p.revenue);
    const cost: number = sum(rows, (p: ProductAggRow) => p.cost * p.qty);
    const prevCost: number = sum(prevRows, (p: ProductAggRow) => p.cost * p.qty);
    const newQty: number = sum(rows.filter((p: ProductAggRow) => p.isNew), (p: ProductAggRow) => p.qty);
    const prevNewQty: number = sum(prevRows.filter((p: ProductAggRow) => p.isNew), (p: ProductAggRow) => p.qty);
    const active: number = rows.filter((p: ProductAggRow) => p.qty > 0).length;
    const prevActive: number = prevRows.filter((p: ProductAggRow) => p.qty > 0).length;
    const kpis: KpiItem[] = [
      { key: 'qty', label: '商品销量', value: qty, format: 'number', delta: change(qty, prevQty), deltaLabel: w.deltaLabel, goodWhen: 'up' },
      { key: 'rev', label: '商品销售额', value: round2(rev), format: 'currency', delta: change(rev, prevRev), deltaLabel: w.deltaLabel, goodWhen: 'up' },
      { key: 'margin', label: '加权毛利率', value: ratio(rev - cost, rev), format: 'percent', delta: ratio(rev - cost, rev) - ratio(prevRev - prevCost, prevRev), deltaLabel: w.deltaLabel, goodWhen: 'up' },
      { key: 'newShare', label: '新品销量占比', value: ratio(newQty, qty), format: 'percent', delta: ratio(newQty, qty) - ratio(prevNewQty, prevQty), deltaLabel: w.deltaLabel, goodWhen: 'up' },
      { key: 'active', label: '动销 SKU', value: active, format: 'number', delta: change(active, prevActive), deltaLabel: w.deltaLabel, goodWhen: 'up' },
      { key: 'perOrder', label: '件单价', value: round2(ratio(rev, qty)), format: 'currency', delta: change(ratio(rev, qty), ratio(prevRev, prevQty)), deltaLabel: w.deltaLabel, goodWhen: 'up' },
    ];
    const top: ProductAggRow[] = [...rows].sort((a: ProductAggRow, b: ProductAggRow) => b.qty - a.qty).slice(0, 10);
    const catMap = new Map<string, number>();
    rows.forEach((p: ProductAggRow) => catMap.set(p.category, (catMap.get(p.category) ?? 0) + p.revenue));
    const tempMap = new Map<string, number>(temp.map((t) => [`${t.a}|${t.b}`, t.qty]));
    const hourMap = new Map<string, number>(hourly.map((t) => [`${t.a}|${t.b}`, t.qty]));
    const { open, close } = DASHBOARD_CONFIG.businessHours;
    const hours: string[] = [];
    for (let h = open; h < close; h += 1) hours.push(String(h).padStart(2, '0'));
    return {
      kpis,
      topProducts: {
        format: 'number',
        secondaryLabel: '销售额',
        items: top.map((p: ProductAggRow) => ({ name: p.name, value: p.qty, secondary: round2(p.revenue) })),
      },
      categories: {
        format: 'currency',
        items: Array.from(catMap.entries())
          .map(([name, value]) => ({ name, value: round2(value) }))
          .sort((a: CategoryItem, b: CategoryItem) => b.value - a.value),
      },
      priceMargin: {
        xLabel: '售价',
        yLabel: '毛利率',
        sizeLabel: '销量',
        xFormat: 'currency',
        yFormat: 'percent',
        points: rows.map((p: ProductAggRow) => ({
          name: p.name,
          x: p.price,
          y: round2(ratio(p.price - p.cost, p.price) * 1000) / 1000,
          size: p.qty,
          group: p.category,
        })),
      },
      temperatureMix: {
        format: 'number',
        categories: DRINK_CATEGORIES,
        series: TEMPERATURES.map((t: string) => ({
          name: t,
          values: DRINK_CATEGORIES.map((c: string) => tempMap.get(`${c}|${t}`) ?? 0),
        })),
      },
      hourlyByCategory: {
        format: 'number',
        categories: hours.map((h: string) => `${h}时`),
        series: PRODUCT_CATEGORIES.map((c: string) => ({
          name: c,
          values: hours.map((h: string) => hourMap.get(`${h}|${c}`) ?? 0),
        })),
      },
      sync,
    };
  }

  async members(range: DashRange, city?: string): Promise<MembersBoard> {
    const w: TimeWindow = buildWindow(range);
    const { cur, prev } = this.scopes(w, city);
    const [sCur, sPrev, activeCur, activePrev, newCur, newPrev, levels, ageGender, memberB, guestB, ratings, camp, sync] =
      await Promise.all([
        this.repo.summary(cur),
        this.repo.summary(prev),
        this.repo.activeMemberCount(cur),
        this.repo.activeMemberCount(prev),
        this.repo.newMemberCount(w.start, w.end),
        this.repo.newMemberCount(w.prevStart, w.prevEnd),
        this.repo.memberLevels(cur),
        this.repo.memberAgeGender(),
        this.repo.buckets(cur, w.granularity, true),
        this.repo.buckets(cur, w.granularity, false),
        this.repo.byDimension(cur, this.repo.dims.rating),
        this.repo.campaignAgg(city),
        this.sync(),
      ]);
    const memberTicket: number = ratio(sCur.revenue, sCur.orders);
    const kpis: KpiItem[] = [
      { key: 'memberShare', label: '会员订单占比', value: ratio(sCur.memberOrders, sCur.orders), format: 'percent', delta: ratio(sCur.memberOrders, sCur.orders) - ratio(sPrev.memberOrders, sPrev.orders), deltaLabel: w.deltaLabel, goodWhen: 'up' },
      { key: 'activeMembers', label: '活跃会员', value: activeCur, format: 'number', delta: change(activeCur, activePrev), deltaLabel: w.deltaLabel, goodWhen: 'up' },
      { key: 'newMembers', label: '新注册会员', value: newCur, format: 'number', delta: change(newCur, newPrev), deltaLabel: w.deltaLabel, goodWhen: 'up' },
      { key: 'newCustomers', label: '新客订单', value: sCur.newCustomers, format: 'number', delta: change(sCur.newCustomers, sPrev.newCustomers), deltaLabel: w.deltaLabel, goodWhen: 'up' },
      { key: 'discount', label: '营销让利', value: round2(sCur.discount), format: 'currency', delta: change(sCur.discount, sPrev.discount), deltaLabel: w.deltaLabel, goodWhen: 'down' },
      { key: 'ticket', label: '整体客单价', value: round2(memberTicket), format: 'currency', delta: change(memberTicket, ratio(sPrev.revenue, sPrev.orders)), deltaLabel: w.deltaLabel, goodWhen: 'up' },
    ];
    const levelMap = new Map<string, { total: number; active: number }>(
      levels.map((l) => [l.level, { total: l.total, active: l.active }]),
    );
    const agMap = new Map<string, number>(ageGender.map((a) => [`${a.age}|${a.gender}`, a.total]));
    const ratingItems: CategoryItem[] = [5, 4, 3, 2, 1].map((star: number) => {
      const row: DimRow | undefined = ratings.find((r: DimRow) => r.name === String(star));
      return { name: `${star} 星`, value: row?.orders ?? 0 };
    });
    const campaigns: TableData = {
      columns: [
        { key: 'name', label: '活动', format: 'text' },
        { key: 'type', label: '类型', format: 'text' },
        { key: 'status', label: '状态', format: 'status' },
        { key: 'orders', label: '带动订单', format: 'number', align: 'right' },
        { key: 'revenue', label: '带动营收', format: 'currency', align: 'right' },
        { key: 'discount', label: '让利', format: 'currency', align: 'right' },
        { key: 'roi', label: '投入产出比', format: 'decimal', align: 'right' },
        { key: 'budgetUse', label: '预算消耗', format: 'meter' },
      ],
      rows: camp.map((c) => ({
        name: c.name,
        type: c.type,
        status: c.status,
        orders: c.orders,
        revenue: round2(c.revenue),
        discount: round2(c.discount),
        roi: round2(ratio(c.revenue, c.discount)),
        budgetUse: c.budget > 0 ? round2((c.discount / c.budget) * 1000) / 1000 : null,
      })),
    };
    return {
      kpis,
      levels: {
        format: 'number',
        categories: LEVELS,
        series: [
          { name: '会员总数', values: LEVELS.map((l: string) => levelMap.get(l)?.total ?? 0) },
          { name: '窗口内活跃', values: LEVELS.map((l: string) => levelMap.get(l)?.active ?? 0) },
        ],
      },
      ageGender: {
        format: 'number',
        categories: AGES,
        series: GENDERS.map((g: string) => ({ name: g, values: AGES.map((a: string) => agMap.get(`${a}|${g}`) ?? 0) })),
      },
      memberTrend: {
        granularity: w.granularity,
        format: 'number',
        series: [
          ...this.bucketSeries(w, memberB, null, (r: BucketRow) => r.orders, ['会员订单', '']),
          ...this.bucketSeries(w, guestB, null, (r: BucketRow) => r.orders, ['非会员订单', '']),
        ],
      },
      ratings: { format: 'number', items: ratingItems },
      campaigns,
      sync,
    };
  }

  async live(city?: string): Promise<LiveBoard> {
    const w: TimeWindow = buildWindow('today');
    const { cur, prev } = this.scopes(w, city);
    const since: Date = new Date(Date.now() - 60 * 60 * 1000);
    const [sCur, sPrev, bCur, bPrev, cities, channels, products, times, feed, sync] = await Promise.all([
      this.repo.summary(cur),
      this.repo.summary(prev),
      this.repo.buckets(cur, 'hour'),
      this.repo.buckets(prev, 'hour'),
      this.repo.byDimension(cur, this.repo.dims.city),
      this.repo.byDimension(cur, this.repo.dims.channel),
      this.repo.productAgg(cur),
      this.repo.recentOrderTimes(since, city),
      this.feed(30, city),
      this.sync(),
    ]);
    const slots: number[] = new Array<number>(12).fill(0);
    times.forEach((t: Date) => {
      const idx: number = Math.floor((t.getTime() - since.getTime()) / (5 * 60 * 1000));
      if (idx >= 0 && idx < 12) slots[idx] += 1;
    });
    const lastHour: TrendData = {
      granularity: 'minute',
      format: 'number',
      series: [
        {
          name: '每 5 分钟订单',
          points: slots.map((v: number, i: number) => {
            const t: Date = new Date(since.getTime() + (i + 1) * 5 * 60 * 1000);
            const label: string = nowInTz().subtract(Date.now() - t.getTime(), 'millisecond').format('HH:mm');
            return { x: label, y: v };
          }),
        },
      ],
    };
    const top: ProductAggRow[] = [...products].sort((a: ProductAggRow, b: ProductAggRow) => b.qty - a.qty).slice(0, 8);
    return {
      kpis: this.kpis(ORDER_KPIS.slice(0, 4), sCur, sPrev, w),
      lastHour,
      todayVsYesterday: {
        granularity: 'hour',
        format: 'currency',
        series: this.bucketSeries(w, bCur, bPrev, (r: BucketRow) => r.revenue, ['今日', '昨日']),
      },
      cities: this.dimToCategory(cities, 'revenue', '订单数'),
      channels: this.dimToCategory(channels, 'orders', '营收'),
      topProducts: {
        format: 'number',
        secondaryLabel: '销售额',
        items: top.map((p: ProductAggRow) => ({ name: p.name, value: p.qty, secondary: round2(p.revenue) })),
      },
      feed,
      sync,
    };
  }
}
