import React, { useEffect } from 'react';
import { CircleAlert } from 'lucide-react';
import { logger } from '@lark-apaas/client-toolkit/logger';

import { Skeleton } from '@/components/ui/skeleton';

interface BoardStateProps {
  isLoading: boolean;
  error: unknown;
  hasData: boolean;
  children: React.ReactNode;
}

interface ApiErrorShape {
  message?: string;
  response?: { status?: number; data?: { error?: { code?: string; message?: string; ref?: string; details?: string } } };
}

/** 界面只用固定的友好文案；接口返回的错误详情（状态码、排查编号）只打到浏览器控制台 */
const FRIENDLY_TEXT = '看板数据暂时加载失败，稍后会自动重试';

const logError = (error: unknown): void => {
  const e = error as ApiErrorShape | null;
  const body = e?.response?.data?.error;
  let ref: string | undefined = body?.ref;
  if (!ref && body?.details) {
    try {
      ref = (JSON.parse(body.details) as { ref?: string }).ref;
    } catch {
      ref = undefined;
    }
  }
  logger.error('[看板] 数据加载失败', { status: e?.response?.status, code: body?.code, ref, message: e?.message });
};

/** 首次加载显示骨架；轮询失败但已有旧数据时继续展示旧数据，只在顶部提示 */
export const BoardState: React.FC<BoardStateProps> = ({ isLoading, error, hasData, children }) => {
  // 轮询失败时 error 对象每次都是新的：按「状态码 + 错误码」去重，同一类失败只记一次
  const e = error as ApiErrorShape | null;
  const errKey: string | undefined = error ? `${e?.response?.status ?? ''}|${e?.response?.data?.error?.code ?? e?.message ?? ''}` : undefined;
  useEffect(() => {
    if (error) logError(error);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [errKey]);
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
        {FRIENDLY_TEXT}
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
