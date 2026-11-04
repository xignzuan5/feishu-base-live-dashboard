import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { ArrowLeft, Coffee, Maximize2 } from 'lucide-react';

import type { DashboardMeta, LiveBoard } from '@shared/dashboard.interface';
import { Button } from '@/components/ui/button';
import { fetchLive, fetchMeta } from '@/api/dashboard';

import { BoardState } from '@/dashboard/components/BoardState';
import { CategoryPanel, TrendPanel } from '@/dashboard/components/ChartPanels';
import { KpiTile } from '@/dashboard/components/KpiTile';
import { LiveFeedPanel, RankListPanel } from '@/dashboard/components/ListPanels';
import { LiveBadge, StyleSwitcher } from '@/dashboard/components/ShellParts';
import { formatFullClock } from '@/dashboard/lib/format';
import { useBoardFilters, useLiveQuery, useNow } from '@/dashboard/lib/hooks';

const Clock: React.FC = () => {
  const now: number = useNow();
  const { time, date } = formatFullClock(now);
  return (
    <div className="text-right">
      <div className="dash-num dash-kpi-value text-2xl font-semibold leading-none">{time}</div>
      <div className="dash-subtle mt-1 text-xs">{date}</div>
    </div>
  );
};

const enterFullscreen = (): void => {
  const el: HTMLElement = document.documentElement;
  if (document.fullscreenElement) {
    void document.exitFullscreen();
  } else if (el.requestFullscreen) {
    void el.requestFullscreen();
  }
};

/** 投屏大屏：无页头导航，固定一屏，适合会议室 / 门店电视 */
const BigScreenBoard: React.FC = () => {
  const location = useLocation();
  const { city } = useBoardFilters('today');
  const meta = useLiveQuery<DashboardMeta>(['dashboard', 'meta'], fetchMeta);
  const q = useLiveQuery<LiveBoard>(['dashboard', 'live', city], () => fetchLive(city));
  const d: LiveBoard | undefined = q.data;
  return (
    <div className="dash-root flex min-h-screen flex-col px-4 py-4 xl:h-screen xl:overflow-hidden xl:px-6">
      <header className="mb-4 flex flex-wrap items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <NavLink to={{ pathname: '/', search: location.search }} aria-label="返回看板">
            <ArrowLeft className="size-5" />
          </NavLink>
        </Button>
        <span
          className="flex size-10 items-center justify-center rounded-lg"
          style={{ background: 'var(--dash-accent-soft)', color: 'var(--dash-accent)' }}
        >
          <Coffee className="size-6" aria-hidden />
        </span>
        <div className="min-w-0">
          <h1 className="dash-panel-title truncate text-xl xl:text-2xl">{meta.data?.title ?? '经营实时大屏'}</h1>
          <div className="dash-subtle mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs">
            <span>{city === 'all' ? '全部城市' : city}</span>
            <span>今日实时</span>
            <span>数据来自飞书多维表格，每 5 秒刷新</span>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <LiveBadge sync={d?.sync} fetching={q.isFetching} lastFetchedAt={q.dataUpdatedAt} />
          <StyleSwitcher />
          <Button variant="outline" size="icon" onClick={enterFullscreen} aria-label="全屏">
            <Maximize2 className="size-4" />
          </Button>
          <Clock />
        </div>
      </header>

      <BoardState isLoading={q.isLoading} error={q.error} hasData={Boolean(d)}>
        <div className="grid min-h-0 flex-1 gap-3 xl:grid-cols-12 xl:grid-rows-[auto_1fr_1fr]">
          <div className="grid grid-cols-2 gap-3 xl:col-span-9 xl:grid-cols-4">
            {(d?.kpis ?? []).map((k) => (
              <KpiTile key={k.key} item={k} size="big" />
            ))}
          </div>
          <LiveFeedPanel
            title="订单实时滚动"
            subtitle="新订单高亮闪入"
            items={d?.feed}
            className="xl:col-span-3 xl:row-span-3"
            height={760}
            dense
          />
          <TrendPanel
            id="big.today"
            title="今日 vs 昨日 营收（按小时）"
            data={d?.todayVsYesterday}
            className="xl:col-span-6"
            defaultType="area"
            height="fill"
          />
          <TrendPanel
            id="big.lastHour"
            title="最近 60 分钟订单（每 5 分钟）"
            data={d?.lastHour}
            className="xl:col-span-3"
            types={['bar', 'line']}
            defaultType="bar"
            height="fill"
          />
          <RankListPanel title="城市营收榜" data={d?.cities} className="xl:col-span-3" limit={8} />
          <CategoryPanel
            id="big.channels"
            title="渠道订单占比"
            data={d?.channels}
            className="xl:col-span-3"
            types={['donut', 'bar', 'treemap']}
            defaultType="donut"
            height="fill"
          />
          <RankListPanel title="今日爆品" data={d?.topProducts} className="xl:col-span-3" limit={8} />
        </div>
      </BoardState>
    </div>
  );
};

export default BigScreenBoard;
