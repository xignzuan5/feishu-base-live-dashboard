/**
 * 「需求说明驱动」的看板（Spec Board）契约。
 *
 * dashboard-spec.json（由会议整理 / 多维表格仪表盘迁移 / 现场问答产出）经 build_spec_bundle.py
 * 编译成 server/modules/spec-board/spec.generated.ts，服务端按它生成 SQL，前端按它布局渲染。
 * 不需要为每个看板手写查询代码。
 */
import type {
  CategoryData,
  DashRange,
  KpiItem,
  StackedData,
  SyncStatus,
  TableData,
  TrendData,
  ValueFormat,
} from './dashboard.interface';

export const SPEC_PANEL_KINDS = ['kpi', 'trend', 'category', 'stacked', 'table', 'text'] as const;
export type SpecPanelKind = (typeof SPEC_PANEL_KINDS)[number];

export interface SpecLayout {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface SpecPanelMeta {
  id: string;
  kind: SpecPanelKind;
  title: string;
  subtitle?: string;
  layout?: SpecLayout;
  chartTypes: string[];
  defaultChart?: string;
  format: ValueFormat;
  /** 受看板时间范围控制 */
  hasTime: boolean;
  notes: string[];
}

export interface SpecBoardMeta {
  key: string;
  label: string;
  /** 模板中心分组（行业 / 来源），如「工作管理」「客户管理」「多维表格迁移」 */
  group: string;
  /** 推荐排版与风格（需求说明里给的默认值） */
  layout?: string;
  style?: string;
  description: string;
  defaultRange: DashRange;
  hasTimeFilter: boolean;
  panels: SpecPanelMeta[];
}

export interface SpecBoardsMeta {
  title: string;
  /** 实体固定配色组：同组取值按顺序占用分类色槽位，所有图同色 */
  entities: string[][];
  boards: SpecBoardMeta[];
}

export type SpecPanelData =
  | { kind: 'kpi'; kpi: KpiItem }
  | { kind: 'trend'; trend: TrendData }
  | { kind: 'category'; category: CategoryData }
  | { kind: 'stacked'; stacked: StackedData }
  | { kind: 'table'; table: TableData }
  | { kind: 'text'; text: string }
  /** message 是给用户看的友好文案；ref 用于对照服务端日志；detail 仅开发环境返回，前端只打到控制台 */
  | { kind: 'error'; message: string; ref: string; detail?: string };

export interface SpecBoardData {
  key: string;
  panels: Record<string, SpecPanelData>;
  sync: SyncStatus | null;
  generatedAt: string;
}

export interface SpecBoardQuery {
  range?: DashRange;
}
