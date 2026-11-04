import type { EChartsOption } from 'echarts';

import type {
  CategoryData,
  CategoryItem,
  HeatmapData,
  ScatterData,
  StackedData,
  TrendData,
  TrendSeries,
  ValueFormat,
} from '@shared/dashboard.interface';

import { entitySlot } from '../theme/entities';
import type { ChartPalette } from '../theme/styles';
import { formatValue } from '../lib/format';

// ------------------------------------------------------------------ 图表类型目录
export const TREND_TYPES = ['line', 'area', 'bar'] as const;
export type TrendType = (typeof TREND_TYPES)[number];

export const CATEGORY_TYPES = ['bar', 'column', 'treemap', 'donut', 'segmented'] as const;
export type CategoryType = (typeof CATEGORY_TYPES)[number];

export const STACKED_TYPES = ['stacked', 'grouped', 'percent'] as const;
export type StackedType = (typeof STACKED_TYPES)[number];

export const METER_TYPES = ['ring', 'bar'] as const;
export type MeterType = (typeof METER_TYPES)[number];

export const CHART_TYPE_LABELS: Record<string, string> = {
  line: '折线',
  area: '面积',
  bar: '条形',
  column: '柱状',
  treemap: '矩形树图',
  donut: '环形',
  segmented: '占比条',
  stacked: '堆叠',
  grouped: '分组',
  percent: '百分比',
  ring: '圆环',
};

/** 分类色超过 6 个时折叠为「其他」，绝不循环取色 */
const MAX_CATEGORICAL = 6;

/**
 * 一张图里的实体配色：登记过的实体用固定槽位（所有图同色）；
 * 没登记的按出现顺序取「本图还没被占用」的槽位，保证同一张图里不撞色；「其他」固定弱化灰。
 */
const colorsFor = (pal: ChartPalette, names: string[]): Map<string, string> => {
  const out = new Map<string, string>();
  const used = new Set<number>();
  const fixed: [string, number][] = names
    .filter((n: string) => n !== '其他')
    .map((n: string): [string, number] => [n, entitySlot(n, -1)])
    .filter(([, slot]: [string, number]) => slot >= 0 && slot < MAX_CATEGORICAL);
  fixed.forEach(([n, slot]: [string, number]) => {
    if (!used.has(slot)) {
      out.set(n, pal.categorical[slot]);
      used.add(slot);
    }
  });
  let next = 0;
  names.forEach((n: string) => {
    if (out.has(n)) return;
    if (n === '其他') {
      out.set(n, pal.compare);
      return;
    }
    while (used.has(next) && next < MAX_CATEGORICAL) next += 1;
    out.set(n, next < MAX_CATEGORICAL ? pal.categorical[next] : pal.compare);
    used.add(next);
  });
  return out;
};

const foldOthers = (items: CategoryItem[], max: number = MAX_CATEGORICAL): CategoryItem[] => {
  if (items.length <= max) return items;
  const head: CategoryItem[] = items.slice(0, max - 1);
  const rest: CategoryItem[] = items.slice(max - 1);
  const other: CategoryItem = {
    name: '其他',
    value: rest.reduce((a: number, b: CategoryItem) => a + b.value, 0),
    secondary: rest.reduce((a: number, b: CategoryItem) => a + (b.secondary ?? 0), 0),
  };
  return [...head, other];
};

// ------------------------------------------------------------------ 公共底座
const base = (pal: ChartPalette): EChartsOption => ({
  backgroundColor: 'transparent',
  textStyle: { color: pal.text.secondary, fontFamily: 'inherit' },
  animationDuration: 500,
  animationDurationUpdate: 500,
  tooltip: {
    backgroundColor: pal.tooltipBg,
    borderColor: pal.tooltipBorder,
    borderWidth: 1,
    padding: [8, 12],
    textStyle: { color: pal.text.primary, fontSize: 12 },
    extraCssText: 'border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.18);',
  },
});

const axisCommon = (pal: ChartPalette) => ({
  axisLine: { lineStyle: { color: pal.axis } },
  axisTick: { show: false },
  axisLabel: { color: pal.text.muted, fontSize: 11 },
  splitLine: { lineStyle: { color: pal.grid } },
});

const valueAxis = (pal: ChartPalette, format: ValueFormat) => ({
  type: 'value' as const,
  // 计数类指标只用整数刻度，避免出现 0.5 单
  minInterval: format === 'number' ? 1 : undefined,
  ...axisCommon(pal),
  axisLine: { show: false },
  axisLabel: {
    color: pal.text.muted,
    fontSize: 11,
    formatter: (v: number) => formatValue(v, format, { compact: true, cents: false }),
  },
});

