import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Check } from 'lucide-react';

import type { SpecBoardMeta, SpecBoardsMeta } from '@shared/spec-board.interface';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import { fetchSpecMeta } from '@/api/spec-board';

import { BOARDS, type BoardMeta } from '@/dashboard/boards';
import { Sketch } from '@/dashboard/components/LayoutSwitcher';
import { LAYOUTS, LAYOUT_META, isLayoutKey, type LayoutKey } from '@/dashboard/layouts';
import { useDashStyle } from '@/dashboard/theme/DashStyleProvider';
import { CHART_PALETTES, DASH_STYLES, DASH_STYLE_META, type DashStyle } from '@/dashboard/theme/styles';

import { GLOBAL_LAYOUT_KEY } from './SpecBoardPage';

const TONE_LABEL: Record<string, string> = {
  restrained: '克制',
  corporate: '商务',
  editorial: '人文',
  technical: '科技',
};

/** 风格缩略预览：只用该风格自己的色值画一张迷你看板 */
const StylePreview: React.FC<{ style: DashStyle }> = ({ style }) => {
  const m = DASH_STYLE_META[style].preview;
  const pal = CHART_PALETTES[style];
  const bars: number[] = [0.55, 0.8, 0.42, 0.68, 0.35, 0.5];
  return (
    <div className="h-[132px] overflow-hidden rounded-md p-2.5" style={{ background: m.bg }} aria-hidden>
      <div className="mb-2 h-1.5 w-20 rounded-sm" style={{ background: m.text, opacity: 0.85 }} />
      <div className="grid grid-cols-3 gap-1.5">
        {[0, 1, 2].map((i: number) => (
          <div key={i} className="rounded-sm p-1.5" style={{ background: m.panel, border: `1px solid ${m.border}` }}>
            <div className="mb-1 h-1 w-6 rounded-sm" style={{ background: m.muted }} />
            <div className="h-2 w-10 rounded-sm" style={{ background: m.text }} />
          </div>
        ))}
      </div>
      <div className="mt-1.5 grid grid-cols-5 gap-1.5">
        <div className="col-span-3 rounded-sm p-1.5" style={{ background: m.panel, border: `1px solid ${m.border}` }}>
          <svg viewBox="0 0 100 34" className="h-[44px] w-full">
            <polyline
              points="0,26 14,22 28,24 42,14 56,17 70,8 84,12 100,4"
              fill="none"
              stroke={pal.single}
              strokeWidth="2.2"
              strokeLinejoin="round"
            />
            <polyline points="0,28 14,27 28,25 42,24 56,22 70,20 84,21 100,18" fill="none" stroke={pal.compare} strokeWidth="1.4" strokeDasharray="3 3" />
          </svg>
        </div>
        <div className="col-span-2 flex items-end gap-[3px] rounded-sm p-1.5" style={{ background: m.panel, border: `1px solid ${m.border}` }}>
          {bars.map((h: number, i: number) => (
            <div key={i} className="flex-1 rounded-t-[2px]" style={{ height: `${h * 40}px`, background: pal.categorical[i] }} />
          ))}
        </div>
      </div>
    </div>
  );
};

const groupBoards = (boards: SpecBoardMeta[]): [string, SpecBoardMeta[]][] => {
  const map = new Map<string, SpecBoardMeta[]>();
  boards.forEach((b: SpecBoardMeta) => map.set(b.group, [...(map.get(b.group) ?? []), b]));
  return Array.from(map.entries());
};

