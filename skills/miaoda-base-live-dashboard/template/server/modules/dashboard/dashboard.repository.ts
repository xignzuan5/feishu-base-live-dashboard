import { Inject, Injectable } from '@nestjs/common';
import { DRIZZLE_DATABASE, type PostgresJsDatabase } from '@lark-apaas/fullstack-nestjs-core';
import { and, desc, eq, gte, inArray, lt, sql, type AnyColumn, type SQL } from 'drizzle-orm';

import {
  campaigns,
  members,
  orderItems,
  orders,
  products,
  stores,
} from '@server/database/schema';

import { DASHBOARD_CONFIG } from './dashboard.config';

/**
 * 查询层：只依赖 schema.ts 的表对象 + drizzle 的 sql 片段。
 *
 * 多维表格「关联」字段同步到 PG 后是 jsonb：{"link_record_ids": ["rec..."]}，
 * 关联条件统一写成 `<link>->'link_record_ids'->>0 = <目标表>.base_record_id`。
 */
const TZ: string = DASHBOARD_CONFIG.timezone;
if (!/^[A-Za-z_]+\/[A-Za-z_]+$/u.test(TZ)) throw new Error(`非法时区配置：${TZ}`);
/**
 * 时区必须内联成 SQL 字面量：若作为参数传入，SELECT 与 GROUP BY 里会变成 $1 / $11 两个不同参数，
 * PostgreSQL 判定为不同表达式而报 42803（column must appear in the GROUP BY clause）。
 * TZ 只来自配置且已做白名单校验，内联是安全的。
 */
const TZ_SQL: SQL = sql.raw(`'${TZ}'`);
const INVALID: string[] = [...DASHBOARD_CONFIG.invalidStatuses];

export const linkId = (col: AnyColumn | SQL): SQL => sql`(${col}->'link_record_ids'->>0)`;

const STORE_JOIN: SQL = sql`${linkId(orders.store)} = ${stores.baseRecordId}`;
const ITEM_ORDER_JOIN: SQL = sql`${linkId(orderItems.orderRef)} = ${orders.baseRecordId}`;
const ITEM_PRODUCT_JOIN: SQL = sql`${linkId(orderItems.product)} = ${products.baseRecordId}`;
const CAMPAIGN_JOIN: SQL = sql`${linkId(orders.campaign)} = ${campaigns.baseRecordId}`;
const VALID: SQL = sql`${orders.status} NOT IN (${sql.join(
  INVALID.map((s: string) => sql`${s}`),
  sql`, `,
)})`;
/** 非会员订单的关联字段是 {"link_record_ids": null}（JSON null），不能用 jsonb_array_length */
const HAS_MEMBER: SQL = sql`(${orders.member}->'link_record_ids'->>0) IS NOT NULL`;
const LOCAL_TS: SQL = sql`(${orders.orderedAt} AT TIME ZONE ${TZ_SQL})`;

export const num = (v: unknown): number => {
  if (v === null || v === undefined) return 0;
  const n: number = Number(v);
  return Number.isFinite(n) ? n : 0;
};

export interface Scope {
  start: Date;
  end: Date;
  city?: string;
}

export interface Summary {
  revenue: number;
  orders: number;
  allOrders: number;
  cups: number;
  memberOrders: number;
  refunds: number;
  discount: number;
  ratingAvg: number;
  newCustomers: number;
}

export interface DimRow {
  name: string;
  revenue: number;
  orders: number;
}

export interface BucketRow {
  bucket: string;
  revenue: number;
  orders: number;
}

export interface StoreAggRow {
  id: string;
  name: string;
  city: string;
  region: string;
  storeType: string;
  status: string;
  dailyTarget: number;
  ratingScore: number;
  revenue: number;
  orders: number;
}

export interface ProductAggRow {
  name: string;
  category: string;
  price: number;
  cost: number;
  isNew: boolean;
  qty: number;
  revenue: number;
}

export interface FeedRow {
  id: string;
  orderNo: string;
  orderedAt: Date | null;
  store: string;
  city: string;
  channel: string;
  amount: number;
  status: string;
  isMember: boolean;
}

@Injectable()
export class DashboardRepository {
  constructor(@Inject(DRIZZLE_DATABASE) private readonly db: PostgresJsDatabase) {}

  private orderScope(scope: Scope): SQL[] {
    const conds: SQL[] = [gte(orders.orderedAt, scope.start), lt(orders.orderedAt, scope.end)];
    if (scope.city) conds.push(eq(stores.city, scope.city));
    return conds;
  }

