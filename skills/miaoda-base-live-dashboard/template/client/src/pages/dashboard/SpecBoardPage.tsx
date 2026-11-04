import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { CircleAlert } from 'lucide-react';

import type { SpecBoardData, SpecBoardMeta, SpecBoardsMeta, SpecPanelData, SpecPanelMeta } from '@shared/spec-board.interface';
import { Markdown } from '@/components/ui/markdown';
import { cn } from '@/lib/utils';
import { fetchSpecBoard, fetchSpecMeta } from '@/api/spec-board';

import { BoardState } from '@/dashboard/components/BoardState';
import { CategoryPanel, StackedPanel, TrendPanel } from '@/dashboard/components/ChartPanels';
import { KpiTile } from '@/dashboard/components/KpiTile';
import { TablePanel } from '@/dashboard/components/ListPanels';
import { LayoutSwitcher } from '@/dashboard/components/LayoutSwitcher';
import { Panel } from '@/dashboard/components/Panel';
import { CATEGORY_TYPES, STACKED_TYPES, TREND_TYPES } from '@/dashboard/charts/options';
import { useBoardFilters, useLiveQuery, usePanelType } from '@/dashboard/lib/hooks';
import { LAYOUTS, XL_SPAN, arrange, isLayoutKey, pickHero, roleOf, type LayoutKey, type Placement } from '@/dashboard/layouts';

/** 模板中心里「设为默认排版」写入的全局偏好（各看板自己切换过的优先） */
export const GLOBAL_LAYOUT_KEY = 'dash-layout-default';
const readGlobalLayout = (): string | null => {
  try {
    return window.localStorage.getItem(GLOBAL_LAYOUT_KEY);
  } catch {
    return null;
  }
};

const pick = <T extends string>(all: readonly T[], wanted: string[]): T[] => {
  const list: T[] = wanted.filter((w: string): w is T => (all as readonly string[]).includes(w));
  return list.length > 0 ? list : [...all];
};

interface SpecPanelProps {
  boardKey: string;
  meta: SpecPanelMeta;
  data: SpecPanelData | undefined;
  height: number | 'fill';
  className?: string;
}

/** 按面板 kind 选组件；数据形状与内置看板完全一致，风格 / 图表切换全部复用 */
const SpecPanel: React.FC<SpecPanelProps> = ({ boardKey, meta, data, height, className }) => {
  const pid: string = `spec.${boardKey}.${meta.id}`;
  const subtitle: string | undefined = meta.subtitle ?? (meta.notes.length ? meta.notes.join('；') : undefined);
  if (data?.kind === 'error') {
    return (
      <Panel title={meta.title} subtitle={subtitle} className={className}>
        <div className="dash-critical flex items-center gap-2 py-8 text-sm" role="alert">
          <CircleAlert className="size-4" aria-hidden />
          {data.message}
        </div>
      </Panel>
    );
  }
  if (meta.kind === 'kpi') {
    return (
      <div className={cn('min-w-0', className)}>
        {data?.kind === 'kpi' ? <KpiTile item={data.kpi} /> : <div className="dash-panel h-[108px]" />}
      </div>
    );
  }
  if (meta.kind === 'text') {
    return (
      <Panel title={meta.title} className={className}>
        <div className="prose prose-sm max-w-none text-foreground dark:prose-invert">
          <Markdown>{data?.kind === 'text' ? data.text : ''}</Markdown>
        </div>
      </Panel>
    );
  }
  if (meta.kind === 'trend') {
    const types = pick(TREND_TYPES, meta.chartTypes);
    return (
      <TrendPanel
        id={pid}
        title={meta.title}
        subtitle={subtitle}
        data={data?.kind === 'trend' ? data.trend : undefined}
        types={types}
        defaultType={pick(TREND_TYPES, [meta.defaultChart ?? types[0]])[0]}
        height={height}
        className={className}
      />
    );
  }
  if (meta.kind === 'stacked') {
    const types = pick(STACKED_TYPES, meta.chartTypes);
    return (
      <StackedPanel
        id={pid}
        title={meta.title}
        subtitle={subtitle}
        data={data?.kind === 'stacked' ? data.stacked : undefined}
        types={types}
        defaultType={pick(STACKED_TYPES, [meta.defaultChart ?? types[0]])[0]}
        height={height}
        className={className}
      />
    );
  }
  if (meta.kind === 'table') {
    return (
      <TablePanel
        title={meta.title}
        subtitle={subtitle}
        data={data?.kind === 'table' ? data.table : undefined}
        className={className}
      />
    );
  }
  const types = pick(CATEGORY_TYPES, meta.chartTypes);
  return (
    <CategoryPanel
      id={pid}
      title={meta.title}
      subtitle={subtitle}
      data={data?.kind === 'category' ? data.category : undefined}
      types={types}
      defaultType={pick(CATEGORY_TYPES, [meta.defaultChart ?? types[0]])[0]}
      height={height}
      className={className}
    />
  );
};

