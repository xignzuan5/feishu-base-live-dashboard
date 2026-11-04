import { Coffee, LayoutDashboard, MonitorPlay, Store, Users, type LucideIcon } from 'lucide-react';

import type { DashRange } from '@shared/dashboard.interface';

/**
 * 看板类型注册表：导航、默认时间范围、说明都从这里来。
 * 新增一种看板 = 这里加一项 + pages 下加一个页面 + app.tsx 加一条路由。
 */
export interface BoardMeta {
  key: string;
  path: string;
  label: string;
  description: string;
  icon: LucideIcon;
  defaultRange: DashRange;
  /** 独立全屏页（不套页头），如投屏大屏 */
  standalone?: boolean;
}

export const BOARDS: BoardMeta[] = [
  {
    key: 'overview',
    path: '/',
    label: '经营总览',
    description: '营收、订单、渠道、品类与时段，一屏看全局',
    icon: LayoutDashboard,
    defaultRange: 'today',
  },
  {
    key: 'stores',
    path: '/stores',
    label: '门店作战',
    description: '门店排行、目标达成、大区与店型对比',
    icon: Store,
    defaultRange: 'today',
  },
  {
    key: 'products',
    path: '/products',
    label: '商品分析',
    description: '爆品、品类结构、价格与毛利、时段偏好',
    icon: Coffee,
    defaultRange: '7d',
  },
  {
    key: 'members',
    path: '/members',
    label: '会员与营销',
    description: '会员结构、活跃与新客、活动投入产出',
    icon: Users,
    defaultRange: '7d',
  },
  {
    key: 'bigscreen',
    path: '/bigscreen',
    label: '实时大屏',
    description: '投屏模式：今日实时数据 + 订单滚动',
    icon: MonitorPlay,
    defaultRange: 'today',
    standalone: true,
  },
];

export const boardByPath = (pathname: string): BoardMeta => {
  const clean: string = pathname.replace(/\/+$/u, '') || '/';
  return BOARDS.find((b: BoardMeta) => b.path === clean || (b.path !== '/' && clean.endsWith(b.path))) ?? BOARDS[0];
};

export const boardDefaultRange = (key: string): DashRange =>
  BOARDS.find((b: BoardMeta) => b.key === key)?.defaultRange ?? 'today';
