import React from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';

interface EChartProps {
  option: EChartsOption;
  /** 固定高度；传 'fill' 时撑满面板剩余高度（大屏用） */
  height?: number | 'fill';
  /** 读屏用的图表说明 */
  ariaLabel: string;
  /** 切换图表类型时传入，强制重建实例，避免旧系列残留 */
  typeKey?: string;
}

/**
 * ECharts 容器：数据刷新走 merge（平滑过渡），类型切换走 remount。
 */
export const EChart: React.FC<EChartProps> = ({ option, height = 260, ariaLabel, typeKey }) => (
  <div
    role="img"
    aria-label={ariaLabel}
    className={height === 'fill' ? 'min-h-[180px] w-full flex-1' : 'w-full'}
    style={height === 'fill' ? undefined : { height }}
  >
    <ReactECharts
      key={typeKey}
      option={option}
      notMerge={false}
      lazyUpdate
      style={{ width: '100%', height: '100%' }}
      opts={{ renderer: 'canvas' }}
    />
  </div>
);