/** 配置驱动看板：由 dashboard-spec.json 编译而来（会议整理 / 仪表盘迁移 / 行业模板） */
const SpecBoardPage: React.FC = () => {
  const { boardKey = '' } = useParams();
  const metaQ = useQuery<SpecBoardsMeta>({ queryKey: ['spec', 'meta'], queryFn: fetchSpecMeta, staleTime: Infinity });
  const board: SpecBoardMeta | undefined = metaQ.data?.boards.find((b: SpecBoardMeta) => b.key === boardKey);
  if (!board) {
    return (
      <BoardState isLoading={metaQ.isLoading} error={metaQ.error} hasData={false}>
        <div className="dash-subtle py-20 text-center text-sm">看板「{boardKey}」不存在</div>
      </BoardState>
    );
  }
  return <SpecBoardBody key={board.key} board={board} />;
};

const SpecBoardBody: React.FC<{ board: SpecBoardMeta }> = ({ board }) => {
  const boardKey: string = board.key;
  const { range } = useBoardFilters(board.defaultRange);
  const q = useLiveQuery<SpecBoardData>(['spec', boardKey, board.hasTimeFilter ? range : 'all'], () =>
    fetchSpecBoard(boardKey, board.hasTimeFilter ? range : undefined),
  );
  const hasOriginal: boolean = board.panels.some((p: SpecPanelMeta) => Boolean(p.layout));
  const globalDefault: string | null = readGlobalLayout();
  const preferred: LayoutKey =
    globalDefault && isLayoutKey(globalDefault)
      ? globalDefault
      : board.layout && isLayoutKey(board.layout)
        ? board.layout
        : hasOriginal
          ? 'original'
          : 'executive';
  const [layout, setLayout] = usePanelType<LayoutKey>(`layout.${boardKey}`, LAYOUTS, preferred);

  const panels: Record<string, SpecPanelData> = q.data?.panels ?? {};
  const switcher = (
    <div className="mb-3 flex justify-end">
      <LayoutSwitcher value={layout} onChange={setLayout} hasOriginal={hasOriginal} />
    </div>
  );

  if (layout === 'command') {
    const hero: string | undefined = pickHero(board.panels);
    const col = (role: (p: SpecPanelMeta) => boolean): SpecPanelMeta[] => board.panels.filter(role);
    const left: SpecPanelMeta[] = col((p: SpecPanelMeta) => p.kind === 'kpi' || p.kind === 'text');
    const center: SpecPanelMeta[] = col((p: SpecPanelMeta) => ['hero', 'wide'].includes(roleOf(p, hero)));
    const right: SpecPanelMeta[] = col((p: SpecPanelMeta) => roleOf(p, hero) === 'side');
    const render = (list: SpecPanelMeta[], h: number) =>
      list.map((p: SpecPanelMeta) => (
        <SpecPanel key={p.id} boardKey={boardKey} meta={p} data={panels[p.id]} height={p.id === hero ? 340 : h} />
      ));
    return (
      <BoardState isLoading={q.isLoading} error={q.error} hasData={Boolean(q.data)}>
        {switcher}
        <div className="grid gap-3 xl:grid-cols-12">
          <div className="flex flex-col gap-3 xl:col-span-3">{render(left, 200)}</div>
          <div className="flex flex-col gap-3 xl:col-span-6">{render(center, 280)}</div>
          <div className="flex flex-col gap-3 xl:col-span-3">{render(right, 240)}</div>
        </div>
      </BoardState>
    );
  }

  const placed: Placement[] = arrange(board.panels, layout);
  return (
    <BoardState isLoading={q.isLoading} error={q.error} hasData={Boolean(q.data)}>
      {switcher}
      <div className={cn('grid gap-3 xl:grid-cols-12', layout === 'focus' && 'mx-auto max-w-4xl')}>
        {placed.map((pl: Placement) => (
          <SpecPanel
            key={pl.panel.id}
            boardKey={boardKey}
            meta={pl.panel}
            data={panels[pl.panel.id]}
            height={pl.height || 260}
            className={layout === 'focus' && pl.panel.kind !== 'kpi' ? 'xl:col-span-12' : XL_SPAN[pl.span]}
          />
        ))}
      </div>
    </BoardState>
  );
};

export default SpecBoardPage;
