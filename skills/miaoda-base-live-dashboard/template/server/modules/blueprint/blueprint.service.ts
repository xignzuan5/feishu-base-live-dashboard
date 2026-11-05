import { Inject, Injectable, Logger, NotFoundException } from '@nestjs/common';
import { DRIZZLE_DATABASE, type PostgresJsDatabase } from '@lark-apaas/fullstack-nestjs-core';

import type { CategoryItem, DashRange, KpiItem, TrendSeries } from '@shared/dashboard.interface';
import type {
  SpecBoardData,
  SpecBoardMeta,
  SpecBoardsMeta,
  SpecPanelData,
  SpecPanelMeta,
} from '@shared/spec-board.interface';

import { buildWindow, nowInTz, toIso, type TimeWindow } from '../dashboard/dashboard.time';
import { exposeDetail, newErrorRef } from '../dashboard/safe-error';
import { SpecQueryBuilder, SpecQueryError, type QueryWindow } from './blueprint.query';
import { SPEC_BUNDLE } from './spec.generated';
import type { SpecBoardDef, SpecPanelDef, SpecTableMap } from './spec.types';

type Row = Record<string, unknown>;

const num = (v: unknown): number => {
  const n: number = Number(v);
  return Number.isFinite(n) ? n : 0;
};
const round2 = (n: number): number => Math.round(n * 100) / 100;
/** 时间维度标签：'09' → '09:00'，'2026-11-04' → '11-04' */
const label = (v: unknown): string => {
  const s: string = String(v);
  if (/^\d{2}$/u.test(s)) return `${s}:00`;
  if (/^\d{4}-\d{2}-\d{2}$/u.test(s)) return s === nowInTz().format('YYYY-MM-DD') ? '今日' : s.slice(5);
  return s;
};

@Injectable()
export class SpecBoardService {
  private readonly logger = new Logger(SpecBoardService.name);
  private readonly qb = new SpecQueryBuilder(SPEC_BUNDLE);

  constructor(@Inject(DRIZZLE_DATABASE) private readonly db: PostgresJsDatabase) {}

  private board(key: string): SpecBoardDef {
    const b: SpecBoardDef | undefined = SPEC_BUNDLE.boards.find((x: SpecBoardDef) => x.key === key);
    if (!b) throw new NotFoundException(`看板「${key}」不存在`);
    return b;
  }

  meta(): SpecBoardsMeta {
    return {
      title: SPEC_BUNDLE.title,
      entities: SPEC_BUNDLE.entities ?? [],
      boards: SPEC_BUNDLE.boards.map(
        (b: SpecBoardDef): SpecBoardMeta => ({
          key: b.key,
          label: b.label,
          group: b.group,
          layout: b.layout,
          style: b.style,
          description: b.description,
          defaultRange: b.defaultRange,
          hasTimeFilter: b.panels.some((p: SpecPanelDef) => Boolean(p.timeField)),
          panels: b.panels.map(
            (p: SpecPanelDef): SpecPanelMeta => ({
              id: p.id,
              kind: p.kind,
              title: p.title,
              subtitle: p.subtitle,
              layout: p.layout,
              chartTypes: p.chartTypes,
              defaultChart: p.defaultChart,
              format: p.format,
              hasTime: Boolean(p.timeField),
              notes: p.notes,
            }),
          ),
        }),
      ),
    };
  }

  private async run(p: SpecPanelDef, win: QueryWindow | null): Promise<Row[]> {
    const rows = await this.db.execute(this.qb.build(p, win));
    return rows as unknown as Row[];
  }

