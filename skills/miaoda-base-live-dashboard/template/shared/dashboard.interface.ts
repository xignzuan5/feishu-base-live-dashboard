/**
 * 实时看板：前后端共享契约
 *
 * 面板组件只认这里的几种「标准数据形状」，与业务表无关：
 *   KpiItem / TrendData / CategoryData / StackedData / HeatmapData / ScatterData /
 *   MeterData / FeedItem / TableData
 * 换一张多维表格时，只需让后端把查询结果整理成这些形状，前端面板全部复用。
 */

// ---------------------------------------------------------------- 筛选
export const DASH_RANGES = ['today', '7d', '30d', '90d'] as const;
export type DashRange = (typeof DASH_RANGES)[number];
export const isDashRange = (v: string): v is DashRange =>
  (DASH_RANGES as readonly string[]).includes(v);
export const DASH_RANGE_LABELS: Record<DashRange, string> = {
  today: '今日',
  '7d': '近 7 天',
  '30d': '近 30 天',
  '90d': '近 90 天',
};

export interface DashboardQuery {
  range?: DashRange;
  /** 城市筛选，不传表示全部 */
  city?: string;
}

// ---------------------------------------------------------------- 标准数据形状
export const VALUE_FORMATS = ['currency', 'number', 'percent', 'decimal'] as const;
export type ValueFormat = (typeof VALUE_FORMATS)[number];

export interface KpiItem {
  key: string;
  label: string;
  value: number;
  format: ValueFormat;
  /** 与对比周期的变化：currency/number 为相对变化率；percent 为百分点差 */
  delta: number | null;
  deltaLabel: string;
  /** 指标上升是好事还是坏事（退款率上升是坏事） */
  goodWhen: 'up' | 'down';
  /** 迷你走势（可选） */
  spark?: number[];
}

export interface SeriesPoint {
  x: string;
  y: number;
}

export interface TrendSeries {
  name: string;
  points: SeriesPoint[];
  /** 对比周期用虚线、弱化色 */
  compare?: boolean;
}

export interface TrendData {
  granularity: 'minute' | 'hour' | 'day';
  format: ValueFormat;
  series: TrendSeries[];
}

export interface CategoryItem {
  name: string;
  value: number;
  /** 次要数值（如订单数），tooltip 里展示 */
  secondary?: number;
}

export interface CategoryData {
  format: ValueFormat;
  secondaryLabel?: string;
  items: CategoryItem[];
}

export interface StackedData {
  format: ValueFormat;
  categories: string[];
  series: { name: string; values: number[] }[];
}

export interface HeatmapData {
  xLabels: string[];
  yLabels: string[];
  /** [xIndex, yIndex, value] */
  cells: [number, number, number][];
  format: ValueFormat;
}

export interface ScatterPoint {
  name: string;
  x: number;
  y: number;
  size: number;
  group: string;
}

export interface ScatterData {
  xLabel: string;
  yLabel: string;
  sizeLabel: string;
  xFormat: ValueFormat;
  yFormat: ValueFormat;
  points: ScatterPoint[];
}

export interface MeterData {
  label: string;
  value: number;
  target: number;
  format: ValueFormat;
}

export interface FeedItem {
  id: string;
  orderNo: string;
  time: string;
  store: string;
  city: string;
  channel: string;
  amount: number;
  status: string;
  summary: string;
  isMember: boolean;
}

export interface TableColumn {
  key: string;
  label: string;
  format?: ValueFormat | 'text' | 'meter' | 'status';
  align?: 'left' | 'right';
}

export type TableCell = string | number | null;

export interface TableData {
  columns: TableColumn[];
  rows: Record<string, TableCell>[];
}

export interface SyncStatus {
  /** 业务最新一条记录时间（多维表格里的下单时间） */
  lastRecordAt: string | null;
  /** 应用数据库最近一次被同步写入的时间 */
  lastSyncedAt: string | null;
  serverTime: string;
  totalRecords: number;
}

// ---------------------------------------------------------------- 各看板响应
export interface DashboardMeta {
  title: string;
  cities: string[];
  baseUrl: string;
  sync: SyncStatus;
}

export interface OverviewBoard {
  kpis: KpiItem[];
  trend: TrendData;
  channels: CategoryData;
  categories: CategoryData;
  heatmap: HeatmapData;
  cities: CategoryData;
  feed: FeedItem[];
  sync: SyncStatus;
}

export interface StoresBoard {
  kpis: KpiItem[];
  achievement: MeterData;
  leaderboard: TableData;
  regionByType: StackedData;
  topStoresTrend: TrendData;
  storeTypes: CategoryData;
  sync: SyncStatus;
}

export interface ProductsBoard {
  kpis: KpiItem[];
  topProducts: CategoryData;
  categories: CategoryData;
  priceMargin: ScatterData;
  temperatureMix: StackedData;
  hourlyByCategory: StackedData;
  sync: SyncStatus;
}

export interface MembersBoard {
  kpis: KpiItem[];
  levels: StackedData;
  ageGender: StackedData;
  memberTrend: TrendData;
  ratings: CategoryData;
  campaigns: TableData;
  sync: SyncStatus;
}

export interface LiveBoard {
  kpis: KpiItem[];
  lastHour: TrendData;
  todayVsYesterday: TrendData;
  cities: CategoryData;
  channels: CategoryData;
  topProducts: CategoryData;
  feed: FeedItem[];
  sync: SyncStatus;
}