  async summary(scope: Scope): Promise<Summary> {
    const rows = await this.db
      .select({
        revenue: sql<string>`COALESCE(SUM(${orders.paidAmount}) FILTER (WHERE ${VALID}), 0)`,
        orders: sql<string>`COUNT(*) FILTER (WHERE ${VALID})`,
        allOrders: sql<string>`COUNT(*)`,
        cups: sql<string>`COALESCE(SUM(${orders.cups}) FILTER (WHERE ${VALID}), 0)`,
        memberOrders: sql<string>`COUNT(*) FILTER (WHERE ${VALID} AND ${HAS_MEMBER})`,
        refunds: sql<string>`COUNT(*) FILTER (WHERE ${orders.status} = '已退款')`,
        discount: sql<string>`COALESCE(SUM(${orders.discount}) FILTER (WHERE ${VALID}), 0)`,
        ratingAvg: sql<string>`COALESCE(AVG(${orders.rating}), 0)`,
        newCustomers: sql<string>`COUNT(*) FILTER (WHERE ${VALID} AND ${orders.isNewCustomer})`,
      })
      .from(orders)
      .leftJoin(stores, STORE_JOIN)
      .where(and(...this.orderScope(scope)));
    const r = rows[0];
    return {
      revenue: num(r?.revenue),
      orders: num(r?.orders),
      allOrders: num(r?.allOrders),
      cups: num(r?.cups),
      memberOrders: num(r?.memberOrders),
      refunds: num(r?.refunds),
      discount: num(r?.discount),
      ratingAvg: num(r?.ratingAvg),
      newCustomers: num(r?.newCustomers),
    };
  }

  /** 按小时 / 按日分桶的营收与订单 */
  async buckets(scope: Scope, granularity: 'hour' | 'day', memberOnly?: boolean): Promise<BucketRow[]> {
    const bucket: SQL<string> =
      granularity === 'hour'
        ? sql<string>`to_char(${LOCAL_TS}, 'HH24')`
        : sql<string>`to_char(${LOCAL_TS}, 'YYYY-MM-DD')`;
    const conds: SQL[] = [...this.orderScope(scope), VALID];
    if (memberOnly === true) conds.push(HAS_MEMBER);
    if (memberOnly === false) conds.push(sql`NOT (${HAS_MEMBER})`);
    const rows = await this.db
      .select({
        bucket,
        revenue: sql<string>`COALESCE(SUM(${orders.paidAmount}), 0)`,
        orders: sql<string>`COUNT(*)`,
      })
      .from(orders)
      .leftJoin(stores, STORE_JOIN)
      .where(and(...conds))
      .groupBy(bucket);
    return rows.map((r) => ({ bucket: String(r.bucket), revenue: num(r.revenue), orders: num(r.orders) }));
  }

  /** 按订单上的某个维度（渠道 / 支付 / 城市 / 门店类型…）聚合 */
  async byDimension(scope: Scope, dim: SQL<string>): Promise<DimRow[]> {
    const rows = await this.db
      .select({
        name: dim,
        revenue: sql<string>`COALESCE(SUM(${orders.paidAmount}), 0)`,
        orders: sql<string>`COUNT(*)`,
      })
      .from(orders)
      .leftJoin(stores, STORE_JOIN)
      .where(and(...this.orderScope(scope), VALID))
      .groupBy(dim)
      .orderBy(desc(sql`2`));
    return rows.map((r) => ({ name: String(r.name ?? '未知'), revenue: num(r.revenue), orders: num(r.orders) }));
  }

  dims = {
    channel: sql<string>`COALESCE(${orders.channel}, '未知')`,
    payMethod: sql<string>`COALESCE(${orders.payMethod}, '未知')`,
    city: sql<string>`COALESCE(${stores.city}, '未知')`,
    region: sql<string>`COALESCE(${stores.region}, '未知')`,
    storeType: sql<string>`COALESCE(${stores.storeType}, '未知')`,
    rating: sql<string>`${orders.rating}::text`,
  };

  /** 星期 × 小时 订单量 */
  async weekHourMatrix(scope: Scope): Promise<{ dow: number; hour: number; orders: number }[]> {
    const dow: SQL<string> = sql<string>`EXTRACT(ISODOW FROM ${LOCAL_TS})::int`;
    const hour: SQL<string> = sql<string>`EXTRACT(HOUR FROM ${LOCAL_TS})::int`;
    const rows = await this.db
      .select({ dow, hour, orders: sql<string>`COUNT(*)` })
      .from(orders)
      .leftJoin(stores, STORE_JOIN)
      .where(and(...this.orderScope(scope), VALID))
      .groupBy(dow, hour);
    return rows.map((r) => ({ dow: num(r.dow), hour: num(r.hour), orders: num(r.orders) }));
  }