/** 模板中心：看板模板（按行业）、风格、排版，一处挑选 */
const TemplateCenter: React.FC = () => {
  const location = useLocation();
  const { style, setStyle } = useDashStyle();
  const meta = useQuery<SpecBoardsMeta>({ queryKey: ['spec', 'meta'], queryFn: fetchSpecMeta, staleTime: Infinity });
  const [defaultLayout, setDefaultLayout] = useState<string | null>(() => {
    try {
      return window.localStorage.getItem(GLOBAL_LAYOUT_KEY);
    } catch {
      return null;
    }
  });
  const chooseLayout = (k: LayoutKey) => {
    setDefaultLayout(k);
    try {
      window.localStorage.setItem(GLOBAL_LAYOUT_KEY, k);
      Object.keys(window.localStorage)
        .filter((key: string) => key.startsWith('dash-panel-type:layout.'))
        .forEach((key: string) => window.localStorage.removeItem(key));
    } catch {
      // 存储不可用时只在本次生效
    }
  };
  const builtin: BoardMeta[] = BOARDS.filter((b: BoardMeta) => !b.standalone);
  const groups: [string, SpecBoardMeta[]][] = groupBoards(meta.data?.boards ?? []);

  return (
    <Tabs defaultValue="boards" className="gap-4">
      <TabsList>
        <TabsTrigger value="boards">看板模板</TabsTrigger>
        <TabsTrigger value="styles">风格（{DASH_STYLES.length}）</TabsTrigger>
        <TabsTrigger value="layouts">排版（{LAYOUTS.length}）</TabsTrigger>
      </TabsList>

      <TabsContent value="boards" className="flex flex-col gap-6">
        <section aria-label="零售连锁（精细排版）">
          <h3 className="dash-panel-title mb-3 text-base">零售连锁</h3>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {builtin.map((b: BoardMeta) => (
              <div key={b.key} className="dash-panel flex flex-col gap-2 p-4">
                <div className="flex items-center gap-2">
                  <b.icon className="dash-accent size-4" aria-hidden />
                  <span className="font-medium">{b.label}</span>
                </div>
                <p className="dash-subtle flex-1 text-sm">{b.description}</p>
                <Button asChild variant="secondary" size="sm" className="self-start">
                  <Link to={{ pathname: b.path, search: location.search }}>打开{b.label}</Link>
                </Button>
              </div>
            ))}
          </div>
        </section>
        {groups.map(([group, boards]) => (
          <section key={group} aria-label={group}>
            <h3 className="dash-panel-title mb-3 text-base">{group}</h3>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {boards.map((b: SpecBoardMeta) => {
                const hasCoords: boolean = b.panels.some((pm) => Boolean(pm.layout));
                const layout: LayoutKey =
                  b.layout && isLayoutKey(b.layout) ? b.layout : hasCoords ? 'original' : 'executive';
                return (
                  <div key={b.key} className="dash-panel flex flex-col gap-2 p-4">
                    <Sketch cells={LAYOUT_META[layout].sketch} active className="h-16 w-full" />
                    <span className="font-medium">{b.label}</span>
                    <p className="dash-subtle flex-1 text-sm">{b.description}</p>
                    <div className="flex flex-wrap gap-1.5">
                      <Badge variant="outline">{b.panels.length} 个面板</Badge>
                      <Badge variant="outline">推荐排版：{LAYOUT_META[layout].label}</Badge>
                    </div>
                    <Button asChild variant="secondary" size="sm" className="self-start">
                      <Link to={{ pathname: `/spec/${b.key}`, search: location.search }}>打开{b.label}</Link>
                    </Button>
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </TabsContent>

      <TabsContent value="styles">
        <div role="radiogroup" aria-label="看板风格" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {DASH_STYLES.map((s: DashStyle) => {
            const m = DASH_STYLE_META[s];
            const active: boolean = s === style;
            return (
              <div key={s} className={cn('dash-panel flex flex-col gap-3 p-3', active && 'ring-2 ring-primary')}>
                <StylePreview style={s} />
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{m.label}</span>
                  <Badge variant="outline">{TONE_LABEL[m.tone]}</Badge>
                </div>
                <p className="dash-subtle text-sm">{m.description}</p>
                <p className="text-xs">适合：{m.bestFor}</p>
                <Button
                  variant={active ? 'default' : 'secondary'}
                  size="sm"
                  role="radio"
                  aria-checked={active}
                  onClick={() => setStyle(s)}
                  className="self-start"
                >
                  {active ? <Check className="size-4" /> : null}
                  {active ? '正在使用' : `使用${m.label}`}
                </Button>
              </div>
            );
          })}
        </div>
      </TabsContent>

      <TabsContent value="layouts">
        <p className="dash-subtle mb-3 text-sm">排版作用于模板看板；每个看板右上角也能单独切换。</p>
        <div role="radiogroup" aria-label="默认排版" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {LAYOUTS.map((k: LayoutKey) => {
            const m = LAYOUT_META[k];
            const active: boolean = defaultLayout === k;
            return (
              <div key={k} className={cn('dash-panel flex flex-col gap-3 p-4', active && 'ring-2 ring-primary')}>
                <Sketch cells={m.sketch} active={active} className="h-24 w-full" />
                <span className="font-medium">{m.label}</span>
                <p className="dash-subtle flex-1 text-sm">{m.description}</p>
                <Button
                  variant={active ? 'default' : 'secondary'}
                  size="sm"
                  role="radio"
                  aria-checked={active}
                  onClick={() => chooseLayout(k)}
                  className="self-start"
                >
                  {active ? <Check className="size-4" /> : null}
                  {active ? '已设为默认' : '设为默认排版'}
                </Button>
              </div>
            );
          })}
        </div>
      </TabsContent>
    </Tabs>
  );
};

export default TemplateCenter;
