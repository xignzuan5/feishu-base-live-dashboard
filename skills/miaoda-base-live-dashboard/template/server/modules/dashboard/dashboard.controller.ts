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

/**
 * 只读看板接口。前端每 5 秒轮询一次（平台不支持 SSE/WebSocket，用短轮询做实时）。
 */
@Controller('api/dashboard')
export class DashboardController {
  constructor(private readonly service: DashboardService) {}

  @Get('meta')
  meta(): Promise<DashboardMeta> {
    return this.service.meta();
  }

  @Get('overview')
  overview(@Query() q: DashboardQueryDto): Promise<OverviewBoard> {
    return this.service.overview(q.range ?? 'today', q.city);
  }

  @Get('stores')
  stores(@Query() q: DashboardQueryDto): Promise<StoresBoard> {
    return this.service.stores(q.range ?? 'today', q.city);
  }

  @Get('products')
  products(@Query() q: DashboardQueryDto): Promise<ProductsBoard> {
    return this.service.products(q.range ?? '7d', q.city);
  }

  @Get('members')
  members(@Query() q: DashboardQueryDto): Promise<MembersBoard> {
    return this.service.members(q.range ?? '7d', q.city);
  }

  @Get('live')
  live(@Query() q: DashboardQueryDto): Promise<LiveBoard> {
    return this.service.live(q.city);
  }
}
