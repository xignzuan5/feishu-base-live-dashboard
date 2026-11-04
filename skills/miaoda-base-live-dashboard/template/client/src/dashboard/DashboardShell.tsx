import React from 'react';
import { NavLink, Outlet, matchPath, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Database, LayoutDashboard, LayoutGrid, LayoutTemplate, MonitorPlay } from 'lucide-react';

import type { DashboardMeta } from '@shared/dashboard.interface';
import type { SpecBoardMeta, SpecBoardsMeta } from '@shared/spec-board.interface';
import { fetchSpecMeta } from '@/api/spec-board';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { fetchMeta } from '@/api/dashboard';

import { BOARDS, boardByPath, type BoardMeta } from './boards';
import { BoardFilterBar, LiveBadge, StyleSwitcher } from './components/ShellParts';
import { useBoardFilters, useLiveQuery } from './lib/hooks';

/** 看板通用外壳：页头（品牌 / 看板导航 / 实时状态 / 风格切换）+ 筛选条 + 内容 */
export const DashboardShell: React.FC = () => {
  const location = useLocation();
  const specMeta = useQuery<SpecBoardsMeta>({ queryKey: ['spec', 'meta'], queryFn: fetchSpecMeta, staleTime: Infinity });
  const specBoards: SpecBoardMeta[] = specMeta.data?.boards ?? [];
  const specKey: string | undefined = matchPath('/spec/:key', location.pathname)?.params.key;
  const specBoard: SpecBoardMeta | undefined = specBoards.find((b: SpecBoardMeta) => b.key === specKey);
  const builtin: BoardMeta = boardByPath(location.pathname);
  const onTemplates: boolean = Boolean(matchPath('/templates', location.pathname));
  const board = specBoard
    ? { label: specBoard.label, description: specBoard.description, defaultRange: specBoard.defaultRange }
    : onTemplates
      ? { label: '模板中心', description: '挑选行业看板模板、风格和排版', defaultRange: builtin.defaultRange }
      : builtin;
  const filters = useBoardFilters(board.defaultRange);
  const metaQuery = useLiveQuery<DashboardMeta>(['dashboard', 'meta'], fetchMeta);
  const meta: DashboardMeta | undefined = metaQuery.data;

  return (
    <div className="dash-root">
      <header className="dash-header sticky top-0 z-30">
        <div className="mx-auto flex max-w-[1680px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 md:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <span
              className="flex size-9 shrink-0 items-center justify-center rounded-lg"
              style={{ background: 'var(--dash-accent-soft)', color: 'var(--dash-accent)' }}
            >
              <LayoutDashboard className="size-5" aria-hidden />
            </span>
            <div className="min-w-0">
              <h1 className="dash-panel-title truncate text-base">{meta?.title ?? '经营实时看板'}</h1>
              <p className="dash-subtle truncate text-xs">数据来自飞书多维表格，改动几秒内同步</p>
            </div>
          </div>

          <nav aria-label="看板类型" className="order-3 flex w-full gap-1 overflow-x-auto lg:order-none lg:w-auto">
            {BOARDS.filter((b: BoardMeta) => !b.standalone).map((b: BoardMeta) => (
              <NavLink
                key={b.key}
                to={{ pathname: b.path, search: location.search }}
                end={b.path === '/'}
                className={({ isActive }: { isActive: boolean }) =>
                  cn(
                    'flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors',
                    isActive ? 'bg-accent text-accent-foreground font-medium' : 'dash-subtle hover:text-foreground',
                  )
                }
              >
                <b.icon className="size-4" aria-hidden />
                {b.label}
              </NavLink>
            ))}
            {specBoard ? (
              <NavLink
                key={`spec-${specBoard.key}`}
                to={{ pathname: `/spec/${specBoard.key}`, search: location.search }}
                className={({ isActive }: { isActive: boolean }) =>
                  cn(
                    'flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors',
                    isActive ? 'bg-accent text-accent-foreground font-medium' : 'dash-subtle hover:text-foreground',
                  )
                }
              >
                <LayoutTemplate className="size-4" aria-hidden />
                <span className="max-w-[10rem] truncate">{specBoard.label}</span>
              </NavLink>
            ) : null}
            <NavLink
              to={{ pathname: '/templates', search: location.search }}
              className={({ isActive }: { isActive: boolean }) =>
                cn(
                  'flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors',
                  isActive ? 'bg-accent text-accent-foreground font-medium' : 'dash-subtle hover:text-foreground',
                )
              }
            >
              <LayoutGrid className="size-4" aria-hidden />
              模板中心
              {specBoards.length > 0 ? <span className="dash-subtle text-xs">{specBoards.length}</span> : null}
            </NavLink>
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <LiveBadge sync={meta?.sync} fetching={metaQuery.isFetching} lastFetchedAt={metaQuery.dataUpdatedAt} />
            <StyleSwitcher />
            {meta?.baseUrl ? (
              <Button variant="outline" size="sm" asChild>
                <a href={meta.baseUrl} target="_blank" rel="noreferrer" aria-label="打开数据源多维表格">
                  <Database className="size-4" />
                  <span className="hidden xl:inline">多维表格</span>
                </a>
              </Button>
            ) : null}
            <Button variant="default" size="sm" asChild>
              <NavLink to={{ pathname: '/bigscreen', search: location.search }} aria-label="进入实时大屏">
                <MonitorPlay className="size-4" />
                <span className="hidden xl:inline">大屏</span>
              </NavLink>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1680px] px-4 pb-10 pt-5 md:px-6">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            <h2 className="dash-panel-title text-xl">{board.label}</h2>
            <p className="dash-subtle mt-1 text-sm">{board.description}</p>
          </div>
          {onTemplates ? null : <BoardFilterBar
            range={filters.range}
            city={filters.city}
            cities={meta?.cities ?? []}
            onRange={filters.setRange}
            onCity={filters.setCity}
            ranges={specKey && !specBoard?.hasTimeFilter ? [] : undefined}
            showCity={!specKey}
          />}
        </div>
        <Outlet />
      </main>
    </div>
  );
};
