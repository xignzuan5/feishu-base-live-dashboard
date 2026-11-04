import { sql, type SQL } from 'drizzle-orm';

import type { SpecBundle, SpecCondition, SpecFieldMap, SpecPanelDef, SpecTableMap } from './spec.types';

/**
 * 需求说明 → SQL。
 *
 * 平台规范要求「通过 schema 读写、不手写 SQL」；这里的看板是配置驱动的，表名列名来自
 * 构建期生成的 spec.generated.ts（开发者可控，非用户输入），并且只允许引用映射表里登记过的列，
 * 全部用 drizzle 的 sql.identifier / 参数绑定拼装，不存在注入面。
 */

export interface QueryWindow {
  start: Date;
  end: Date;
  /** 时间维度分桶：today 按小时，其余按天 */
  granularity: 'hour' | 'day';
}

export class SpecQueryError extends Error {}

const id = (s: string): SQL => sql`${sql.identifier(s)}`;
const col = (alias: string, c: string): SQL => sql`${id(alias)}.${id(c)}`;
const linkFirst = (alias: string, c: string): SQL => sql`(${col(alias, c)}->'link_record_ids'->>0)`;

const AGG_SQL: Record<string, string> = { SUM: 'SUM', AVERAGE: 'AVG', MAX: 'MAX', MIN: 'MIN' };

export class SpecQueryBuilder {
  private readonly tzSql: SQL;

  constructor(private readonly bundle: SpecBundle) {
    if (!/^[A-Za-z_]+\/[A-Za-z_]+$/u.test(bundle.timezone)) {
      throw new SpecQueryError(`非法时区：${bundle.timezone}`);
    }
    // 时区内联为字面量：作为参数时 SELECT 与 GROUP BY 会变成不同参数，PG 报 42803
    this.tzSql = sql.raw(`'${bundle.timezone}'`);
  }

  private table(name: string | undefined): SpecTableMap {
    const t: SpecTableMap | undefined = name ? this.bundle.tables[name] : undefined;
    if (!t) throw new SpecQueryError(`表「${name ?? ''}」未同步到应用数据库`);
    return t;
  }

  private field(t: SpecTableMap, tableName: string, name: string): SpecFieldMap {
    const f: SpecFieldMap | undefined = t.fields[name];
    if (!f) throw new SpecQueryError(`字段「${tableName}.${name}」未同步（检查同步计划是否排除了它）`);
    return f;
  }

  private numeric(f: SpecFieldMap): SQL {
    if (f.type === 'number') return sql`${col('t', f.col)}::numeric`;
    return sql`NULLIF(${col('t', f.col)}::text, '')::numeric`;
  }

  private localTs(f: SpecFieldMap): SQL {
    return sql`(${col('t', f.col)} AT TIME ZONE ${this.tzSql})`;
  }

