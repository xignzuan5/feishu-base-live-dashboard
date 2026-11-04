import type { ValueFormat } from '@shared/dashboard.interface';

/**
 * 业务时区：与 server/modules/dashboard/dashboard.config.ts 的 timezone 保持一致。
 * 所有时间都按它展示，避免在海外 / 出差时看板显示成本地时间。
 */
export const BUSINESS_TZ = 'Asia/Shanghai';

const nf0 = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 1 });
const nf2 = new Intl.NumberFormat('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** 大数用「万」缩写，保留 1~2 位小数 */
export const compactNumber = (v: number): string => {
  const abs: number = Math.abs(v);
  if (abs >= 1e8) return `${nf2.format(v / 1e8)}亿`;
  if (abs >= 1e4) return `${nf1.format(v / 1e4)}万`;
  return nf0.format(v);
};

export interface FormatOptions {
  compact?: boolean;
  /** 货币是否保留两位小数（默认：小于 1000 时保留） */
  cents?: boolean;
}

export const formatValue = (v: number | null | undefined, format: ValueFormat, opts: FormatOptions = {}): string => {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  switch (format) {
    case 'currency': {
      if (opts.compact && Math.abs(v) >= 1e4) return `¥${compactNumber(v)}`;
      const cents: boolean = opts.cents ?? Math.abs(v) < 1000;
      return `¥${cents ? nf2.format(v) : nf0.format(v)}`;
    }
    case 'percent':
      return `${nf1.format(v * 100)}%`;
    case 'decimal':
      return nf2.format(v);
    default:
      return opts.compact ? compactNumber(v) : nf0.format(v);
  }
};

/** 变化量：率变化用 ±x.x%，百分点用 ±x.x pt */
export const formatDelta = (delta: number | null, format: ValueFormat): string => {
  if (delta === null || !Number.isFinite(delta)) return '—';
  const sign: string = delta > 0 ? '+' : delta < 0 ? '−' : '±';
  const abs: number = Math.abs(delta) * 100;
  return format === 'percent' ? `${sign}${nf1.format(abs)} pt` : `${sign}${nf1.format(abs)}%`;
};

export const formatClock = (iso: string | null | undefined): string => {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleTimeString('zh-CN', {
    timeZone: BUSINESS_TZ,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
};

export const formatShortTime = (iso: string): string => {
  const d = new Date(iso);
  return d.toLocaleTimeString('zh-CN', { timeZone: BUSINESS_TZ, hour: '2-digit', minute: '2-digit', hour12: false });
};

export const secondsAgo = (iso: string | null | undefined, now: number): number | null => {
  if (!iso) return null;
  return Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
};

export const formatFullClock = (ms: number): { time: string; date: string } => {
  const d = new Date(ms);
  return {
    time: d.toLocaleTimeString('zh-CN', { timeZone: BUSINESS_TZ, hour12: false }),
    date: d.toLocaleDateString('zh-CN', {
      timeZone: BUSINESS_TZ,
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      weekday: 'long',
    }),
  };
};
