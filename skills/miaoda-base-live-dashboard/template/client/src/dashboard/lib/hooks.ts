import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { keepPreviousData, useQuery, type UseQueryResult } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';

import { isDashRange, type DashRange } from '@shared/dashboard.interface';

/** 实时轮询间隔：多维表格 → 应用数据库同步是秒级，前端 5 秒拉一次 */
export const LIVE_INTERVAL_MS = 5000;

export const useLiveQuery = <T,>(key: unknown[], fetcher: () => Promise<T>, interval: number = LIVE_INTERVAL_MS): UseQueryResult<T> =>
  useQuery<T>({
    queryKey: key,
    queryFn: fetcher,
    refetchInterval: interval,
    refetchIntervalInBackground: false,
    placeholderData: keepPreviousData,
    staleTime: interval / 2,
  });

export interface BoardFilters {
  range: DashRange;
  city: string;
  setRange: (r: DashRange) => void;
  setCity: (c: string) => void;
}

/** 时间范围 / 城市放在 URL 上：切换看板时保留，分享链接也能还原 */
export const useBoardFilters = (defaultRange: DashRange = 'today'): BoardFilters => {
  const [params, setParams] = useSearchParams();
  const rawRange: string = params.get('range') ?? '';
  const range: DashRange = isDashRange(rawRange) ? rawRange : defaultRange;
  const city: string = params.get('city') ?? 'all';

  const update = useCallback(
    (key: string, value: string, fallback: string) => {
      const next = new URLSearchParams(params);
      if (value === fallback) next.delete(key);
      else next.set(key, value);
      setParams(next, { replace: true });
    },
    [params, setParams],
  );

  return {
    range,
    city,
    setRange: (r: DashRange) => update('range', r, defaultRange),
    setCity: (c: string) => update('city', c, 'all'),
  };
};

/** 面板的图表类型选择：记在本地，下次打开保持 */
export const usePanelType = <T extends string>(panelId: string, allowed: readonly T[], fallback: T): [T, (t: T) => void] => {
  const storageKey: string = `dash-panel-type:${panelId}`;
  const [value, setValue] = useState<T>(() => {
    try {
      const saved: string | null = window.localStorage.getItem(storageKey);
      if (saved && (allowed as readonly string[]).includes(saved)) return saved as T;
    } catch {
      // 读不到存储时用默认类型
    }
    return fallback;
  });
  const set = useCallback(
    (t: T) => {
      setValue(t);
      try {
        window.localStorage.setItem(storageKey, t);
      } catch {
        // 忽略存储失败
      }
    },
    [storageKey],
  );
  return [value, set];
};

/** 每秒跳一次的时钟（显示「x 秒前同步」） */
export const useNow = (tickMs: number = 1000): number => {
  const [now, setNow] = useState<number>(() => Date.now());
  useEffect(() => {
    const id: number = window.setInterval(() => setNow(Date.now()), tickMs);
    return () => window.clearInterval(id);
  }, [tickMs]);
  return now;
};

/** 记住上一轮出现过的 id，返回本轮新出现的 id 集合（订单流闪入动画） */
export const useNewIds = (ids: string[]): Set<string> => {
  const seen = useRef<Set<string> | null>(null);
  const fresh = useMemo<Set<string>>(() => {
    if (seen.current === null) return new Set<string>();
    const prev: Set<string> = seen.current;
    return new Set<string>(ids.filter((id: string) => !prev.has(id)));
  }, [ids]);
  useEffect(() => {
    seen.current = new Set<string>(ids);
  }, [ids]);
  return fresh;
};

/** 数值变化时返回递增的 key，用来重放「刷新高亮」动画 */
export const useChangeKey = (value: number | string | null | undefined): number => {
  const prev = useRef<number | string | null | undefined>(value);
  const [key, setKey] = useState<number>(0);
  useEffect(() => {
    if (prev.current !== value) {
      prev.current = value;
      setKey((k: number) => k + 1);
    }
  }, [value]);
  return key;
};
