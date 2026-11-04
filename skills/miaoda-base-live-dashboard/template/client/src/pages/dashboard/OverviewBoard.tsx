import React from 'react';

import type { OverviewBoard as OverviewData } from '@shared/dashboard.interface';
import { DASH_RANGE_LABELS } from '@shared/dashboard.interface';
import { fetchOverview } from '@/api/dashboard';

import { boardDefaultRange } from '@/dashboard/boards';
import { BoardState } from '@/dashboard/components/BoardState';
import { CategoryPanel, HeatmapPanel, TrendPanel } from '@/dashboard/components/ChartPanels';
import { KpiRow } from '@/dashboard/components/KpiTile';
import { LiveFeedPanel } from '@/dashboard/components/ListPanels';
import { useBoardFilters, useLiveQuery } from '@/dashboard/lib/hooks';

const OverviewBoard: React.FC = () => {
  const { range, city } = useBoardFilters(boardDefaultRange('overview'));
  const q = useLiveQuery<OverviewData>(['dashboard', 'overview', range, city], () => fetchOverview(range, city));
  const d: OverviewData | undefined = q.data;
  const rangeLabel: string = DASH_RANGE_LABELS[range];
  return (
    <BoardState isLoading={q.isLoading} error={q.error} hasData={Boolean(d)}>
      <div className="flex flex-col gap-3">
        <KpiRow items={d?.kpis ?? []} />
        <div className="grid gap-3 xl:grid-cols-12">
          <TrendPanel
            id="overview.trend"
            title="营收走势"
            subtitle={range === 'today' ? '按小时，虚线为昨日' : '按天，虚线为上一周期'}
            data={d?.trend}
            className="xl:col-span-8"
            height={300}
          />
          <LiveFeedPanel items={d?.feed} className="xl:col-span-4 xl:row-span-2" height={640} />
          <CategoryPanel
            id="overview.channels"
            title="渠道营收"
            subtitle={rangeLabel}
            data={d?.channels}
            className="xl:col-span-4"
            defaultType="bar"
          />
          <CategoryPanel
            id="overview.categories"
            title="品类销售构成"
            subtitle={rangeLabel}
            data={d?.categories}
            className="xl:col-span-4"
            defaultType="treemap"
          />
          <HeatmapPanel
            id="overview.heatmap"
            title="下单时段热力"
            subtitle="近 30 天各时段订单量"
            data={d?.heatmap}
            className="xl:col-span-7"
            height={300}
          />
          <CategoryPanel
            id="overview.cities"
            title="城市营收"
            subtitle={rangeLabel}
            data={d?.cities}
            className="xl:col-span-5"
            defaultType="column"
            height={300}
          />
        </div>
      </div>
    </BoardState>
  );
};

export default OverviewBoard;
