import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

import type { DashRange } from '@shared/dashboard.interface';

import { DASHBOARD_CONFIG } from './dashboard.config';

dayjs.extend(utc);
dayjs.extend(timezone);

export interface TimeWindow {
  start: Date;
  end: Date;
  prevStart: Date;
  prevEnd: Date;
  /** 窗口覆盖的自然日数 */
  days: number;
  granularity: 'hour' | 'day';
  /** 当前窗口的分桶键（hour: '00'..'23'；day: 'YYYY-MM-DD'） */
  bucketKeys: string[];
  /** 对比窗口的分桶键，与 bucketKeys 按下标对齐 */
  prevBucketKeys: string[];
  /** 分桶展示标签 */
  bucketLabels: string[];
  deltaLabel: string;
}

const TZ: string = DASHBOARD_CONFIG.timezone;

export const nowInTz = (): dayjs.Dayjs => dayjs().tz(TZ);

export const buildWindow = (range: DashRange): TimeWindow => {
  const now: dayjs.Dayjs = nowInTz();
  const today: dayjs.Dayjs = now.startOf('day');
  if (range === 'today') {
    const hours: string[] = Array.from({ length: 24 }, (_v: unknown, i: number) =>
      String(i).padStart(2, '0'),
    );
    return {
      start: today.toDate(),
      end: now.toDate(),
      prevStart: today.subtract(1, 'day').toDate(),
      prevEnd: now.subtract(1, 'day').toDate(),
      days: 1,
      granularity: 'hour',
      bucketKeys: hours,
      prevBucketKeys: hours,
      bucketLabels: hours.map((h: string) => `${h}:00`),
      deltaLabel: '较昨日同期',
    };
  }
  const days: number = range === '7d' ? 7 : range === '90d' ? 90 : 30;
  const start: dayjs.Dayjs = today.subtract(days - 1, 'day');
  const prevStart: dayjs.Dayjs = start.subtract(days, 'day');
  const keys: string[] = [];
  const prevKeys: string[] = [];
  const labels: string[] = [];
  for (let i = 0; i < days; i += 1) {
    keys.push(start.add(i, 'day').format('YYYY-MM-DD'));
    prevKeys.push(prevStart.add(i, 'day').format('YYYY-MM-DD'));
    // 最后一天是今天、还没过完：标成「今日」，避免把未完结的一天误读为下跌
    labels.push(i === days - 1 ? '今日' : start.add(i, 'day').format('MM-DD'));
  }
  return {
    start: start.toDate(),
    end: now.toDate(),
    prevStart: prevStart.toDate(),
    prevEnd: now.subtract(days, 'day').toDate(),
    days,
    granularity: 'day',
    bucketKeys: keys,
    prevBucketKeys: prevKeys,
    bucketLabels: labels,
    deltaLabel: `较前 ${days} 天`,
  };
};

/** 今日已过营业时长占比（用于把日目标折算成「截至此刻」的目标） */
export const elapsedBusinessRatio = (): number => {
  const now: dayjs.Dayjs = nowInTz();
  const { open, close } = DASHBOARD_CONFIG.businessHours;
  const hour: number = now.hour() + now.minute() / 60;
  if (hour <= open) return 0.02;
  if (hour >= close) return 1;
  return (hour - open) / (close - open);
};

export const toIso = (v: Date | string | null | undefined): string | null => {
  if (!v) return null;
  return dayjs(v).toISOString();
};