const legend = (pal: ChartPalette, show: boolean) => ({
  show,
  top: 0,
  right: 0,
  icon: 'roundRect',
  itemWidth: 10,
  itemHeight: 10,
  itemGap: 14,
  textStyle: { color: pal.text.secondary, fontSize: 12 },
});

const glow = (pal: ChartPalette, color: string) =>
  pal.glow > 0 ? { shadowBlur: pal.glow, shadowColor: color } : {};

interface TooltipParam {
  marker?: string;
  seriesName?: string;
  name?: string;
  value?: unknown;
  data?: unknown;
  percent?: number;
  axisValueLabel?: string;
}

const tooltipRows = (params: TooltipParam | TooltipParam[], format: ValueFormat): string => {
  const list: TooltipParam[] = Array.isArray(params) ? params : [params];
  const head: string = list[0]?.axisValueLabel ?? list[0]?.name ?? '';
  const rows: string = list
    .map(
      (p: TooltipParam) =>
        `<div style="display:flex;justify-content:space-between;gap:16px"><span>${p.marker ?? ''}${p.seriesName ?? ''}</span><b>${formatValue(Number(Array.isArray(p.value) ? p.value[1] : p.value), format)}</b></div>`,
    )
    .join('');
  return `<div style="font-weight:600;margin-bottom:4px">${head}</div>${rows}`;
};

// ------------------------------------------------------------------ 趋势（折线 / 面积 / 柱状）
export const trendOption = (
  data: TrendData,
  type: TrendType,
  pal: ChartPalette,
  opts: { stack?: boolean } = {},
): EChartsOption => {
  const longest: TrendSeries = data.series.reduce(
    (a: TrendSeries, b: TrendSeries) => (b.points.length > a.points.length ? b : a),
    data.series[0] ?? { name: '', points: [] },
  );
  const xLabels: string[] = longest.points.map((p) => p.x);
  const main: TrendSeries[] = data.series.filter((s: TrendSeries) => !s.compare);
  const singleMain: boolean = main.length === 1;
  const palette = colorsFor(pal, main.map((x: TrendSeries) => x.name));
  const series = data.series.map((s: TrendSeries) => {
    if (s.compare) {
      return {
        name: s.name,
        type: 'line' as const,
        data: s.points.map((p) => p.y),
        smooth: true,
        symbol: 'none',
        z: 1,
        lineStyle: { width: 2, type: 'dashed' as const, color: pal.compare },
        itemStyle: { color: pal.compare },
      };
    }
    const color: string = singleMain ? pal.single : palette.get(s.name) ?? pal.single;
    if (type === 'bar') {
      return {
        name: s.name,
        type: 'bar' as const,
        data: s.points.map((p) => p.y),
        stack: opts.stack ? 'total' : undefined,
        barMaxWidth: 18,
        itemStyle: { color, borderRadius: opts.stack ? 0 : [4, 4, 0, 0], ...glow(pal, color) },
        z: 2,
      };
    }
    return {
      name: s.name,
      type: 'line' as const,
      data: s.points.map((p) => p.y),
      smooth: true,
      stack: opts.stack ? 'total' : undefined,
      symbol: 'circle',
      symbolSize: 8,
      showSymbol: false,
      z: 3,
      lineStyle: { width: 2, color, ...glow(pal, color) },
      itemStyle: { color, borderColor: pal.surface, borderWidth: 2 },
      areaStyle:
        type === 'area'
          ? {
              color: {
                type: 'linear' as const,
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: singleMain ? pal.singleSoft : `${color}55` },
                  { offset: 1, color: 'rgba(0,0,0,0)' },
                ],
              },
            }
          : undefined,
    };
  });
  return {
    ...base(pal),
    grid: { left: 8, right: 12, top: data.series.length > 1 ? 36 : 16, bottom: 8, containLabel: true },
    legend: legend(pal, data.series.length > 1),
    tooltip: {
      ...(base(pal).tooltip as object),
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: pal.axis } },
      formatter: (p: unknown) => tooltipRows(p as TooltipParam[], data.format),
    },
    xAxis: { type: 'category', data: xLabels, boundaryGap: type === 'bar', ...axisCommon(pal), splitLine: { show: false } },
    yAxis: valueAxis(pal, data.format),
    series,
  } as EChartsOption;
};

