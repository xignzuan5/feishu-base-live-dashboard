import { Module } from '@nestjs/common';

import { SpecBoardController } from './blueprint.controller';
import { SpecBoardService } from './blueprint.service';

@Module({
  controllers: [SpecBoardController],
  providers: [SpecBoardService],
})
export class SpecBoardModule {}
