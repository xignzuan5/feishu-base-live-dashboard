import React, { useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, CircleAlert, CircleCheck, Clock, Crown, TriangleAlert } from 'lucide-react';

import type { CategoryData, FeedItem, TableCell, TableColumn, TableData } from '@shared/dashboard.interface';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

import { formatShortTime, formatValue } from '../lib/format';
import { useNewIds } from '../lib/hooks';
import { Panel, PanelEmpty } from './Panel';

// ------------------------------------------------------------------ 实时订单流
const STATUS_TONE: Record<string, 'good' | 'warning' | 'critical' | 'muted'> = {
  已完成: 'good',
  制作中: 'warning',
  配送中: 'warning',
  已退款: 'critical',
  已取消: 'muted',
  营业中: 'good',
  试营业: 'warning',
  装修升级: 'muted',
  进行中: 'good',
  未开始: 'warning',
  已结束: 'muted',
};

const STATUS_ICON = { good: CircleCheck, warning: Clock, critical: CircleAlert, muted: TriangleAlert } as const;

export const StatusTag: React.FC<{ value: string }> = ({ value }) => {
  const tone = STATUS_TONE[value] ?? 'muted';
  const Icon = STATUS_ICON[tone];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 whitespace-nowrap text-xs',
        tone === 'good' && 'dash-good',
        tone === 'warning' && 'dash-warning',
        tone === 'critical' && 'dash-critical',
        tone === 'muted' && 'dash-subtle',
      )}
    >
      <Icon className="size-3" aria-hidden />
      {value}
    </span>
  );
};

interface LiveFeedPanelProps {
  title?: string;
  subtitle?: string;
  items: FeedItem[] | undefined;
  height?: number;
  className?: string;
  dense?: boolean;
}

