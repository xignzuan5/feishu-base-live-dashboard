import { Controller, Get, Param, Query } from '@nestjs/common';

import type { SpecBoardData, SpecBoardsMeta } from '@shared/spec-board.interface';

import { DashboardQueryDto } from '../dashboard/dashboard.dto';
import { LiveCache } from '../dashboard/live-cache';
import { SpecBoardService } from './blueprint.service';

/** 配置驱动看板：静态路由 meta 必须在 :key 之前 */
@Controller('api/spec-board')
export class SpecBoardController {
  /** 3 秒短缓存 + 同请求合并（见 live-cache.ts） */
  private readonly cache = new LiveCache(3000);

  constructor(private readonly service: SpecBoardService) {}

  @Get('meta')
  meta(): SpecBoardsMeta {
    return this.service.meta();
  }

  @Get('board/:key')
  board(@Param('key') key: string, @Query() q: DashboardQueryDto): Promise<SpecBoardData> {
    return this.cache.get(`${key}|${q.range ?? ''}`, () => this.service.boardData(key, q.range));
  }
}