  private condition(t: SpecTableMap, tableName: string, c: SpecCondition): SQL {
    const f: SpecFieldMap = this.field(t, tableName, c.field);
    const target: SQL = f.type === 'link' ? linkFirst('t', f.col) : col('t', f.col);
    const raw: unknown = c.value;
    const values: unknown[] = Array.isArray(raw) ? raw : raw === undefined || raw === null ? [] : [raw];
    const exactMs: number | null =
      raw && typeof raw === 'object' && !Array.isArray(raw) && 'exact_date_ms' in raw
        ? Number((raw as { exact_date_ms: number }).exact_date_ms)
        : null;
    const scalar = (v: unknown): SQL => sql`${v as string | number | boolean}`;
    // 字段对字段：{"field": "计划截止"}（同一张表）
    const otherField: string | null =
      raw && typeof raw === 'object' && !Array.isArray(raw) && 'field' in raw ? String((raw as { field: string }).field) : null;
    const list: SQL = sql.join(values.map(scalar), sql`, `);
    const isDate: boolean = f.type === 'datetime' || f.type === 'date';
    const relative: string | null =
      raw && typeof raw === 'object' && !Array.isArray(raw) && 'relative' in raw
        ? String((raw as { relative: string }).relative)
        : null;
    const tsVal: SQL =
      exactMs !== null ? sql`to_timestamp(${exactMs / 1000})` : relative !== null ? this.relativeDate(relative) : sql`NULL`;
    // date 列和时间戳比较会按会话时区（UTC）换算，先把右值换成业务时区的自然日
    const dateVal: SQL = f.type === 'date' ? sql`((${tsVal}) AT TIME ZONE ${this.tzSql})::date` : tsVal;
    if (otherField) {
      const g: SpecFieldMap = this.field(t, tableName, otherField);
      const ops: Record<string, string> = { is: '=', isNot: '<>', isGreater: '>', isGreaterEqual: '>=', isLess: '<', isLessEqual: '<=' };
      const op: string | undefined = ops[c.op];
      if (!op) throw new SpecQueryError(`字段对字段比较不支持操作符：${c.op}`);
      return sql`${col('t', f.col)} ${sql.raw(op)} ${col('t', g.col)}`;
    }
    switch (c.op) {
      case 'is':
        if (exactMs !== null || relative !== null) {
          return sql`(${this.localTs(f)})::date = (${dateVal} AT TIME ZONE ${this.tzSql})::date`;
        }
        if (f.type === 'checkbox') return sql`COALESCE(${target}, false) = ${Boolean(values[0])}`;
        if (f.type === 'multiselect') return sql`${target} @> ARRAY[${list}]::text[]`;
        return values.length > 1 ? sql`${target}::text IN (${list})` : sql`${target}::text = ${scalar(values[0])}`;
      case 'isNot':
        if (f.type === 'multiselect') return sql`NOT (COALESCE(${target}, ARRAY[]::text[]) @> ARRAY[${list}]::text[])`;
        return sql`(${target} IS NULL OR ${target}::text NOT IN (${list}))`;
      case 'contains':
        if (f.type === 'multiselect') return sql`${target} && ARRAY[${list}]::text[]`;
        return sql`${target}::text ILIKE ${`%${String(values[0] ?? '')}%`}`;
      case 'doesNotContain':
        if (f.type === 'multiselect') return sql`NOT (COALESCE(${target}, ARRAY[]::text[]) && ARRAY[${list}]::text[])`;
        return sql`(${target} IS NULL OR ${target}::text NOT ILIKE ${`%${String(values[0] ?? '')}%`})`;
      case 'isEmpty':
        if (f.type === 'multiselect') return sql`COALESCE(cardinality(${target}), 0) = 0`;
        return sql`(${target} IS NULL OR ${target}::text = '')`;
      case 'isNotEmpty':
        if (f.type === 'multiselect') return sql`COALESCE(cardinality(${target}), 0) > 0`;
        return sql`(${target} IS NOT NULL AND ${target}::text <> '')`;
      case 'isGreater':
      case 'isGreaterEqual':
      case 'isLess':
      case 'isLessEqual': {
        const op: SQL = sql.raw({ isGreater: '>', isGreaterEqual: '>=', isLess: '<', isLessEqual: '<=' }[c.op] as string);
        if (isDate) return sql`${col('t', f.col)} ${op} ${dateVal}`;
        return sql`${this.numeric(f)} ${op} ${Number(values[0])}`;
      }
      default:
        throw new SpecQueryError(`不支持的筛选操作符：${c.op}`);
    }
  }

  /** 相对日期：now / today / -7d / +3d（按业务时区的自然日） */
  private relativeDate(rel: string): SQL {
    if (rel === 'now') return sql`now()`;
    const today: SQL = sql`((now() AT TIME ZONE ${this.tzSql})::date::timestamp AT TIME ZONE ${this.tzSql})`;
    if (rel === 'today') return today;
    const m: RegExpMatchArray | null = /^([+-])(\d{1,4})d$/u.exec(rel);
    if (!m) throw new SpecQueryError(`不支持的相对日期：${rel}`);
    const days: number = Number(m[2]) * (m[1] === '-' ? -1 : 1);
    return sql`(${today} + make_interval(days => ${days}))`;
  }

