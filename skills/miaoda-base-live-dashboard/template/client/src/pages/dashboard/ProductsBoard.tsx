import React from 'react';

import type { ProductsBoard as ProductsData } from '@shared/dashboard.interface';
import { DASH_RANGE_LABELS } from '@shared/dashboard.interface';
import { fetchProducts } from '@/api/dashboard';

import { boardDefaultRange } from '@/dashboard/boards';
import { BoardState } from '@/dashboard/components/BoardState';
import { CategoryPanel, ScatterPanel, StackedPanel } from '@/dashboard/components/ChartPanels';
import { KpiRow } from '@/dashboard/components/KpiTile';
import { useBoardFilters, useLiveQuery } from '@/dashboard/lib/hooks';

const ProductsBoard: React.FC = () => {
  const { range, city } = useBoardFilters(boardDefaultRange('products'));
  const q = useLiveQuery<ProductsData>(['dashboard', 'products', range, city], () => fetchProducts(range, city));
  const d: ProductsData | undefined = q.data;
  const rangeLabel: string = DASH_RANGE_LABELS[range];
  return (
    <BoardState isLoading={q.isLoading} error={q.error} hasData={Boolean(d)}>
      <div className="flex flex-col gap-3">
        <KpiRow items={d?.kpis ?? []} />
        <div className="grid gap-3 xl:grid-cols-12">
          <CategoryPanel
            id="products.top"
            title="爆品 TOP10"
            subtitle={`${rangeLabel}按销量`}
            data={d?.topProducts}
            className="xl:col-span-5"
            types={['bar', 'column', 'treemap']}
            defaultType="bar"
            height={340}
          />
          <CategoryPanel
            id="products.categories"
            title="品类销售额"
            subtitle={rangeLabel}
            data={d?.categories}
            className="xl:col-span-3"
            defaultType="donut"
            height={340}
          />
          <ScatterPanel
            id="products.priceMargin"
            title="价格 × 毛利 × 销量"
            subtitle="气泡越大销量越高"
            data={d?.priceMargin}
            className="xl:col-span-4"
            height={340}
          />
          <StackedPanel
            id="products.hourly"
            title="分时段品类需求"
            subtitle={`${rangeLabel}件数`}
            data={d?.hourlyByCategory}
            className="xl:col-span-8"
            defaultType="stacked"
            height={300}
          />
          <StackedPanel
            id="products.temperature"
            title="饮品冷热偏好"
            subtitle="热 / 冰 / 少冰"
            data={d?.temperatureMix}
            className="xl:col-span-4"
            defaultType="percent"
            horizontal
            height={300}
          />
        </div>
      </div>
    </BoardState>
  );
};

export default ProductsBoard;
