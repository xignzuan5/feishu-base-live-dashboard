import { Controller, Get, Logger, Param, Query } from '@nestjs/common';

import type { SpecBoardData, SpecBoardsMeta } from '@shared/spec-board.interface';

import { DashboardQueryDto } from '../dashboard/dashboard.dto';
import { LiveCache } from '../dashboard/live-cache';
import { guard } from '../dashboard/safe-error';
import { SpecBoardService } from './blueprint.service';

/** 配置驱动看板：静态路由 meta 必须在 :key 之前 */
@Controller('api/spec-board')
export class SpecBoardController {
  /** 3 秒短缓存 + 同请求合并（见 live-cache.ts） */
  private readonly cache = new LiveCache(3000);
  private readonly logger = new Logger(SpecBoardController.name);

  constructor(private readonly service: SpecBoardService) {}

  @Get('meta')
  meta(): SpecBoardsMeta {
    return this.service.meta();  // 纯内存配置，不会触发数据库错误
  }

  @Get('board/:key')
  board(@Param('key') key: string, @Query() q: DashboardQueryDto): Promise<SpecBoardData> {
    return guard(this.logger, `配置看板 ${key}`, () =>
      this.cache.get(`${key}|${q.range ?? ''}`, () => this.service.boardData(key, q.range)),
    );
  }
}