  /** 门店维度聚合；无订单的门店也保留（left join） */
  async storeAgg(scope: Scope): Promise<StoreAggRow[]> {
    const joinCond: SQL = and(
      STORE_JOIN,
      gte(orders.orderedAt, scope.start),
      lt(orders.orderedAt, scope.end),
      VALID,
    ) as SQL;
    const rows = await this.db
      .select({
        id: stores.baseRecordId,
        name: stores.storeName,
        city: stores.city,
        region: stores.region,
        storeType: stores.storeType,
        status: stores.status,
        dailyTarget: stores.dailyTarget,
        ratingScore: stores.ratingScore,
        revenue: sql<string>`COALESCE(SUM(${orders.paidAmount}), 0)`,
        orders: sql<string>`COUNT(${orders.id})`,
      })
      .from(stores)
      .leftJoin(orders, joinCond)
      .where(scope.city ? eq(stores.city, scope.city) : undefined)
      .groupBy(
        stores.baseRecordId,
        stores.storeName,
        stores.city,
        stores.region,
        stores.storeType,
        stores.status,
        stores.dailyTarget,
        stores.ratingScore,
      );
    return rows.map((r) => ({
      id: String(r.id ?? ''),
      name: String(r.name ?? ''),
      city: String(r.city ?? ''),
      region: String(r.region ?? ''),
      storeType: String(r.storeType ?? ''),
      status: String(r.status ?? ''),
      dailyTarget: num(r.dailyTarget),
      ratingScore: num(r.ratingScore),
      revenue: num(r.revenue),
      orders: num(r.orders),
    }));
  }

  /** 指定门店的分桶营收 */
  async storeBuckets(
    scope: Scope,
    granularity: 'hour' | 'day',
    storeIds: string[],
  ): Promise<{ storeId: string; bucket: string; revenue: number }[]> {
    if (storeIds.length === 0) return [];
    const bucket: SQL<string> =
      granularity === 'hour'
        ? sql<string>`to_char(${LOCAL_TS}, 'HH24')`
        : sql<string>`to_char(${LOCAL_TS}, 'YYYY-MM-DD')`;
    const sid: SQL = linkId(orders.store);
    const rows = await this.db
      .select({ storeId: sql<string>`${sid}`, bucket, revenue: sql<string>`COALESCE(SUM(${orders.paidAmount}), 0)` })
      .from(orders)
      .where(and(gte(orders.orderedAt, scope.start), lt(orders.orderedAt, scope.end), VALID, inArray(sid, storeIds)))
      .groupBy(sid, bucket);
    return rows.map((r) => ({ storeId: String(r.storeId), bucket: String(r.bucket), revenue: num(r.revenue) }));
  }

  /** 商品维度聚合（订单明细 → 订单 → 门店 / 商品） */
  async productAgg(scope: Scope): Promise<ProductAggRow[]> {
    const rows = await this.db
      .select({
        name: products.productName,
        category: products.category,
        price: products.price,
        cost: products.cost,
        isNew: products.isNew,
        qty: sql<string>`COALESCE(SUM(${orderItems.qty}), 0)`,
        revenue: sql<string>`COALESCE(SUM(${orderItems.qty} * ${orderItems.unitPrice}), 0)`,
      })
      .from(orderItems)
      .innerJoin(orders, ITEM_ORDER_JOIN)
      .innerJoin(products, ITEM_PRODUCT_JOIN)
      .leftJoin(stores, STORE_JOIN)
      .where(and(...this.orderScope(scope), VALID))
      .groupBy(products.productName, products.category, products.price, products.cost, products.isNew);
    return rows.map((r) => ({
      name: String(r.name ?? ''),
      category: String(r.category ?? ''),
      price: num(r.price),
      cost: num(r.cost),
      isNew: Boolean(r.isNew),
      qty: num(r.qty),
      revenue: num(r.revenue),
    }));
  }

  /** 明细按两个维度交叉计数（如 品类 × 温度、小时 × 品类） */
  async itemCross(scope: Scope, dimA: SQL<string>, dimB: SQL<string>): Promise<{ a: string; b: string; qty: number }[]> {
    const rows = await this.db
      .select({ a: dimA, b: dimB, qty: sql<string>`COALESCE(SUM(${orderItems.qty}), 0)` })
      .from(orderItems)
      .innerJoin(orders, ITEM_ORDER_JOIN)
      .innerJoin(products, ITEM_PRODUCT_JOIN)
      .leftJoin(stores, STORE_JOIN)
      .where(and(...this.orderScope(scope), VALID))
      .groupBy(dimA, dimB);
    return rows.map((r) => ({ a: String(r.a ?? '未知'), b: String(r.b ?? '未知'), qty: num(r.qty) }));
  }

