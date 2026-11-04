import React from 'react';

import type { StoresBoard as StoresData } from '@shared/dashboard.interface';
import { DASH_RANGE_LABELS } from '@shared/dashboard.interface';
import { fetchStores } from '@/api/dashboard';

import { boardDefaultRange } from '@/dashboard/boards';
import { BoardState } from '@/dashboard/components/BoardState';
import { CategoryPanel, MeterPanel, StackedPanel, TrendPanel } from '@/dashboard/components/ChartPanels';
import { KpiRow } from '@/dashboard/components/KpiTile';
import { TablePanel } from '@/dashboard/components/ListPanels';
import { useBoardFilters, useLiveQuery } from '@/dashboard/lib/hooks';

const StoresBoard: React.FC = () => {
  const { range, city } = useBoardFilters(boardDefaultRange('stores'));
  const q = useLiveQuery<StoresData>(['dashboard', 'stores', range, city], () => fetchStores(range, city));
  const d: StoresData | undefined = q.data;
  const rangeLabel: string = DASH_RANGE_LABELS[range];
  return (
    <BoardState isLoading={q.isLoading} error={q.error} hasData={Boolean(d)}>
      <div className="flex flex-col gap-3">
        <KpiRow items={d?.kpis ?? []} />
        <div className="grid gap-3 xl:grid-cols-12">
          <MeterPanel
            id="stores.achievement"
            title="整体目标达成"
            subtitle={range === 'today' ? '日目标 × 近 4 周同时段营收占比' : `${rangeLabel}累计目标`}
            data={d?.achievement}
            className="xl:col-span-3"
            height={260}
          />
          <TrendPanel
            id="stores.topTrend"
            title="TOP5 门店营收走势"
            subtitle={rangeLabel}
            data={d?.topStoresTrend}
            className="xl:col-span-9"
            defaultType="line"
            height={260}
          />
          <TablePanel
            title="门店排行榜"
            subtitle="点表头可排序；目标达成 = 营收 ÷ 目标"
            data={d?.leaderboard}
            className="xl:col-span-8 xl:row-span-2"
            maxHeight={620}
          />
          <StackedPanel
            id="stores.regionByType"
            title="大区 × 店型营收"
            subtitle={rangeLabel}
            data={d?.regionByType}
            className="xl:col-span-4"
            defaultType="stacked"
          />
          <CategoryPanel
            id="stores.types"
            title="店型店均营收"
            subtitle="不含装修门店"
            data={d?.storeTypes}
            className="xl:col-span-4"
            types={['column', 'bar', 'treemap']}
            defaultType="column"
          />
        </div>
      </div>
    </BoardState>
  );
};

export default StoresBoard;
