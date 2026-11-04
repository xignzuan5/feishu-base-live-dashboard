/**
 * 看板短缓存 + 同请求合并。
 *
 * 为什么需要：看板每 5 秒轮询一次，每次要并发跑 ~10 条聚合查询。大屏常开、多人同时看时，
 * 线上数据库很小的连接上限会被打满（实测报 `remaining connection slots are reserved`，
 * 连发布时的「数据库更新」都会失败）。
 *
 * 做法：同一个看板 + 同一组筛选，在 TTL 内只算一次；正在算的请求直接复用同一个 Promise。
 * TTL 小于前端轮询间隔，所以看到的数据最多晚 3 秒，不影响「实时」体验。
 */
export class LiveCache {
  private readonly store = new Map<string, { at: number; value: Promise<unknown> }>();

  constructor(private readonly ttlMs: number = 3000, private readonly maxEntries: number = 200) {}

  get<T>(key: string, compute: () => Promise<T>): Promise<T> {
    const now: number = Date.now();
    const hit = this.store.get(key);
    if (hit && now - hit.at < this.ttlMs) return hit.value as Promise<T>;
    const value: Promise<T> = compute().catch((e: unknown) => {
      // 失败不缓存，下一次请求重新计算
      this.store.delete(key);
      throw e;
    });
    this.store.set(key, { at: now, value });
    if (this.store.size > this.maxEntries) {
      const oldest: string | undefined = this.store.keys().next().value;
      if (oldest !== undefined) this.store.delete(oldest);
    }
    return value;
  }
}
