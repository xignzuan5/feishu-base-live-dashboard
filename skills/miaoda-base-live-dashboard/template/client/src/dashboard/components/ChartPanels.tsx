import React, { useMemo } from 'react';

import type {
  CategoryData,
  HeatmapData,
  MeterData,
  ScatterData,
  StackedData,
  TrendData,
} from '@shared/dashboard.interface';

import { EChart } from '../charts/EChart';
import {
  CATEGORY_TYPES,
  METER_TYPES,
  STACKED_TYPES,
  TREND_TYPES,
  categoryOption,
  heatmapOption,
  ringOption,
  scatterOption,
  stackedOption,
  trendOption,
  type CategoryType,
  type MeterType,
  type StackedType,
  type TrendType,
} from '../charts/options';
import { formatValue } from '../lib/format';
import { usePanelType } from '../lib/hooks';
import { useDashStyle } from '../theme/DashStyleProvider';
import { ChartTypeSwitch } from './ChartTypeSwitch';
import { Panel, PanelEmpty } from './Panel';

interface BasePanelProps {
  /** 面板唯一 id：图表类型选择按它记忆 */
  id: string;
  title: string;
  subtitle?: string;
  /** 图表高度；'fill' = 撑满面板（大屏网格里用） */
  height?: number | 'fill';
  className?: string;
}

const emptyHeight = (h: number | 'fill'): number => (h === 'fill' ? 200 : h);

// ------------------------------------------------------------------ 趋势
interface TrendPanelProps extends BasePanelProps {
  data: TrendData | undefined;
  types?: readonly TrendType[];
  defaultType?: TrendType;
  stack?: boolean;
}

export const TrendPanel: React.FC<TrendPanelProps> = ({
  id, title, subtitle, data, height = 280, className, types = TREND_TYPES, defaultType = 'area', stack,
}) => {
  const { palette, style } = useDashStyle();
  const [type, setType] = usePanelType<TrendType>(id, types, defaultType);
  const option = useMemo(() => (data ? trendOption(data, type, palette, { stack }) : null), [data, type, palette, stack]);
  const empty: boolean = !data || data.series.every((s) => s.points.length === 0);
  return (
    <Panel
      title={title}
      subtitle={subtitle}
      className={className}
      actions={types.length > 1 ? <ChartTypeSwitch value={type} options={types} onChange={setType} label={title} /> : null}
    >
      {empty || !option ? <PanelEmpty height={emptyHeight(height)} /> : (
        <EChart option={option} height={height} ariaLabel={`${title}趋势图`} typeKey={`${type}-${style}`} />
      )}
    </Panel>
  );
};

// ------------------------------------------------------------------ 构成 / 排行
interface CategoryPanelProps extends BasePanelProps {
  data: CategoryData | undefined;
  types?: readonly CategoryType[];
  defaultType?: CategoryType;
}

export const CategoryPanel: React.FC<CategoryPanelProps> = ({
  id, title, subtitle, data, height = 280, className, types = CATEGORY_TYPES, defaultType = 'bar',
}) => {
  const { palette, style } = useDashStyle();
  const [type, setType] = usePanelType<CategoryType>(id, types, defaultType);
  const option = useMemo(() => (data ? categoryOption(data, type, palette) : null), [data, type, palette]);
  return (
    <Panel
      title={title}
      subtitle={subtitle}
      className={className}
      actions={types.length > 1 ? <ChartTypeSwitch value={type} options={types} onChange={setType} label={title} /> : null}
    >
      {!data || data.items.length === 0 || !option ? <PanelEmpty height={emptyHeight(height)} /> : (
        <EChart
          option={option}
          height={type === 'segmented' ? Math.min(emptyHeight(height), 120) : height}
          ariaLabel={`${title}：${data.items.slice(0, 5).map((i) => `${i.name} ${formatValue(i.value, data.format)}`).join('，')}`}
          typeKey={`${type}-${style}`}
        />
      )}
    </Panel>
  );
};

// ------------------------------------------------------------------ 多系列对比
interface StackedPanelProps extends BasePanelProps {
  data: StackedData | undefined;
  types?: readonly StackedType[];
  defaultType?: StackedType;
  horizontal?: boolean;
}