  private async panel(p: SpecPanelDef, w: TimeWindow): Promise<SpecPanelData> {
    if (p.kind === 'text') return { kind: 'text', text: p.text ?? '' };
    const win: QueryWindow = { start: w.start, end: w.end, granularity: w.granularity };
    if (p.kind === 'table' && p.columns && p.columns.length > 0) {
      const recs = (await this.db.execute(this.qb.buildRecords(p, p.timeField ? win : null))) as unknown as Row[];
      const tm: SpecTableMap | undefined = p.table ? SPEC_BUNDLE.tables[p.table] : undefined;
      return {
        kind: 'table',
        table: {
          columns: p.columns.map((name: string, i: number) => {
            const numeric: boolean = tm?.fields[name]?.type === 'number';
            return { key: `c${i}`, label: name, format: numeric ? 'number' : 'text', align: numeric ? 'right' : 'left' };
          }),
          rows: recs.map((r: Row) => {
            const out: Record<string, string | number | null> = {};
            (p.columns ?? []).forEach((_n: string, i: number) => {
              const v: unknown = r[`c${i}`];
              out[`c${i}`] = v === null || v === undefined ? null : typeof v === 'number' ? v : String(v);
            });
            return out;
          }),
        },
      };
    }
    const rows: Row[] = await this.run(p, p.timeField ? win : null);

    if (p.kind === 'kpi') {
      const pickValue = (r: Row | undefined): number => {
        if (p.compute === 'ratio') {
          const den: number = num(r?.m1);
          return den > 0 ? num(r?.m0) / den : 0;
        }
        return num(r?.m0);
      };
      // 比率的分母为 0（如上期一单都没结）时没有可比的值，不能当成 0% 去算环比
      const comparable = (r: Row | undefined): boolean => p.compute !== 'ratio' || num(r?.m1) > 0;
      const value: number = pickValue(rows[0]);
      let delta: number | null = null;
      if (p.timeField) {
        const prevRows: Row[] = await this.run(p, { start: w.prevStart, end: w.prevEnd, granularity: w.granularity });
        const prev: number = pickValue(prevRows[0]);
        if (!comparable(rows[0]) || !comparable(prevRows[0])) delta = null;
        else if (p.format === 'percent') delta = value - prev;
        else delta = prev > 0 ? (value - prev) / prev : null;
      }
      const kpi: KpiItem = {
        key: p.id,
        label: p.title,
        value: p.format === 'percent' ? Math.round(value * 10000) / 10000 : round2(value),
        format: p.format,
        delta,
        deltaLabel: p.timeField ? w.deltaLabel : '全部数据',
        goodWhen: p.goodWhen ?? 'up',
      };
      return { kind: 'kpi', kpi };
    }

    const measureNames: string[] = p.measures.map((m) => m.label);
    // compute: ratio 也可用于类别 / 多系列：每行取 m0 / m1
    const val = (r: Row, i: number = 0): number => {
      if (p.compute === 'ratio') {
        const den: number = num(r.m1);
        return den > 0 ? num(r.m0) / den : 0;
      }
      return num(r[`m${i}`]);
    };
    // 第二维度的系列顺序：有固定顺序按它，否则按合计降序
    const orderSeries = (names: string[]): string[] => {
      const fixed: string[] | undefined = p.dimensions[1]?.order;
      if (fixed && fixed.length) {
        return [...names].sort(
          (a: string, b: string) =>
            (fixed.indexOf(a) < 0 ? 999 : fixed.indexOf(a)) - (fixed.indexOf(b) < 0 ? 999 : fixed.indexOf(b)),
        );
      }
      const total = (n: string): number => rows.filter((r: Row) => String(r.d1) === n).reduce((a: number, r: Row) => a + val(r), 0);
      return [...names].sort((a: string, b: string) => total(b) - total(a));
    };
    // 两个维度 + limit：按第一维度合计取 Top N
    const topCategories = (cats: string[]): string[] => {
      if (!p.limit || p.dimensions.length < 2) return cats;
      const total = (c: string): number => rows.filter((r: Row) => String(r.d0) === c).reduce((a: number, r: Row) => a + val(r), 0);
      return [...cats].sort((a: string, b: string) => total(b) - total(a)).slice(0, p.limit);
    };
    if (p.kind === 'trend') {
      const series: TrendSeries[] = [];
      if (p.dimensions.length >= 2) {
        const xs: string[] = Array.from(new Set(rows.map((r: Row) => label(r.d0))));
        const groups: string[] = orderSeries(Array.from(new Set(rows.map((r: Row) => String(r.d1)))));
        groups.forEach((g: string) => {
          const m = new Map<string, number>(
            rows.filter((r: Row) => String(r.d1) === g).map((r: Row) => [label(r.d0), val(r)]),
          );
          series.push({ name: g, points: xs.map((x: string) => ({ x, y: round2(m.get(x) ?? 0) })) });
        });
      } else {
        measureNames.forEach((name: string, i: number) => {
          series.push({ name, points: rows.map((r: Row) => ({ x: label(r.d0), y: round2(num(r[`m${i}`])) })) });
        });
      }
      return { kind: 'trend', trend: { granularity: w.granularity, format: p.format, series } };
    }

    if (p.kind === 'category') {
      const items: CategoryItem[] = rows.map((r: Row) => ({
        name: String(r.d0),
        value: p.compute === 'ratio' ? Math.round(val(r) * 10000) / 10000 : round2(val(r)),
      }));
      return { kind: 'category', category: { format: p.format, items } };
    }

    if (p.kind === 'stacked') {
      if (p.dimensions.length >= 2) {
        const cats: string[] = topCategories(Array.from(new Set(rows.map((r: Row) => String(r.d0)))));
        const groups: string[] = orderSeries(Array.from(new Set(rows.map((r: Row) => String(r.d1)))));
        return {
          kind: 'stacked',
          stacked: {
            format: p.format,
            categories: cats,
            series: groups.map((g: string) => ({
              name: g,
              values: cats.map((c: string) => {
                const hit: Row | undefined = rows.find((r: Row) => String(r.d0) === c && String(r.d1) === g);
                return hit ? round2(val(hit)) : 0;
              }),
            })),
          },
        };
      }
      return {
        kind: 'stacked',
        stacked: {
          format: p.format,
          categories: rows.map((r: Row) => String(r.d0)),
          series: measureNames.map((name: string, i: number) => ({
            name,
            values: rows.map((r: Row) => round2(num(r[`m${i}`]))),
          })),
        },
      };
    }

    // table：维度列 + 指标列
    return {
      kind: 'table',
      table: {
        columns: [
          ...p.dimensions.map((d, i: number) => ({ key: `d${i}`, label: d.field, format: 'text' as const })),
          ...p.measures.map((m, i: number) => ({ key: `m${i}`, label: m.label, format: p.format, align: 'right' as const })),
        ],
        rows: rows.map((r: Row) => {
          const out: Record<string, string | number | null> = {};
          Object.keys(r).forEach((k: string) => {
            out[k] = k.startsWith('m') ? round2(num(r[k])) : String(r[k]);
          });
          return out;
        }),
      },
    };
  }

