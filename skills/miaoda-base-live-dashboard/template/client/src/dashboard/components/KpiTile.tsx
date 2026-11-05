import React from 'react';
import { ArrowDownRight, ArrowUpRight, CircleAlert, Minus, TriangleAlert } from 'lucide-react';

import type { KpiItem, KpiThreshold } from '@shared/dashboard.interface';
import { cn } from '@/lib/utils';

import { formatDelta, formatValue } from '../lib/format';
import { useChangeKey } from '../lib/hooks';

interface KpiTileProps {
  item: KpiItem;
  /** big：大屏用超大数字 */
  size?: 'default' | 'big';
}

interface Breach {
  level: 'critical' | 'warning';
  text: string;
}

/** 绝对阈值：越线时返回级别和提示文字（「超过 10」「低于 60%」），没越线返回 null */
export const checkThreshold = (item: KpiItem): Breach | null => {
  const t: KpiThreshold | undefined = item.threshold;
  if (!t) return null;
  const level: Breach['level'] = t.level ?? 'critical';
  const fmt = (n: number): string => formatValue(n, item.format, { compact: Math.abs(n) >= 1e5 });
  if (t.above !== undefined && item.value > t.above) return { level, text: `超过 ${fmt(t.above)}` };
  if (t.below !== undefined && item.value < t.below) return { level, text: `低于 ${fmt(t.below)}` };
  return null;
};

/** 指标卡：大数字 + 环比 + 可选的阈值提示（状态色都配图标和文字，不单靠颜色表达） */
export const KpiTile: React.FC<KpiTileProps> = ({ item, size = 'default' }) => {
  const tick: number = useChangeKey(item.value);
  const breach: Breach | null = checkThreshold(item);
  const AlertIcon = breach?.level === 'warning' ? TriangleAlert : CircleAlert;
  const d: number | null = item.delta;
  const good: boolean | null = d === null || d === 0 ? null : (d > 0) === (item.goodWhen === 'up');
  const Icon = d === null || d === 0 ? Minus : d > 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <div
      className={cn('dash-panel dash-kpi flex min-w-0 flex-col justify-between', size === 'big' ? 'p-5' : 'p-4')}
      data-alert={breach?.level}
    >
      {/* 窄卡片放不下时，阈值提示换到第二行，保证指标名完整 */}
      <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1 text-xs">
        <span className="dash-subtle min-w-0 truncate">{item.label}</span>
        {breach ? (
          <span
            className={cn(
              'inline-flex shrink-0 items-center gap-1 font-medium',
              breach.level === 'critical' ? 'dash-critical' : 'dash-warning',
            )}
          >
            <AlertIcon className="size-3.5" aria-hidden />
            {breach.text}
          </span>
        ) : null}
      </div>
      <div
        key={tick}
        className={cn(
          'dash-num mt-2 truncate font-semibold',
          !breach && 'dash-kpi-value',
          breach?.level === 'critical' && 'dash-critical',
          breach?.level === 'warning' && 'dash-warning',
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