export const StackedPanel: React.FC<StackedPanelProps> = ({
  id, title, subtitle, data, height = 280, className, types = STACKED_TYPES, defaultType = 'stacked', horizontal,
}) => {
  const { palette, style } = useDashStyle();
  const [type, setType] = usePanelType<StackedType>(id, types, defaultType);
  const option = useMemo(
    () => (data ? stackedOption(data, type, palette, { horizontal }) : null),
    [data, type, palette, horizontal],
  );
  return (
    <Panel
      title={title}
      subtitle={subtitle}
      className={className}
      actions={types.length > 1 ? <ChartTypeSwitch value={type} options={types} onChange={setType} label={title} /> : null}
    >
      {!data || data.categories.length === 0 || !option ? <PanelEmpty height={emptyHeight(height)} /> : (
        <EChart option={option} height={height} ariaLabel={`${title}对比图`} typeKey={`${type}-${style}`} />
      )}
    </Panel>
  );
};

// ------------------------------------------------------------------ 热力图
interface HeatmapPanelProps extends BasePanelProps {
  data: HeatmapData | undefined;
}

export const HeatmapPanel: React.FC<HeatmapPanelProps> = ({ title, subtitle, data, height = 280, className }) => {
  const { palette, style } = useDashStyle();
  const option = useMemo(() => (data ? heatmapOption(data, palette) : null), [data, palette]);
  return (
    <Panel title={title} subtitle={subtitle} className={className}>
      {!option ? <PanelEmpty height={emptyHeight(height)} /> : (
        <EChart option={option} height={height} ariaLabel={`${title}热力图`} typeKey={style} />
      )}
    </Panel>
  );
};

// ------------------------------------------------------------------ 气泡散点
interface ScatterPanelProps extends BasePanelProps {
  data: ScatterData | undefined;
}

export const ScatterPanel: React.FC<ScatterPanelProps> = ({ title, subtitle, data, height = 300, className }) => {
  const { palette, style } = useDashStyle();
  const option = useMemo(() => (data ? scatterOption(data, palette) : null), [data, palette]);
  return (
    <Panel title={title} subtitle={subtitle} className={className}>
      {!data || data.points.length === 0 || !option ? <PanelEmpty height={emptyHeight(height)} /> : (
        <EChart option={option} height={height} ariaLabel={`${title}散点图`} typeKey={style} />
      )}
    </Panel>
  );
};

// ------------------------------------------------------------------ 目标达成（圆环 / 进度条）
interface MeterPanelProps extends Omit<BasePanelProps, 'height'> {
  height?: number;
  data: MeterData | undefined;
  types?: readonly MeterType[];
  defaultType?: MeterType;
}

export const MeterPanel: React.FC<MeterPanelProps> = ({
  id, title, subtitle, data, height = 220, className, types = METER_TYPES, defaultType = 'ring',
}) => {
  const { palette, style } = useDashStyle();
  const [type, setType] = usePanelType<MeterType>(id, types, defaultType);
  const pct: number = data && data.target > 0 ? data.value / data.target : 0;
  const pctText: string = formatValue(pct, 'percent');
  const option = useMemo(
    () => (data ? ringOption(data.value, data.target, palette) : null),
    [data, palette],
  );
  return (
    <Panel
      title={title}
      subtitle={subtitle}
      className={className}
      actions={<ChartTypeSwitch value={type} options={types} onChange={setType} label={title} />}
    >
      {!data || !option ? <PanelEmpty height={emptyHeight(height)} /> : (
        <div className="flex h-full flex-col justify-center" style={{ minHeight: height }}>
          {type === 'ring' ? (
            <div className="relative">
              <EChart option={option} height={height - 56} ariaLabel={`${title} ${pctText}`} typeKey={`ring-${style}`} />
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="dash-num dash-kpi-value text-3xl font-semibold">{pctText}</span>
                <span className="dash-subtle mt-1 text-xs">达成率</span>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-3 py-6">
              <div className="dash-num dash-kpi-value text-4xl font-semibold">{pctText}</div>
              <div className="dash-meter-track" style={{ height: 12 }}>
                <div
                  className="dash-meter-fill"
                  data-over={pct >= 1}
                  style={{ width: `${Math.min(pct, 1) * 100}%` }}
                  role="meter"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={Math.round(pct * 100)}
                  aria-label={title}
                />
              </div>
            </div>
          )}
          <div className="dash-subtle mt-2 flex justify-between gap-2 text-xs">
            <span>实际 <b className="dash-num text-foreground">{formatValue(data.value, data.format, { compact: true })}</b></span>
            <span>目标 <b className="dash-num text-foreground">{formatValue(data.target, data.format, { compact: true })}</b></span>
          </div>
        </div>
      )}
    </Panel>
  );
};
