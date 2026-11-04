import { axiosForBackend } from '@lark-apaas/client-toolkit/utils/getAxiosForBackend';

import type { DashRange } from '@shared/dashboard.interface';
import type { SpecBoardData, SpecBoardsMeta } from '@shared/spec-board.interface';
import { registerEntityGroups } from '@/dashboard/theme/entities';

export const fetchSpecMeta = async (): Promise<SpecBoardsMeta> => {
  const res = await axiosForBackend({ url: '/api/spec-board/meta', method: 'GET' });
  const meta: SpecBoardsMeta = res.data as SpecBoardsMeta;
  registerEntityGroups(meta.entities ?? []);
  return meta;
};

export const fetchSpecBoard = async (key: string, range?: DashRange): Promise<SpecBoardData> => {
  const res = await axiosForBackend({
    url: `/api/spec-board/board/${encodeURIComponent(key)}`,
    method: 'GET',
    params: range ? { range } : {},
  });
  return res.data as SpecBoardData;
};