  /**
   * 生成面板查询。返回列：d0、d1（维度，可选）、m0..mN（指标）。
   * 关联维度取对方表主字段（与多维表格仪表盘展示一致）；多选维度按选项拆开统计（enumerated）。
   */
  build(p: SpecPanelDef, win: QueryWindow | null): SQL {
    const tableName: string = p.table ?? '';
    const t: SpecTableMap = this.table(tableName);
    const joins: SQL[] = [];
    const dims: SQL[] = [];
    p.dimensions.forEach((d, i: number) => {
      const f: SpecFieldMap = this.field(t, tableName, d.field);
      if (f.type === 'link') {
        const tgt: SpecTableMap = this.table(f.target);
        const alias = `j${i}`;
        const shown: SpecFieldMap = this.field(tgt, f.target ?? '', d.via ?? tgt.primary);
        joins.push(
          sql`LEFT JOIN ${id(tgt.pg)} AS ${id(alias)} ON ${linkFirst('t', f.col)} = ${col(alias, 'base_record_id')}`,
        );
        dims.push(
          shown.type === 'multiselect'
            ? sql`COALESCE(array_to_string(${col(alias, shown.col)}, '、'), '未关联')`
            : sql`COALESCE(${col(alias, shown.col)}::text, '未关联')`,
        );
      } else if (f.type === 'multiselect') {
        const alias = `u${i}`;
        joins.push(sql`CROSS JOIN LATERAL unnest(COALESCE(${col('t', f.col)}, ARRAY['未填写']::text[])) AS ${id(alias)}(v)`);
        dims.push(sql`${id(alias)}.v`);
      } else if (f.type === 'datetime') {
        const fmt: string = win?.granularity === 'hour' ? 'HH24' : 'YYYY-MM-DD';
        dims.push(sql`to_char(${this.localTs(f)}, ${sql.raw(`'${fmt}'`)})`);
      } else if (f.type === 'date') {
        dims.push(sql`to_char(${col('t', f.col)}, 'YYYY-MM-DD')`);
      } else if (f.type === 'checkbox') {
        dims.push(sql`CASE WHEN ${col('t', f.col)} THEN '是' ELSE '否' END`);
      } else {
        dims.push(sql`COALESCE(${col('t', f.col)}::text, '未填写')`);
      }
    });
    const measures: SQL[] = p.measures.map((m) => {
      const cond: SQL | null =
        m.where && m.where.length > 0
          ? sql.join(m.where.map((c: SpecCondition) => this.condition(t, tableName, c)), sql` AND `)
          : null;
      const filt: SQL = cond ? sql` FILTER (WHERE ${cond})` : sql``;
      if (m.agg === 'COUNT' || !m.field) return sql`COUNT(*)${filt}`;
      const f: SpecFieldMap = this.field(t, tableName, m.field);
      if (m.agg === 'COUNT_DISTINCT') {
        const target: SQL = f.type === 'link' ? linkFirst('t', f.col) : col('t', f.col);
        return sql`COUNT(DISTINCT ${target})${filt}`;
      }
      return sql`COALESCE(${sql.raw(AGG_SQL[m.agg] ?? 'SUM')}(${this.numeric(f)})${filt}, 0)`;
    });
    if (measures.length === 0) measures.push(sql`COUNT(*)`);

    const where: SQL[] = [];
    if (p.filter && p.filter.conditions.length > 0) {
      const parts: SQL[] = p.filter.conditions.map((c: SpecCondition) => this.condition(t, tableName, c));
      where.push(sql`(${sql.join(parts, p.filter.conjunction === 'or' ? sql` OR ` : sql` AND `)})`);
    }
    if (p.timeField && win) {
      const f: SpecFieldMap = this.field(t, tableName, p.timeField);
      if (f.type === 'date') {
        // 日期列按业务时区的自然日比较（含今天）
        where.push(sql`${col('t', f.col)} >= (${win.start.toISOString()}::timestamptz AT TIME ZONE ${this.tzSql})::date`);
        where.push(sql`${col('t', f.col)} <= (${win.end.toISOString()}::timestamptz AT TIME ZONE ${this.tzSql})::date`);
      } else {
        where.push(sql`${col('t', f.col)} >= ${win.start.toISOString()}::timestamptz`);
        where.push(sql`${col('t', f.col)} < ${win.end.toISOString()}::timestamptz`);
      }
    }
    const selects: SQL[] = [
      ...dims.map((d: SQL, i: number) => sql`${d} AS ${id(`d${i}`)}`),
      ...measures.map((m: SQL, i: number) => sql`${m} AS ${id(`m${i}`)}`),
    ];
    const parts: SQL[] = [sql`SELECT ${sql.join(selects, sql`, `)} FROM ${id(t.pg)} AS ${id('t')}`];
    if (joins.length) parts.push(sql.join(joins, sql` `));
    if (where.length) parts.push(sql`WHERE ${sql.join(where, sql` AND `)}`);
    if (dims.length) {
      parts.push(sql`GROUP BY ${sql.join(dims.map((_d: SQL, i: number) => sql.raw(String(i + 1))), sql`, `)}`);
      const isTime: boolean = p.dimensions[0] ? ['datetime', 'date'].includes(t.fields[p.dimensions[0].field]?.type) : false;
      const fixed: string[] | undefined = p.dimensions[0]?.order;
      const byValue: boolean = !isTime && !fixed && (p.sort?.by === 'value' || (!p.sort && p.kind !== 'trend'));
      const dir: SQL = sql.raw((p.sort?.order ?? (byValue ? 'desc' : 'asc')) === 'desc' ? 'DESC' : 'ASC');
      if (fixed && fixed.length > 0) {
        // 固定顺序：array_position 找不到返回 NULL，NULLS LAST 放到最后
        const arr: SQL = sql`ARRAY[${sql.join(fixed.map((v: string) => sql`${v}`), sql`, `)}]::text[]`;
        // ORDER BY 的函数里不能引用输出列别名 "d0"，直接用维度表达式（不含参数，和 GROUP BY 1 等价）
        parts.push(sql`ORDER BY array_position(${arr}, ${dims[0]}) NULLS LAST, ${id('m0')} DESC`);
      } else {
        parts.push(byValue ? sql`ORDER BY ${id('m0')} ${dir}` : sql`ORDER BY 1 ${isTime ? sql.raw('ASC') : dir}`);
      }
      // 两个维度时 Top N 在服务层按第一维度合计截取，这里不截断组合
      if (p.limit && p.limit > 0 && dims.length === 1) parts.push(sql`LIMIT ${Math.min(p.limit, 500)}`);
      else parts.push(sql`LIMIT 2000`);
    }
    return sql.join(parts, sql` `);
  }

