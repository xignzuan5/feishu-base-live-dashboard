import React from 'react';

import type { MembersBoard as MembersData } from '@shared/dashboard.interface';
import { DASH_RANGE_LABELS } from '@shared/dashboard.interface';
import { fetchMembers } from '@/api/dashboard';

import { boardDefaultRange } from '@/dashboard/boards';
import { BoardState } from '@/dashboard/components/BoardState';
import { CategoryPanel, StackedPanel, TrendPanel } from '@/dashboard/components/ChartPanels';
import { KpiRow } from '@/dashboard/components/KpiTile';
import { TablePanel } from '@/dashboard/components/ListPanels';
import { useBoardFilters, useLiveQuery } from '@/dashboard/lib/hooks';

const MembersBoard: React.FC = () => {
  const { range, city } = useBoardFilters(boardDefaultRange('members'));
  const q = useLiveQuery<MembersData>(['dashboard', 'members', range, city], () => fetchMembers(range, city));
  const d: MembersData | undefined = q.data;
  const rangeLabel: string = DASH_RANGE_LABELS[range];
  return (
    <BoardState isLoading={q.isLoading} error={q.error} hasData={Boolean(d)}>
      <div className="flex flex-col gap-3">
        <KpiRow items={d?.kpis ?? []} />
        <div className="grid gap-3 xl:grid-cols-12">
          <TrendPanel
            id="members.trend"
            title="会员 / 非会员订单"
            subtitle={rangeLabel}
            data={d?.memberTrend}
            className="xl:col-span-8"
            defaultType="area"
            stack
            height={290}
          />
          <CategoryPanel
            id="members.ratings"
            title="订单评价分布"
            subtitle={`${rangeLabel}已评价订单`}
            data={d?.ratings}
            className="xl:col-span-4"
            types={['column', 'bar', 'segmented', 'donut']}
            defaultType="column"
            height={290}
          />
          <StackedPanel
            id="members.levels"
            title="会员等级：总量 vs 活跃"
            subtitle={rangeLabel}
            data={d?.levels}
            className="xl:col-span-6"
            types={['grouped', 'stacked']}
            defaultType="grouped"
          />
          <StackedPanel
            id="members.ageGender"
            title="会员画像：年龄 × 性别"
            subtitle="全部会员"
            data={d?.ageGender}
            className="xl:col-span-6"
            defaultType="stacked"
          />
          <TablePanel
            title="营销活动效果"
            subtitle="活动全周期；投入产出比 = 带动营收 ÷ 让利"
            data={d?.campaigns}
            className="xl:col-span-12"
            maxHeight={420}
          />
        </div>
      </div>
    </BoardState>
  );
};

export default MembersBoard;
