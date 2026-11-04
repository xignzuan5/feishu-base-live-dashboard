import type { DashRange, ValueFormat } from '@shared/dashboard.interface';
import type { SpecLayout, SpecPanelKind } from '@shared/spec-board.interface';

/** 多维表格字段 → 应用数据库列（由 build_spec_bundle.py 根据同步映射生成） */
export interface SpecFieldMap {
  col: string;
  type: 'text' | 'number' | 'select' | 'multiselect' | 'datetime' | 'date' | 'checkbox' | 'link' | 'formula' | 'other';
  /** 关联字段的目标表（多维表格表名） */
  target?: string;
}

export interface SpecTableMap {
  pg: string;
  primary: string;
  fields: Record<string, SpecFieldMap>;
}

export interface SpecCondition {
  field: string;
  op: string;
  /** 取值；日期可写 {"exact_date_ms": 1700000000000} 或 {"relative": "today" | "now" | "-7d" | "+3d"} */
  value?: unknown;
}

export interface SpecMeasure {
  field?: string;
  agg: 'SUM' | 'AVERAGE' | 'MAX' | 'MIN' | 'COUNT' | 'COUNT_DISTINCT';
  label: string;
  /** 条件聚合：只统计满足条件的记录（如「已完成任务数」「逾期任务数」） */
  where?: SpecCondition[];
}

export interface SpecDimension {
  field: string;
  mode: 'integrated' | 'enumerated';
  /** 固定排序（如漏斗阶段、优先级）：按这个顺序输出，未列出的排在后面 */
  order?: string[];
  /** 关联字段专用：按对方表的这个字段分组（如 客户 → 行业），默认用对方主字段 */
  via?: string;
}

export interface SpecPanelDef {
  id: string;
  kind: SpecPanelKind;
  title: string;
  subtitle?: string;
  table?: string;
  measures: SpecMeasure[];
  dimensions: SpecDimension[];
  filter?: { conjunction: 'and' | 'or'; conditions: SpecCondition[] };
  sort?: { by: 'value' | 'dimension' | 'field'; field?: string; order: 'asc' | 'desc' };
  /** 记录清单模式（仅 table）：逐条列出这些字段，不做汇总；配合 filter / sort / limit */
  columns?: string[];
  limit?: number;
  /** ratio：指标卡取 m0 / m1（完成率、赢单率、SLA 达成率…） */
  compute?: 'ratio';
  /** 指标上升是好事还是坏事（逾期率上升是坏事） */
  goodWhen?: 'up' | 'down';
  /** 受时间范围控制的日期字段；null = 全量（与原仪表盘口径一致） */
  timeField: string | null;
  format: ValueFormat;
  chartTypes: string[];
  defaultChart?: string;
  layout?: SpecLayout;
  text?: string;
  notes: string[];
}

export interface SpecBoardDef {
  key: string;
  label: string;
  group: string;
  layout?: string;
  style?: string;
  description: string;
  defaultRange: DashRange;
  panels: SpecPanelDef[];
}

export interface SpecBundle {
  title: string;
  entities: string[][];
  timezone: string;
  boards: SpecBoardDef[];
  tables: Record<string, SpecTableMap>;
}
