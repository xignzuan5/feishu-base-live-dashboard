import React from 'react';
import { Check, LayoutTemplate } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';

import { LAYOUTS, LAYOUT_META, type LayoutKey } from '../layouts';

/** 版式缩略图：12 栅格示意 */
export const Sketch: React.FC<{ cells: [number, number, number, number][]; active: boolean; className?: string }> = ({
  cells,
  active,
  className = 'h-9 w-14 shrink-0',
}) => {
  const rows: number = Math.max(...cells.map((c) => c[1] + c[3]));
  return (
    <svg viewBox={`0 0 120 ${rows * 10}`} className={className} aria-hidden>
      {cells.map(([x, y, w, h], i: number) => (
        <rect
          key={i}
          x={x * 10 + 1}
          y={y * 10 + 1}
          width={w * 10 - 2}
          height={h * 10 - 2}
          rx={2}
          fill={active ? 'var(--dash-accent)' : 'currentColor'}
          opacity={active ? 0.85 - i * 0.06 : 0.28}
        />
      ))}
    </svg>
  );
};

interface LayoutSwitcherProps {
  value: LayoutKey;
  onChange: (v: LayoutKey) => void;
  /** 原仪表盘没有坐标时隐藏「原始布局」 */
  hasOriginal: boolean;
}

export const LayoutSwitcher: React.FC<LayoutSwitcherProps> = ({ value, onChange, hasOriginal }) => (
  <Popover>
    <PopoverTrigger asChild>
      <Button variant="outline" size="sm" aria-label="切换排版" className="gap-1.5">
        <LayoutTemplate className="size-4" />
        <span className="hidden md:inline">{LAYOUT_META[value].label}</span>
      </Button>
    </PopoverTrigger>
    <PopoverContent align="end" className="w-80 p-2">
      <div className="dash-subtle px-2 pb-2 pt-1 text-xs">排版类型</div>
      <div role="radiogroup" aria-label="排版类型" className="flex flex-col gap-1">
        {LAYOUTS.filter((k: LayoutKey) => hasOriginal || k !== 'original').map((k: LayoutKey) => {
          const meta = LAYOUT_META[k];
          const active: boolean = k === value;
          return (
            <Button
              key={k}
              variant="ghost"
              role="radio"
              aria-checked={active}
              onClick={() => onChange(k)}
              className={cn('h-auto justify-start gap-3 px-2 py-2 text-left', active && 'bg-accent text-accent-foreground')}
            >
              <Sketch cells={meta.sketch} active={active} />
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium">{meta.label}</span>
                <span className="dash-subtle block whitespace-normal text-xs font-normal">{meta.description}</span>
              </span>
              {active ? <Check className="size-4 shrink-0" /> : null}
            </Button>
          );
        })}
      </div>
    </PopoverContent>
  </Popover>
);