  itemDims = {
    category: sql<string>`COALESCE(${products.category}, '未知')`,
    temperature: sql<string>`COALESCE(${orderItems.temperature}, '未知')`,
    hour: sql<string>`to_char(${LOCAL_TS}, 'HH24')`,
  };

  /** 窗口内下过单的会员按等级计数 + 全部会员按等级计数 */
  async memberLevels(scope: Scope): Promise<{ level: string; total: number; active: number }[]> {
    const totals = await this.db
      .select({ level: members.level, total: sql<string>`COUNT(*)` })
      .from(members)
      .groupBy(members.level);
    const active = await this.db
      .select({ level: members.level, active: sql<string>`COUNT(DISTINCT ${members.baseRecordId})` })
      .from(orders)
      .innerJoin(members, sql`${linkId(orders.member)} = ${members.baseRecordId}`)
      .leftJoin(stores, STORE_JOIN)
      .where(and(...this.orderScope(scope), VALID))
      .groupBy(members.level);
    const activeMap = new Map<string, number>(active.map((r) => [String(r.level), num(r.active)]));
    return totals.map((r) => ({
      level: String(r.level ?? '未知'),
      total: num(r.total),
      active: activeMap.get(String(r.level)) ?? 0,
    }));
  }

  async memberAgeGender(): Promise<{ age: string; gender: string; total: number }[]> {
    const rows = await this.db
      .select({ age: members.ageGroup, gender: members.gender, total: sql<string>`COUNT(*)` })
      .from(members)
      .groupBy(members.ageGroup, members.gender);
    return rows.map((r) => ({ age: String(r.age ?? '未知'), gender: String(r.gender ?? '未知'), total: num(r.total) }));
  }

  async activeMemberCount(scope: Scope): Promise<number> {
    const rows = await this.db
      .select({ n: sql<string>`COUNT(DISTINCT ${linkId(orders.member)})` })
      .from(orders)
      .leftJoin(stores, STORE_JOIN)
      .where(and(...this.orderScope(scope), VALID, HAS_MEMBER));
    return num(rows[0]?.n);
  }

  async newMemberCount(start: Date, end: Date): Promise<number> {
    const rows = await this.db
      .select({ n: sql<string>`COUNT(*)` })
      .from(members)
      .where(
        and(
          sql`${members.registeredOn} >= (${start.toISOString()}::timestamptz AT TIME ZONE ${TZ_SQL})::date`,
          sql`${members.registeredOn} <= (${end.toISOString()}::timestamptz AT TIME ZONE ${TZ_SQL})::date`,
        ),
      );
    return num(rows[0]?.n);
  }

  async campaignAgg(city?: string): Promise<
    { name: string; type: string; status: string; budget: number; orders: number; revenue: number; discount: number }[]
  > {
    const rows = await this.db
      .select({
        name: campaigns.campaignName,
        type: campaigns.campaignType,
        status: campaigns.status,
        budget: campaigns.budget,
        orders: sql<string>`COUNT(${orders.id}) FILTER (WHERE ${VALID})`,
        revenue: sql<string>`COALESCE(SUM(${orders.paidAmount}) FILTER (WHERE ${VALID}), 0)`,
        discount: sql<string>`COALESCE(SUM(${orders.discount}) FILTER (WHERE ${VALID}), 0)`,
      })
      .from(campaigns)
      .leftJoin(orders, CAMPAIGN_JOIN)
      .leftJoin(stores, STORE_JOIN)
      .where(city ? eq(stores.city, city) : undefined)
      .groupBy(campaigns.campaignName, campaigns.campaignType, campaigns.status, campaigns.budget, campaigns.startDate)
      .orderBy(desc(campaigns.startDate));
    return rows.map((r) => ({
      name: String(r.name ?? ''),
      type: String(r.type ?? ''),
      status: String(r.status ?? ''),
      budget: num(r.budget),
      orders: num(r.orders),
      revenue: num(r.revenue),
      discount: num(r.discount),
    }));
  }

