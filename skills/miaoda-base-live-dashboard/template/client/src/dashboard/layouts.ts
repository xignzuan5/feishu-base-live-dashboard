import type { SpecPanelMeta } from '@shared/spec-board.interface';

/**
 * 排版类型（版式）：同一组面板，按「角色」重新编排。
 * 角色：kpi 指标卡 / hero 主图（第一个趋势或多系列图）/ side 构成排行 / wide 表格与多系列 / note 文本说明
 */
export const LAYOUTS = ['original', 'executive', 'command', 'grid', 'workbench', 'scorecard', 'magazine', 'focus'] as const;
export type LayoutKey = (typeof LAYOUTS)[number];
export const isLayoutKey = (v: string): v is LayoutKey => (LAYOUTS as readonly string[]).includes(v);

export interface LayoutMeta {
  key: LayoutKey;
  label: string;
  description: string;
  /** 12 栅格示意，给版式选择器画缩略图：[x, y, w, h] */
  sketch: [number, number, number, number][];
}

export const LAYOUT_META: Record<LayoutKey, LayoutMeta> = {
  original: {
    key: 'original',
    label: '原始布局',
    description: '沿用需求说明 / 原仪表盘里的坐标',
    sketch: [[0, 0, 6, 2], [6, 0, 6, 2], [0, 2, 4, 4], [4, 2, 4, 4], [8, 2, 4, 4]],
  },
  executive: {
    key: 'executive',
    label: '管理层简报',
    description: '顶部指标带 → 一张主图 → 两列明细，适合周会汇报',
    sketch: [[0, 0, 3, 1], [3, 0, 3, 1], [6, 0, 3, 1], [9, 0, 3, 1], [0, 1, 12, 3], [0, 4, 6, 3], [6, 4, 6, 3]],
  },
  command: {
    key: 'command',
    label: '指挥中心',
    description: '左指标、中主图、右排行，三栏一屏看全，适合值守与投屏',
    sketch: [[0, 0, 3, 2], [0, 2, 3, 2], [0, 4, 3, 2], [3, 0, 6, 4], [3, 4, 6, 2], [9, 0, 3, 3], [9, 3, 3, 3]],
  },
  grid: {
    key: 'grid',
    label: '分析工作台',
    description: '指标带 + 三列等宽卡片，信息密度最高，适合分析排查',
    sketch: [[0, 0, 12, 1], [0, 1, 4, 2], [4, 1, 4, 2], [8, 1, 4, 2], [0, 3, 4, 2], [4, 3, 4, 2], [8, 3, 4, 2]],
  },
  workbench: {
    key: 'workbench',
    label: '个人工作台',
    description: '待办指标在上，主列表占大半屏，右侧放提醒与分布，适合个人与小组每日查看',
    sketch: [[0, 0, 3, 1], [3, 0, 3, 1], [6, 0, 3, 1], [9, 0, 3, 1], [0, 1, 8, 4], [8, 1, 4, 2], [8, 3, 4, 2], [0, 5, 6, 2], [6, 5, 6, 2]],
  },
  scorecard: {
    key: 'scorecard',
    label: '记分对比',
    description: '三张大指标卡 + 一张横贯全屏的记分表，再接一排小图，适合排名与达成对比',
    sketch: [[0, 0, 4, 1], [4, 0, 4, 1], [8, 0, 4, 1], [0, 1, 12, 3], [0, 4, 3, 2], [3, 4, 3, 2], [6, 4, 3, 2], [9, 4, 3, 2]],
  },
  magazine: {
    key: 'magazine',
    label: '杂志式',
    description: '大图 + 说明并排、长短交错，适合对外展示与讲故事',
    sketch: [[0, 0, 8, 3], [8, 0, 4, 3], [0, 3, 5, 3], [5, 3, 7, 3], [0, 6, 7, 3], [7, 6, 5, 3]],
  },
  focus: {
    key: 'focus',
    label: '单列聚焦',
    description: '居中单列长页，适合手机查看、导出长图',
    sketch: [[3, 0, 6, 1], [3, 1, 6, 2], [3, 3, 6, 2], [3, 5, 6, 2]],
  },
};