  /** 单个字段的展示表达式（记录清单用）：关联显示对方主字段，日期按业务时区格式化 */
  private displayExpr(t: SpecTableMap, tableName: string, name: string, i: number, joins: SQL[]): SQL {
    const f: SpecFieldMap = this.field(t, tableName, name);
    if (f.type === 'link') {
      const tgt: SpecTableMap = this.table(f.target);
      const primary: SpecFieldMap = this.field(tgt, f.target ?? '', tgt.primary);
      const alias = `r${i}`;
      joins.push(sql`LEFT JOIN ${id(tgt.pg)} AS ${id(alias)} ON ${linkFirst('t', f.col)} = ${col(alias, 'base_record_id')}`);
      return sql`${col(alias, primary.col)}::text`;
    }
    if (f.type === 'datetime') return sql`to_char(${this.localTs(f)}, 'YYYY-MM-DD HH24:MI')`;
    if (f.type === 'date') return sql`to_char(${col('t', f.col)}, 'YYYY-MM-DD')`;
    if (f.type === 'multiselect') return sql`array_to_string(${col('t', f.col)}, '、')`;
    if (f.type === 'checkbox') return sql`CASE WHEN ${col('t', f.col)} THEN '是' ELSE '否' END`;
    if (f.type === 'number') return sql`${col('t', f.col)}`;
    return sql`${col('t', f.col)}::text`;
  }

  /** 记录清单：逐条列出指定字段（逾期清单、待跟进客户清单…） */
  buildRecords(p: SpecPanelDef, win: QueryWindow | null): SQL {
    const tableName: string = p.table ?? '';
    const t: SpecTableMap = this.table(tableName);
    const joins: SQL[] = [];
    const cols: SQL[] = (p.columns ?? []).map(
      (name: string, i: number) => sql`${this.displayExpr(t, tableName, name, i, joins)} AS ${id(`c${i}`)}`,
    );
    const where: SQL[] = [];
    if (p.filter && p.filter.conditions.length > 0) {
      const parts: SQL[] = p.filter.conditions.map((c: SpecCondition) => this.condition(t, tableName, c));
      where.push(sql`(${sql.join(parts, p.filter.conjunction === 'or' ? sql` OR ` : sql` AND `)})`);
    }
    if (p.timeField && win) {
      const f: SpecFieldMap = this.field(t, tableName, p.timeField);
      where.push(sql`${col('t', f.col)} >= ${win.start.toISOString()}::timestamptz`);
      where.push(sql`${col('t', f.col)} < ${win.end.toISOString()}::timestamptz`);
    }
    const parts: SQL[] = [sql`SELECT ${sql.join(cols, sql`, `)} FROM ${id(t.pg)} AS ${id('t')}`];
    if (joins.length) parts.push(sql.join(joins, sql` `));
    if (where.length) parts.push(sql`WHERE ${sql.join(where, sql` AND `)}`);
    if (p.sort?.field) {
      const sf: SpecFieldMap = this.field(t, tableName, p.sort.field);
      parts.push(sql`ORDER BY ${col('t', sf.col)} ${sql.raw(p.sort.order === 'desc' ? 'DESC' : 'ASC')} NULLS LAST`);
    }
    parts.push(sql`LIMIT ${Math.min(p.limit ?? 20, 200)}`);
    return sql.join(parts, sql` `);
  }

  /** 同步状态：表里最近一次被同步写入的时间 + 行数 */
  syncStatusQuery(pgTable: string): SQL {
    return sql`SELECT MAX(${id('_updated_at')}) AS last_at, COUNT(*) AS total FROM ${id(pgTable)}`;
  }
}