// ------------------------------------------------------------------ 构成（条形 / 柱状 / 树图 / 环形 / 占比条）
export const categoryOption = (data: CategoryData, type: CategoryType, pal: ChartPalette): EChartsOption => {
  const fmt: ValueFormat = data.format;
  const tip = (p: TooltipParam) => {
    const item = p.data as { secondary?: number } | undefined;
    const sec: string =
      data.secondaryLabel && item?.secondary !== undefined
        ? `<div style="display:flex;justify-content:space-between;gap:16px"><span>${data.secondaryLabel}</span><b>${formatValue(item.secondary, fmt === 'currency' ? 'number' : 'currency')}</b></div>`
        : '';
    const pct: string = p.percent !== undefined ? `（${p.percent}%）` : '';
    return `<div style="font-weight:600;margin-bottom:4px">${p.name ?? ''}</div><div style="display:flex;justify-content:space-between;gap:16px"><span>${p.marker ?? ''}数值</span><b>${formatValue(Number(Array.isArray(p.value) ? p.value[0] : p.value), fmt)}${pct}</b></div>${sec}`;
  };
  const tooltip = { ...(base(pal).tooltip as object), trigger: 'item' as const, formatter: (p: unknown) => tip(p as TooltipParam) };

  if (type === 'treemap' || type === 'donut' || type === 'segmented') {
    const items: CategoryItem[] = foldOthers(data.items);
    const total: number = items.reduce((a: number, b: CategoryItem) => a + b.value, 0);
    const colors = colorsFor(pal, items.map((it: CategoryItem) => it.name));
    if (type === 'treemap') {
      return {
        ...base(pal),
        tooltip,
        series: [
          {
            type: 'treemap',
            roam: false,
            nodeClick: false,
            breadcrumb: { show: false },
            top: 4,
            left: 4,
            right: 4,
            bottom: 4,
            itemStyle: { borderColor: pal.surface, borderWidth: 2, gapWidth: 2, borderRadius: 6 },
            label: {
              show: true,
              color: '#fff',
              fontSize: 12,
              formatter: (p: { name: string; value: number }) =>
                `{n|${p.name}}\n{v|${formatValue(p.value, fmt, { compact: true })}}`,
              rich: { n: { fontSize: 12, color: '#fff' }, v: { fontSize: 14, fontWeight: 700, color: '#fff', padding: [4, 0, 0, 0] } },
            },
            data: items.map((it: CategoryItem, i: number) => ({
              name: it.name,
              value: it.value,
              secondary: it.secondary,
              itemStyle: { color: colors.get(it.name) },
            })),
          },
        ],
      } as EChartsOption;
    }
    if (type === 'donut') {
      return {
        ...base(pal),
        tooltip,
        legend: { ...legend(pal, true), top: 'middle', right: 0, orient: 'vertical' },
        series: [
          {
            type: 'pie',
            radius: ['52%', '78%'],
            center: ['36%', '50%'],
            padAngle: 2,
            itemStyle: { borderRadius: 4, borderColor: pal.surface, borderWidth: 2 },
            label: {
              show: true,
              position: 'center',
              formatter: () => `{v|${formatValue(total, fmt, { compact: true })}}\n{l|合计}`,
              rich: {
                v: { fontSize: 18, fontWeight: 700, color: pal.text.primary },
                l: { fontSize: 11, color: pal.text.muted, padding: [4, 0, 0, 0] },
              },
            },
            emphasis: { scale: true, scaleSize: 4, label: { show: true } },
            labelLine: { show: false },
            data: items.map((it: CategoryItem, i: number) => ({
              name: it.name,
              value: it.value,
              secondary: it.secondary,
              itemStyle: { color: colors.get(it.name) },
            })),
          },
        ],
      } as EChartsOption;
    }
    // segmented：一根占比条（部分与整体，最多 6 段）
    return {
      ...base(pal),
      tooltip,
      legend: { ...legend(pal, true), top: 0, left: 0, right: undefined },
      grid: { left: 0, right: 0, top: 40, bottom: 0, height: 44 },
      xAxis: { type: 'value', max: total || 1, show: false },
      yAxis: { type: 'category', data: ['占比'], show: false },
      series: items.map((it: CategoryItem, i: number) => ({
        name: it.name,
        type: 'bar' as const,
        stack: 'all',
        barWidth: 44,
        data: [{ value: it.value, name: it.name, secondary: it.secondary }],
        itemStyle: {
          color: colors.get(it.name),
          borderColor: pal.surface,
          borderWidth: 2,
          borderRadius: i === 0 ? [6, 0, 0, 6] : i === items.length - 1 ? [0, 6, 6, 0] : 0,
        },
        label: {
          show: total > 0 && it.value / total > 0.07,
          position: 'inside' as const,
          color: '#fff',
          fontSize: 11,
          formatter: () => `${Math.round((it.value / (total || 1)) * 100)}%`,
        },
      })),
    } as EChartsOption;
  }

  const horizontal: boolean = type === 'bar';
  const names: string[] = data.items.map((it: CategoryItem) => it.name);
  const values = data.items.map((it: CategoryItem) => ({ value: it.value, name: it.name, secondary: it.secondary }));
  const catAxis = {
    type: 'category' as const,
    data: horizontal ? [...names].reverse() : names,
    ...axisCommon(pal),
    splitLine: { show: false },
    axisLabel: { color: pal.text.secondary, fontSize: 12, width: 96, overflow: 'truncate' as const },
  };
  return {
    ...base(pal),
    tooltip,
    grid: { left: 4, right: horizontal ? 64 : 8, top: horizontal ? 4 : 24, bottom: 4, containLabel: true },
    xAxis: horizontal ? { ...valueAxis(pal, fmt), splitLine: { show: false }, axisLabel: { show: false } } : catAxis,
    yAxis: horizontal ? catAxis : valueAxis(pal, fmt),
    series: [
      {
        type: 'bar',
        data: horizontal ? [...values].reverse() : values,
        barMaxWidth: horizontal ? 14 : 28,
        showBackground: true,
        backgroundStyle: { color: pal.grid, borderRadius: 4 },
        itemStyle: {
          color: pal.single,
          borderRadius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0],
          ...glow(pal, pal.single),
        },
        label: {
          show: true,
          position: horizontal ? 'right' : 'top',
          color: pal.text.secondary,
          fontSize: 11,
          formatter: (p: { value: number }) => formatValue(p.value, fmt, { compact: true }),
        },
      },
    ],
  } as EChartsOption;
};