export type PanelRole = 'kpi' | 'hero' | 'side' | 'wide' | 'note';

export const roleOf = (p: SpecPanelMeta, heroId: string | undefined): PanelRole => {
  if (p.kind === 'kpi') return 'kpi';
  if (p.kind === 'text') return 'note';
  if (p.id === heroId) return 'hero';
  if (p.kind === 'table' || p.kind === 'stacked') return 'wide';
  return 'side';
};

export const pickHero = (panels: SpecPanelMeta[]): string | undefined =>
  (panels.find((p: SpecPanelMeta) => p.kind === 'trend') ?? panels.find((p: SpecPanelMeta) => p.kind === 'stacked'))?.id;

/** Tailwind 需要静态类名，按跨度查表 */
export const XL_SPAN: Record<number, string> = {
  1: 'xl:col-span-1',
  2: 'xl:col-span-2',
  3: 'xl:col-span-3',
  4: 'xl:col-span-4',
  5: 'xl:col-span-5',
  6: 'xl:col-span-6',
  7: 'xl:col-span-7',
  8: 'xl:col-span-8',
  9: 'xl:col-span-9',
  10: 'xl:col-span-10',
  11: 'xl:col-span-11',
  12: 'xl:col-span-12',
};

export interface Placement {
  panel: SpecPanelMeta;
  span: number;
  /** 图表高度（px） */
  height: number;
}

const byPosition = (a: SpecPanelMeta, b: SpecPanelMeta): number =>
  (a.layout?.y ?? 0) - (b.layout?.y ?? 0) || (a.layout?.x ?? 0) - (b.layout?.x ?? 0);

/** 一行没排满的半宽面板拉成通栏，避免右侧留白 */
const fillOrphans = (list: Placement[]): Placement[] => {
  const out: Placement[] = list.map((p: Placement) => ({ ...p }));
  let run: Placement[] = [];
  const flush = (): void => {
    if (run.length % 2 === 1) {
      const last: Placement = run[run.length - 1];
      last.span = 12;
      last.height = Math.min(last.height, 300);
    }
    run = [];
  };
  out.forEach((p: Placement) => {
    if (p.span === 6) run.push(p);
    else flush();
  });
  flush();
  return out;
};

