import { axiosForBackend } from '@lark-apaas/client-toolkit/utils/getAxiosForBackend';

import type {
  DashboardMeta,
  DashRange,
  LiveBoard,
  MembersBoard,
  OverviewBoard,
  ProductsBoard,
  StoresBoard,
} from '@shared/dashboard.interface';

const params = (range?: DashRange, city?: string): Record<string, string> => {
  const p: Record<string, string> = {};
  if (range) p.range = range;
  if (city && city !== 'all') p.city = city;
  return p;
};

const get = async <T,>(url: string, query: Record<string, string> = {}): Promise<T> => {
  const res = await axiosForBackend({ url, method: 'GET', params: query });
  return res.data as T;
};

export const fetchMeta = (): Promise<DashboardMeta> => get<DashboardMeta>('/api/dashboard/meta');

export const fetchOverview = (range: DashRange, city: string): Promise<OverviewBoard> =>
  get<OverviewBoard>('/api/dashboard/overview', params(range, city));

export const fetchStores = (range: DashRange, city: string): Promise<StoresBoard> =>
  get<StoresBoard>('/api/dashboard/stores', params(range, city));

export const fetchProducts = (range: DashRange, city: string): Promise<ProductsBoard> =>
  get<ProductsBoard>('/api/dashboard/products', params(range, city));

export const fetchMembers = (range: DashRange, city: string): Promise<MembersBoard> =>
  get<MembersBoard>('/api/dashboard/members', params(range, city));

export const fetchLive = (city: string): Promise<LiveBoard> => get<LiveBoard>('/api/dashboard/live', params(undefined, city));