// ------------------------------------------------------------------ 多系列（堆叠 / 分组 / 百分比）
export const stackedOption = (
  data: StackedData,
  type: StackedType,
  pal: ChartPalette,
  opts: { horizontal?: boolean } = {},
): EChartsOption => {
  const horizontal: boolean = opts.horizontal ?? false;
  const totals: number[] = data.categories.map((_c: string, i: number) =>
    data.series.reduce((a: number, s) => a + (s.values[i] ?? 0), 0),
  );
  const pct: boolean = type === 'percent';
  const fmt: ValueFormat = pct ? 'percent' : data.format;
  const catAxis = {
    type: 'category' as const,
    data: data.categories,
    ...axisCommon(pal),
    splitLine: { show: false },
  };
  const valAxis = { ...valueAxis(pal, fmt), max: pct ? 1 : undefined };
  const colors = colorsFor(pal, data.series.slice(0, MAX_CATEGORICAL).map((x) => x.name));
  return {
    ...base(pal),
    legend: legend(pal, data.series.length > 1),
    grid: { left: 4, right: 12, top: 36, bottom: 4, containLabel: true },
    tooltip: {
      ...(base(pal).tooltip as object),
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: pal.grid } },
      formatter: (p: unknown) => tooltipRows(p as TooltipParam[], fmt),
    },
    xAxis: horizontal ? valAxis : catAxis,
    yAxis: horizontal ? catAxis : valAxis,
    series: data.series.slice(0, MAX_CATEGORICAL).map((s, i: number) => ({
      name: s.name,
      type: 'bar' as const,
      stack: type === 'grouped' ? undefined : 'total',
      barMaxWidth: type === 'grouped' ? 16 : 28,
      barGap: '20%',
      data: s.values.map((v: number, ci: number) => (pct ? (totals[ci] ? v / totals[ci] : 0) : v)),
      itemStyle: {
        color: colors.get(s.name),
        borderColor: pal.surface,
        borderWidth: type === 'grouped' ? 0 : 1,
        borderRadius: type === 'grouped' ? [4, 4, 0, 0] : 0,
      },
      emphasis: { focus: 'series' as const },
    })),
  } as EChartsOption;
};