/** 网格类版式：返回按顺序排列的面板与跨度（command 版式单独按三栏渲染） */
export const arrange = (panels: SpecPanelMeta[], layout: LayoutKey): Placement[] => {
  const ordered: SpecPanelMeta[] = [...panels].sort(byPosition);
  const hero: string | undefined = pickHero(ordered);
  const kpis: SpecPanelMeta[] = ordered.filter((p: SpecPanelMeta) => p.kind === 'kpi');
  const others: SpecPanelMeta[] = ordered.filter((p: SpecPanelMeta) => p.kind !== 'kpi');
  const kpiSpan: number = kpis.length > 0 ? Math.max(2, Math.floor(12 / Math.min(kpis.length, 6))) : 12;

  if (layout === 'original') {
    const placed: Placement[] = ordered.map((p: SpecPanelMeta) => ({
      panel: p,
      span: Math.min(12, Math.max(2, p.layout?.w ?? 6)),
      height: Math.max(170, (p.layout?.h ?? 3) * 104 - 84),
    }));
    // 按行（相同 y）补满 12 栏：草图换算的宽度加起来常差 1 栏，把差额给本行最后一个面板
    const rows = new Map<number, Placement[]>();
    placed.forEach((pl: Placement) => {
      const y: number = pl.panel.layout?.y ?? 0;
      rows.set(y, [...(rows.get(y) ?? []), pl]);
    });
    rows.forEach((row: Placement[]) => {
      const used: number = row.reduce((a: number, pl: Placement) => a + pl.span, 0);
      if (used < 12 && used >= 9) row[row.length - 1].span += 12 - used;
    });
    return placed;
  }
  const kpiRow: Placement[] = kpis.map((p: SpecPanelMeta) => ({ panel: p, span: kpiSpan, height: 0 }));
  if (layout === 'executive') {
    const rest: Placement[] = others.map((p: SpecPanelMeta) => {
      const role: PanelRole = roleOf(p, hero);
      if (role === 'hero') return { panel: p, span: 12, height: 320 };
      if (role === 'note') return { panel: p, span: 12, height: 0 };
      if (p.kind === 'table') return { panel: p, span: 12, height: 360 };
      return { panel: p, span: 6, height: 280 };
    });
    const heroFirst: Placement[] = [
      ...rest.filter((r: Placement) => r.panel.id === hero),
      ...rest.filter((r: Placement) => r.panel.id !== hero),
    ];
    return [...kpiRow, ...fillOrphans(heroFirst)];
  }
  if (layout === 'grid') {
    return [
      ...kpiRow,
      ...others.map((p: SpecPanelMeta) => ({
        panel: p,
        span: p.kind === 'table' ? 12 : 4,
        height: 240,
      })),
    ];
  }
  if (layout === 'workbench') {
    const tables: SpecPanelMeta[] = others.filter((p: SpecPanelMeta) => p.kind === 'table');
    const main: SpecPanelMeta | undefined = tables[0] ?? others.find((p: SpecPanelMeta) => p.id === hero);
    const rest: SpecPanelMeta[] = others.filter((p: SpecPanelMeta) => p !== main);
    const side: SpecPanelMeta[] = rest.slice(0, 2);
    const bottom: SpecPanelMeta[] = rest.slice(2);
    return [
      ...kpiRow.map((k: Placement) => ({ ...k, span: Math.max(3, k.span) })),
      ...(main ? [{ panel: main, span: 8, height: 420 }] : []),
      ...side.map((p: SpecPanelMeta) => ({ panel: p, span: 4, height: 170 })),
      ...bottom.map((p: SpecPanelMeta) => ({ panel: p, span: p.kind === 'table' ? 12 : 6, height: 260 })),
    ];
  }
  if (layout === 'scorecard') {
    const big: Placement[] = kpis.slice(0, 3).map((p: SpecPanelMeta) => ({ panel: p, span: 4, height: 0 }));
    const smallKpis: Placement[] = kpis.slice(3).map((p: SpecPanelMeta) => ({ panel: p, span: 3, height: 0 }));
    const table: SpecPanelMeta | undefined =
      others.find((p: SpecPanelMeta) => p.kind === 'table') ?? others.find((p: SpecPanelMeta) => p.kind === 'category');
    const rest: SpecPanelMeta[] = others.filter((p: SpecPanelMeta) => p !== table);
    return [
      ...big,
      ...(table ? [{ panel: table, span: 12, height: 360 }] : []),
      ...smallKpis,
      ...rest.map((p: SpecPanelMeta) => ({ panel: p, span: 3, height: 200 })),
    ];
  }
  if (layout === 'magazine') {
    const pattern: number[] = [8, 4, 5, 7, 7, 5];
    const sorted: SpecPanelMeta[] = [
      ...others.filter((p: SpecPanelMeta) => p.id === hero),
      ...others.filter((p: SpecPanelMeta) => p.kind === 'text'),
      ...others.filter((p: SpecPanelMeta) => p.id !== hero && p.kind !== 'text'),
    ];
    let i = 0;
    const rest: Placement[] = sorted.map((p: SpecPanelMeta) => {
      if (p.kind === 'table') return { panel: p, span: 12, height: 360 };
      const span: number = pattern[i % pattern.length];
      i += 1;
      return { panel: p, span, height: span >= 7 ? 320 : 300 };
    });
    return [...kpiRow, ...rest];
  }
  // focus：单列
  return [...kpiRow.map((k: Placement) => ({ ...k, span: 6 })), ...others.map((p: SpecPanelMeta) => ({ panel: p, span: 12, height: 300 }))];
};
