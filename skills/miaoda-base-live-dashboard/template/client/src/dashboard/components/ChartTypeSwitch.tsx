import React from 'react';
import {
  ChartArea,
  ChartBar,
  ChartBarStacked,
  ChartColumn,
  ChartColumnStacked,
  ChartLine,
  ChartPie,
  CircleDashed,
  Columns3,
  LayoutGrid,
  Percent,
  RectangleHorizontal,
  type LucideIcon,
} from 'lucide-react';

import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

import { CHART_TYPE_LABELS } from '../charts/options';

const ICONS: Record<string, LucideIcon> = {
  line: ChartLine,
  area: ChartArea,
  bar: ChartBar,
  column: ChartColumn,
  treemap: LayoutGrid,
  donut: ChartPie,
  segmented: RectangleHorizontal,
  stacked: ChartColumnStacked,
  grouped: Columns3,
  percent: Percent,
  ring: CircleDashed,
  hbar: ChartBarStacked,
};

interface ChartTypeSwitchProps<T extends string> {
  value: T;
  options: readonly T[];
  onChange: (v: T) => void;
  /** 面板名，用于读屏 */
  label: string;
}

/** 面板右上角的图表类型切换（图标 + 悬浮说明） */
export const ChartTypeSwitch = <T extends string>({ value, options, onChange, label }: ChartTypeSwitchProps<T>) => (
  <ToggleGroup
    type="single"
    size="sm"
    value={value}
    onValueChange={(v: string) => {
      if (v) onChange(v as T);
    }}
    aria-label={`${label}的图表类型`}
    className="rounded-md border border-border bg-background/40 p-0.5"
  >
    {options.map((opt: T) => {
      const Icon: LucideIcon = ICONS[opt] ?? ChartColumn;
      const text: string = CHART_TYPE_LABELS[opt] ?? opt;
      return (
        <Tooltip key={opt}>
          <TooltipTrigger asChild>
            <ToggleGroupItem value={opt} aria-label={text} className="h-7 min-w-7 px-1.5">
              <Icon className="size-3.5" />
            </ToggleGroupItem>
          </TooltipTrigger>
          <TooltipContent side="bottom">{text}</TooltipContent>
        </Tooltip>
      );
    })}
  </ToggleGroup>
);
