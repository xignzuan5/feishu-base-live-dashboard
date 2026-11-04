import { IsIn, IsOptional, IsString } from 'class-validator';
import { Transform } from 'class-transformer';

import { DASH_RANGES, type DashboardQuery } from '@shared/dashboard.interface';

export class DashboardQueryDto implements DashboardQuery {
  @IsOptional()
  @Transform(({ obj, key, value }) => (obj[key] === '' ? undefined : value))
  @IsString()
  @IsIn(DASH_RANGES)
  range?: 'today' | '7d' | '30d' | '90d';

  @IsOptional()
  @Transform(({ obj, key, value }) => (obj[key] === '' || obj[key] === 'all' ? undefined : value))
  @IsString()
  city?: string;
}
