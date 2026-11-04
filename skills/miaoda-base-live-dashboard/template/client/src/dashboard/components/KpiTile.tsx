import React from 'react';
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';

import type { KpiItem } from '@shared/dashboard.interface';
import { cn } from '@/lib/utils';

import { formatDelta, formatValue } from '../lib/format';
import { useChangeKey } from '../lib/hooks';

interface KpiTileProps {
  item: KpiItem;
  /** big：大屏用超大数字 */
  size?: 'default' | 'big';
}

/** 指标卡：大数字 + 环比（状态色只配合箭头图标使用，不单靠颜色表达） */
export const KpiTile: React.FC<KpiTileProps> = ({ item, size = 'default' }) => {
  const tick: number = useChangeKey(item.value);
  const d: number | null = item.delta;
  const good: boolean | null = d === null || d === 0 ? null : (d > 0) === (item.goodWhen === 'up');
  const Icon = d === null || d === 0 ? Minus : d > 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <div className={cn('dash-panel dash-kpi flex min-w-0 flex-col justify-between', size === 'big' ? 'p-5' : 'p-4')}>
      <div className="dash-subtle truncate text-xs">{item.label}</div>
      <div
        key={tick}
        className={cn(
          'dash-num dash-kpi-value mt-2 truncate font-semibold',
          tick > 0 && 'dash-tick',
          size === 'big' ? 'text-4xl xl:text-5xl' : 'text-2xl xl:text-[28px]',
        )}
        aria-live="polite"
      >
        {formatValue(item.value, item.format, { compact: item.value >= 1e5 })}
      </div>
      <div className="mt-2 flex items-center gap-1.5 text-xs">
        <span
          className={cn(
            'inline-flex items-center gap-0.5 font-medium',
            good === true && 'dash-good',
            good === false && 'dash-critical',
            good === null && 'dash-subtle',
          )}
        >
          <Icon className="size-3.5" aria-hidden />
          {d === null ? '' : formatDelta(d, item.format)}
        </span>
        <span className="dash-subtle truncate">{item.deltaLabel}</span>
      </div>
    </div>
  );
};

interface KpiRowProps {
  items: KpiItem[];
  size?: 'default' | 'big';
  className?: string;
}

export const KpiRow: React.FC<KpiRowProps> = ({ items, size, className }) => (
  <div
    data-ai-section-type="card-stat"
    className={cn('grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6', className)}
  >
    {items.map((it: KpiItem) => (
      <KpiTile key={it.key} item={it} size={size} />
    ))}
  </div>
);
