import React from 'react';
import { Check, Palette } from 'lucide-react';

import { DASH_RANGES, DASH_RANGE_LABELS, type DashRange, type SyncStatus } from '@shared/dashboard.interface';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { cn } from '@/lib/utils';

import { formatClock, secondsAgo } from '../lib/format';
import { useNow } from '../lib/hooks';
import { useDashStyle } from '../theme/DashStyleProvider';
import { DASH_STYLES, DASH_STYLE_META, type DashStyle } from '../theme/styles';

// ------------------------------------------------------------------ 实时同步徽标
interface LiveBadgeProps {
  sync: SyncStatus | undefined;
  fetching: boolean;
  lastFetchedAt: number;
}

/** 绿色脉冲 = 最近一次轮询成功；黄色 = 超过 30 秒没拿到新数据（网络或同步异常） */
export const LiveBadge: React.FC<LiveBadgeProps> = ({ sync, fetching, lastFetchedAt }) => {
  const now: number = useNow();
  const ago: number = lastFetchedAt ? Math.round((now - lastFetchedAt) / 1000) : 0;
  const stale: boolean = ago > 30;
  const lastOrderAgo: number | null = secondsAgo(sync?.lastRecordAt, now);
  return (
    <div
      className="flex items-center gap-2 rounded-full border border-border px-3 py-1 text-xs"
      role="status"
      aria-label={stale ? '实时连接异常' : '实时同步中'}
    >
      <span className="dash-pulse" data-state={stale ? 'stale' : 'live'} aria-hidden />
      <span className="font-medium">{stale ? '连接异常' : fetching ? '同步中…' : '实时'}</span>
      <span className="dash-subtle hidden sm:inline">
        {ago} 秒前刷新，最新记录 {lastOrderAgo === null ? '—' : formatClock(sync?.lastRecordAt)}
      </span>
    </div>
  );
};

// ------------------------------------------------------------------ 风格切换
export const StyleSwitcher: React.FC = () => {
  const { style, setStyle } = useDashStyle();
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" aria-label="切换看板风格" className="gap-1.5">
          <Palette className="size-4" />
          <span className="hidden md:inline">{DASH_STYLE_META[style].label}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 p-2">
        <div className="dash-subtle px-2 pb-2 pt-1 text-xs">看板风格</div>
        <div role="radiogroup" aria-label="看板风格" className="flex flex-col gap-1">
          {DASH_STYLES.map((s: DashStyle) => {
            const meta = DASH_STYLE_META[s];
            const active: boolean = s === style;
            return (
              <Button
                key={s}
                variant="ghost"
                role="radio"
                aria-checked={active}
                onClick={() => setStyle(s)}
                className={cn('h-auto justify-start gap-3 px-2 py-2 text-left', active && 'bg-accent text-accent-foreground')}
              >
                <span className="flex shrink-0 overflow-hidden rounded-md border border-border">
                  {meta.swatches.map((c: string) => (
                    <span key={c} className="block h-8 w-4" style={{ background: c }} />
                  ))}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium">{meta.label}</span>
                  <span className="dash-subtle block truncate text-xs font-normal">{meta.description}</span>
                </span>
                {active ? <Check className="size-4 shrink-0" /> : null}
              </Button>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
};

// ------------------------------------------------------------------ 筛选：时间范围 + 城市
interface BoardFilterBarProps {
  range: DashRange;
  city: string;
  cities: string[];
  onRange: (r: DashRange) => void;
  onCity: (c: string) => void;
  ranges?: readonly DashRange[];
  showCity?: boolean;
}

export const BoardFilterBar: React.FC<BoardFilterBarProps> = ({
  range, city, cities, onRange, onCity, ranges = DASH_RANGES, showCity = true,
}) => (
  <div className="flex flex-wrap items-center gap-2">
    {ranges.length > 0 ? (
    <ToggleGroup
      type="single"
      size="sm"
      value={range}
      onValueChange={(v: string) => {
        if (v) onRange(v as DashRange);
      }}
      aria-label="时间范围"
      className="rounded-md border border-border p-0.5"
    >
      {ranges.map((r: DashRange) => (
        <ToggleGroupItem key={r} value={r} className="h-7 px-3 text-xs">
          {DASH_RANGE_LABELS[r]}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
    ) : null}
    {showCity ? (
    <Select value={city} onValueChange={onCity}>
      <SelectTrigger size="sm" className="h-8 w-[112px] text-xs" aria-label="城市">
        <SelectValue placeholder="全部城市" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">全部城市</SelectItem>
        {cities.map((c: string) => (
          <SelectItem key={c} value={c}>
            {c}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
    ) : null}
  </div>
);