// ------------------------------------------------------------------ 热力图（顺序色阶，单一色相）
export const heatmapOption = (data: HeatmapData, pal: ChartPalette): EChartsOption => {
  const max: number = data.cells.reduce((a: number, c: [number, number, number]) => Math.max(a, c[2]), 0);
  return {
    ...base(pal),
    tooltip: {
      ...(base(pal).tooltip as object),
      formatter: (p: unknown) => {
        const v = (p as { value: [number, number, number] }).value;
        return `<div style="font-weight:600">${data.yLabels[v[1]]} ${data.xLabels[v[0]]}</div><div>订单 <b>${formatValue(v[2], data.format)}</b></div>`;
      },
    },
    grid: { left: 4, right: 4, top: 4, bottom: 36, containLabel: true },
    xAxis: { type: 'category', data: data.xLabels, ...axisCommon(pal), splitLine: { show: false }, axisLine: { show: false } },
    // inverse：第一行（周一）在最上面
    yAxis: {
      type: 'category',
      data: data.yLabels,
      inverse: true,
      ...axisCommon(pal),
      splitLine: { show: false },
      axisLine: { show: false },
    },
    visualMap: {
      min: 0,
      max: max || 1,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      itemWidth: 10,
      itemHeight: 120,
      text: ['多', '少'],
      textStyle: { color: pal.text.muted, fontSize: 11 },
      inRange: { color: pal.sequential },
    },
    series: [
      {
        type: 'heatmap',
        data: data.cells,
        itemStyle: { borderColor: pal.surface, borderWidth: 2, borderRadius: 3 },
        emphasis: { itemStyle: { borderColor: pal.text.primary, borderWidth: 1 } },
      },
    ],
  } as EChartsOption;
};

// ------------------------------------------------------------------ 气泡散点
export const scatterOption = (data: ScatterData, pal: ChartPalette): EChartsOption => {
  const groups: string[] = Array.from(new Set(data.points.map((p) => p.group))).slice(0, MAX_CATEGORICAL);
  const maxSize: number = data.points.reduce((a: number, p) => Math.max(a, p.size), 1);
  const colors = colorsFor(pal, groups);
  return {
    ...base(pal),
    legend: legend(pal, groups.length > 1),
    grid: { left: 8, right: 16, top: 40, bottom: 8, containLabel: true },
    tooltip: {
      ...(base(pal).tooltip as object),
      formatter: (p: unknown) => {
        const d = (p as { data: { name: string; value: [number, number, number] } }).data;
        return `<div style="font-weight:600;margin-bottom:4px">${d.name}</div>${data.xLabel} <b>${formatValue(d.value[0], data.xFormat)}</b><br/>${data.yLabel} <b>${formatValue(d.value[1], data.yFormat)}</b><br/>${data.sizeLabel} <b>${formatValue(d.value[2], 'number')}</b>`;
      },
    },
    xAxis: { ...valueAxis(pal, data.xFormat), name: data.xLabel, nameTextStyle: { color: pal.text.muted }, scale: true },
    yAxis: { ...valueAxis(pal, data.yFormat), name: data.yLabel, nameTextStyle: { color: pal.text.muted }, scale: true },
    series: groups.map((g: string, i: number) => ({
      name: g,
      type: 'scatter' as const,
      data: data.points
        .filter((p) => p.group === g)
        .map((p) => ({ name: p.name, value: [p.x, p.y, p.size] })),
      symbolSize: (v: number[]) => 8 + Math.sqrt(v[2] / maxSize) * 34,
      itemStyle: {
        color: colors.get(g),
        opacity: 0.85,
        borderColor: pal.surface,
        borderWidth: 2,
        ...glow(pal, colors.get(g) ?? pal.single),
      },
    })),
  } as EChartsOption;
};

// ------------------------------------------------------------------ 进度环
/** 进度环；中心大数字由 MeterPanel 用 HTML 叠加（字号可控、可被读屏读到） */
export const ringOption = (value: number, target: number, pal: ChartPalette): EChartsOption => {
  const pctVal: number = target > 0 ? Math.min(value / target, 1.5) : 0;
  const color: string = pctVal >= 1 ? pal.status.good : pal.single;
  return {
    ...base(pal),
    series: [
      {
        type: 'gauge',
        startAngle: 90,
        endAngle: -270,
        min: 0,
        max: 1,
        radius: '88%',
        pointer: { show: false },
        progress: { show: true, roundCap: true, width: 14, itemStyle: { color, ...glow(pal, color) } },
        axisLine: { lineStyle: { width: 14, color: [[1, pal.grid]] } },
        splitLine: { show: false },
        axisTick: { show: false },
        axisLabel: { show: false },
        detail: { show: false },
        data: [{ value: Math.min(pctVal, 1) }],
      },
    ],
  } as EChartsOption;
};
