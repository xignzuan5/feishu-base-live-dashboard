import { Controller, Get, Query } from '@nestjs/common';

import type {
  DashboardMeta,
  LiveBoard,
  MembersBoard,
  OverviewBoard,
  ProductsBoard,
  StoresBoard,
} from '@shared/dashboard.interface';

import { DashboardQueryDto } from './dashboard.dto';
import { DashboardService } from './dashboard.service';
import { LiveCache } from './live-cache';

/**
 * 只读看板接口。前端每 5 秒轮询一次（平台不支持 SSE/WebSocket，用短轮询做实时）。
 */
@Controller('api/dashboard')
export class DashboardController {
  /** 3 秒短缓存 + 同请求合并：多人同时看、大屏常开时保护数据库连接 */
  private readonly cache = new LiveCache(3000);

  constructor(private readonly service: DashboardService) {}

  private key(name: string, q: DashboardQueryDto): string {
    return `${name}|${q.range ?? ''}|${q.city ?? ''}`;
  }

  @Get('meta')
  meta(): Promise<DashboardMeta> {
    return this.cache.get('meta', () => this.service.meta());
  }

  @Get('overview')
  overview(@Query() q: DashboardQueryDto): Promise<OverviewBoard> {
    return this.cache.get(this.key('overview', q), () => this.service.overview(q.range ?? 'today', q.city));
  }

  @Get('stores')
  stores(@Query() q: DashboardQueryDto): Promise<StoresBoard> {
    return this.cache.get(this.key('stores', q), () => this.service.stores(q.range ?? 'today', q.city));
  }

  @Get('products')
  products(@Query() q: DashboardQueryDto): Promise<ProductsBoard> {
    return this.cache.get(this.key('products', q), () => this.service.products(q.range ?? '7d', q.city));
  }

  @Get('members')
  members(@Query() q: DashboardQueryDto): Promise<MembersBoard> {
    return this.cache.get(this.key('members', q), () => this.service.members(q.range ?? '7d', q.city));
  }

  @Get('live')
  live(@Query() q: DashboardQueryDto): Promise<LiveBoard> {
    return this.cache.get(this.key('live', q), () => this.service.live(q.city));
  }
}