  /** 最新订单流 */
  async latestOrders(limit: number, city?: string): Promise<FeedRow[]> {
    const rows = await this.db
      .select({
        id: orders.baseRecordId,
        orderNo: orders.orderNo,
        orderedAt: orders.orderedAt,
        store: stores.storeName,
        city: stores.city,
        channel: orders.channel,
        amount: orders.paidAmount,
        status: orders.status,
        isMember: sql<boolean>`${HAS_MEMBER}`,
      })
      .from(orders)
      .leftJoin(stores, STORE_JOIN)
      .where(city ? eq(stores.city, city) : undefined)
      .orderBy(desc(orders.orderedAt), desc(orders.orderNo))
      .limit(limit);
    return rows.map((r) => ({
      id: String(r.id ?? r.orderNo ?? ''),
      orderNo: String(r.orderNo ?? ''),
      orderedAt: r.orderedAt ?? null,
      store: String(r.store ?? '未知门店'),
      city: String(r.city ?? ''),
      channel: String(r.channel ?? ''),
      amount: num(r.amount),
      status: String(r.status ?? ''),
      isMember: Boolean(r.isMember),
    }));
  }

  /** 订单 → 商品摘要（「拿铁×2、可颂」） */
  async orderSummaries(orderIds: string[]): Promise<Map<string, string>> {
    const result = new Map<string, string>();
    if (orderIds.length === 0) return result;
    const oid: SQL = linkId(orderItems.orderRef);
    const rows = await this.db
      .select({ orderId: sql<string>`${oid}`, name: products.productName, qty: orderItems.qty })
      .from(orderItems)
      .innerJoin(products, ITEM_PRODUCT_JOIN)
      .where(inArray(oid, orderIds));
    for (const r of rows) {
      const key: string = String(r.orderId);
      const part: string = `${String(r.name ?? '')}${num(r.qty) > 1 ? `×${num(r.qty)}` : ''}`;
      result.set(key, result.has(key) ? `${result.get(key)}、${part}` : part);
    }
    return result;
  }

  /** 最近 N 分钟的下单时间（用于大屏分钟级柱图） */
  async recentOrderTimes(since: Date, city?: string): Promise<Date[]> {
    const conds: SQL[] = [gte(orders.orderedAt, since), VALID];
    if (city) conds.push(eq(stores.city, city));
    const rows = await this.db
      .select({ t: orders.orderedAt })
      .from(orders)
      .leftJoin(stores, STORE_JOIN)
      .where(and(...conds));
    return rows.map((r) => r.t).filter((t): t is Date => t instanceof Date);
  }

  /**
   * 近 28 天里「每天截至当前时刻」的营收占全天营收的比例。
   * 用于把日目标折算成「截至此刻应完成」的目标（早高峰门店上午就能完成一大半）。
   */
  async timeOfDayShare(nowTime: string, city?: string): Promise<number | null> {
    const since: Date = new Date(Date.now() - 28 * 24 * 3600 * 1000);
    const todayStart: Date = new Date(Date.now() - 24 * 3600 * 1000);
    const conds: SQL[] = [gte(orders.orderedAt, since), lt(orders.orderedAt, todayStart), VALID];
    if (city) conds.push(eq(stores.city, city));
    const rows = await this.db
      .select({
        part: sql<string>`COALESCE(SUM(${orders.paidAmount}) FILTER (WHERE ${LOCAL_TS}::time <= ${nowTime}::time), 0)`,
        total: sql<string>`COALESCE(SUM(${orders.paidAmount}), 0)`,
      })
      .from(orders)
      .leftJoin(stores, STORE_JOIN)
      .where(and(...conds));
    const total: number = num(rows[0]?.total);
    return total > 0 ? num(rows[0]?.part) / total : null;
  }

  async syncStatus(): Promise<{ lastRecordAt: Date | null; lastSyncedAt: Date | null; total: number }> {
    const rows = await this.db
      .select({
        lastRecordAt: sql<string | null>`MAX(${orders.orderedAt})`,
        lastSyncedAt: sql<string | null>`MAX(${orders.updatedAt})`,
        total: sql<string>`COUNT(*)`,
      })
      .from(orders);
    const r = rows[0];
    return {
      lastRecordAt: r?.lastRecordAt ? new Date(r.lastRecordAt) : null,
      lastSyncedAt: r?.lastSyncedAt ? new Date(r.lastSyncedAt) : null,
      total: num(r?.total),
    };
  }

  async cities(): Promise<string[]> {
    const rows = await this.db
      .selectDistinct({ city: stores.city })
      .from(stores)
      .orderBy(stores.city);
    return rows.map((r) => String(r.city ?? '')).filter((c: string) => c.length > 0);
  }
}
