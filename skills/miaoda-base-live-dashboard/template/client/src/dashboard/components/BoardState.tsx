import React from 'react';
import { CircleAlert } from 'lucide-react';

import { Skeleton } from '@/components/ui/skeleton';

interface BoardStateProps {
  isLoading: boolean;
  error: unknown;
  hasData: boolean;
  children: React.ReactNode;
}

const errorText = (error: unknown): string => {
  const e = error as { response?: { data?: { error?: { message?: string } } } } | null;
  return e?.response?.data?.error?.message ?? '看板数据加载失败，请稍后重试';
};

/** 首次加载显示骨架；轮询失败但已有旧数据时继续展示旧数据，只在顶部提示 */
export const BoardState: React.FC<BoardStateProps> = ({ isLoading, error, hasData, children }) => {
  if (isLoading && !hasData) {
    return (
      <div className="flex flex-col gap-3" aria-busy="true" aria-label="加载中">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          {Array.from({ length: 6 }, (_v: unknown, i: number) => (
            <Skeleton key={i} className="h-[108px] rounded-xl" />
          ))}
        </div>
        <div className="grid gap-3 xl:grid-cols-12">
          <Skeleton className="h-[340px] rounded-xl xl:col-span-8" />
          <Skeleton className="h-[340px] rounded-xl xl:col-span-4" />
        </div>
      </div>
    );
  }
  if (error && !hasData) {
    return (
      <div className="dash-panel dash-critical flex items-center gap-2 p-6 text-sm" role="alert">
        <CircleAlert className="size-4" aria-hidden />
        {errorText(error)}
      </div>
    );
  }
  return (
    <>
      {error ? (
        <div className="dash-warning mb-3 flex items-center gap-2 text-xs" role="status">
          <CircleAlert className="size-3.5" aria-hidden />
          最近一次刷新失败，正在展示上一次的数据，稍后自动重试
        </div>
      ) : null}
      {children}
    </>
  );
};