  private async syncStatus(board: SpecBoardDef): Promise<SpecBoardData['sync']> {
    const p: SpecPanelDef | undefined = board.panels.find((x: SpecPanelDef) => x.table);
    const t: SpecTableMap | undefined = p?.table ? SPEC_BUNDLE.tables[p.table] : undefined;
    if (!t) return null;
    const rows = (await this.db.execute(
      this.qb.syncStatusQuery(t.pg),
    )) as unknown as Row[];
    return {
      lastRecordAt: toIso(rows[0]?.last_at as string | null),
      lastSyncedAt: toIso(rows[0]?.last_at as string | null),
      serverTime: new Date().toISOString(),
      totalRecords: num(rows[0]?.total),
    };
  }

  async boardData(key: string, range?: DashRange): Promise<SpecBoardData> {
    const board: SpecBoardDef = this.board(key);
    const w: TimeWindow = buildWindow(range ?? board.defaultRange);
    const entries = await Promise.all(
      board.panels.map(async (p: SpecPanelDef): Promise<[string, SpecPanelData]> => {
        try {
          return [p.id, await this.panel(p, w)];
        } catch (e: unknown) {
          const ref: string = newErrorRef();
          this.logger.error(`[${ref}] 面板 ${board.key}/${p.id} 查询失败`, e instanceof Error ? e.stack : String(e));
          // 配置问题（SpecQueryError）的说明对开发有用，但不展示给最终用户：只在非生产环境随响应带给控制台
          const detail: string | undefined = exposeDetail()
            ? e instanceof SpecQueryError
              ? e.message
              : (e instanceof Error ? e.message : String(e)).slice(0, 300)
            : undefined;
          return [p.id, { kind: 'error', message: '该面板暂时无法显示', ref, detail }];
        }
      }),
    );
    return {
      key,
      panels: Object.fromEntries(entries),
      sync: await this.syncStatus(board),
      generatedAt: new Date().toISOString(),
    };
  }
}