export const LiveFeedPanel: React.FC<LiveFeedPanelProps> = ({
  title = '实时订单流', subtitle = '多维表格新增 / 修改订单，几秒内出现在这里', items, height = 420, className, dense,
}) => {
  const ids: string[] = useMemo(() => (items ?? []).map((i: FeedItem) => i.id), [items]);
  const fresh: Set<string> = useNewIds(ids);
  return (
    <Panel title={title} subtitle={subtitle} className={className} bodyClassName="overflow-hidden">
      {!items || items.length === 0 ? <PanelEmpty height={height} message="暂无订单" /> : (
        <ol className="-mx-2 flex flex-col overflow-y-auto pr-1" style={{ maxHeight: height }} aria-live="polite">
          {items.map((it: FeedItem) => (
            <li
              key={it.id}
              className={cn(
                'flex items-center gap-3 rounded-md px-2 border-b border-border/50 last:border-b-0',
                dense ? 'py-1.5' : 'py-2',
                fresh.has(it.id) && 'dash-flash',
              )}
            >
              <span className="dash-num dash-subtle w-10 shrink-0 text-xs">{formatShortTime(it.time)}</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5 text-sm">
                  <span className="truncate font-medium">{it.store}</span>
                  {it.isMember ? <Crown className="dash-accent size-3 shrink-0" aria-label="会员" /> : null}
                  <span className="dash-subtle shrink-0 text-xs">{it.channel}</span>
                </div>
                {!dense ? <div className="dash-subtle truncate text-xs">{it.summary || it.orderNo}</div> : null}
              </div>
              <div className="flex shrink-0 flex-col items-end gap-0.5">
                <span className="dash-num text-sm font-semibold">{formatValue(it.amount, 'currency', { cents: true })}</span>
                <StatusTag value={it.status} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </Panel>
  );
};

// ------------------------------------------------------------------ 数据表（排行榜 / 活动效果）
const renderCell = (col: TableColumn, v: TableCell): React.ReactNode => {
  if (v === null || v === undefined) return <span className="dash-subtle">—</span>;
  if (col.format === 'status') return <StatusTag value={String(v)} />;
  if (col.format === 'meter') {
    const pct: number = Number(v);
    return (
      <div className="flex min-w-[120px] items-center gap-2">
        <div className="dash-meter-track flex-1">
          <div className="dash-meter-fill" data-over={pct >= 1} style={{ width: `${Math.min(pct, 1) * 100}%` }} />
        </div>
        <span className="dash-num w-12 text-right text-xs">{formatValue(pct, 'percent')}</span>
      </div>
    );
  }
  if (col.format === 'text' || col.format === undefined) return String(v);
  return <span className="dash-num">{formatValue(Number(v), col.format, { compact: Number(v) >= 1e5 })}</span>;
};

interface TablePanelProps {
  title: string;
  subtitle?: string;
  data: TableData | undefined;
  className?: string;
  maxHeight?: number;
  defaultSort?: string;
}

export const TablePanel: React.FC<TablePanelProps> = ({ title, subtitle, data, className, maxHeight = 460, defaultSort }) => {
  const [sortKey, setSortKey] = useState<string | undefined>(defaultSort);
  const [desc, setDesc] = useState<boolean>(true);
  const rows = useMemo(() => {
    if (!data) return [];
    if (!sortKey) return data.rows;
    return [...data.rows].sort((a, b) => {
      const av: TableCell = a[sortKey];
      const bv: TableCell = b[sortKey];
      const an: number = typeof av === 'number' ? av : Number.NEGATIVE_INFINITY;
      const bn: number = typeof bv === 'number' ? bv : Number.NEGATIVE_INFINITY;
      if (typeof av === 'string' && typeof bv === 'string') return desc ? bv.localeCompare(av) : av.localeCompare(bv);
      return desc ? bn - an : an - bn;
    });
  }, [data, sortKey, desc]);
  const onSort = (key: string) => {
    if (key === sortKey) setDesc((d: boolean) => !d);
    else {
      setSortKey(key);
      setDesc(true);
    }
  };
  return (
    <Panel title={title} subtitle={subtitle} className={className} bodyClassName="overflow-hidden">
      {!data || data.rows.length === 0 ? <PanelEmpty /> : (
        <div className="overflow-auto" style={{ maxHeight }}>
          <table className="w-full border-collapse text-sm">
            <thead className="sticky top-0 z-10" style={{ background: 'var(--card)' }}>
              <tr>
                {data.columns.map((c: TableColumn) => (
                  <th
                    key={c.key}
                    scope="col"
                    className={cn('dash-subtle whitespace-nowrap border-b border-border px-2 py-2 text-xs font-normal', c.align === 'right' ? 'text-right' : 'text-left')}
                  >
                    {c.format === 'text' || c.format === 'status' ? c.label : (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 px-1 text-xs font-normal"
                        onClick={() => onSort(c.key)}
                        aria-label={`按${c.label}排序`}
                      >
                        {c.label}
                        {sortKey === c.key ? (desc ? <ArrowDown className="size-3" /> : <ArrowUp className="size-3" />) : null}
                      </Button>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i: number) => (
                <tr key={String(r[data.columns[1]?.key] ?? i)} className="border-b border-border/50 last:border-b-0 hover:bg-[var(--dash-accent-soft)]">
                  {data.columns.map((c: TableColumn) => (
                    <td key={c.key} className={cn('whitespace-nowrap px-2 py-2', c.align === 'right' && 'text-right')}>
                      {renderCell(c, r[c.key])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
};

// ------------------------------------------------------------------ 排行榜列表（大屏）
interface RankListPanelProps {
  title: string;
  subtitle?: string;
  data: CategoryData | undefined;
  className?: string;
  limit?: number;
}

export const RankListPanel: React.FC<RankListPanelProps> = ({ title, subtitle, data, className, limit = 8 }) => {
  const items = (data?.items ?? []).slice(0, limit);
  const max: number = items.reduce((a: number, b) => Math.max(a, b.value), 0) || 1;
  return (
    <Panel title={title} subtitle={subtitle} className={className}>
      {items.length === 0 || !data ? <PanelEmpty /> : (
        <ol className="flex flex-col gap-2.5">
          {items.map((it, i: number) => (
            <li key={it.name} className="flex items-center gap-3">
              <Badge
                variant={i < 3 ? 'default' : 'secondary'}
                className="dash-num h-5 w-6 shrink-0 justify-center px-0 text-[11px]"
              >
                {i + 1}
              </Badge>
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex justify-between gap-2 text-sm">
                  <span className="truncate">{it.name}</span>
                  <span className="dash-num shrink-0 font-semibold">{formatValue(it.value, data.format, { compact: true })}</span>
                </div>
                <div className="dash-meter-track">
                  <div className="dash-meter-fill" style={{ width: `${(it.value / max) * 100}%` }} />
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </Panel>
  );
};
