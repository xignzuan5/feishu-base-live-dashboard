import { Controller, Get, Param, Query } from '@nestjs/common';

import type { SpecBoardData, SpecBoardsMeta } from '@shared/spec-board.interface';

import { DashboardQueryDto } from '../dashboard/dashboard.dto';
import { SpecBoardService } from './blueprint.service';

/** 配置驱动看板：静态路由 meta 必须在 :key 之前 */
@Controller('api/spec-board')
export class SpecBoardController {
  constructor(private readonly service: SpecBoardService) {}

  @Get('meta')
  meta(): SpecBoardsMeta {
    return this.service.meta();
  }

  @Get('board/:key')
  board(@Param('key') key: string, @Query() q: DashboardQueryDto): Promise<SpecBoardData> {
    return this.service.boardData(key, q.range);
  }
}
