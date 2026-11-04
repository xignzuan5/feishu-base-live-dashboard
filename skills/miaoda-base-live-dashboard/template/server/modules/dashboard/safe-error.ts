import { HttpException, HttpStatus, type Logger } from '@nestjs/common';

/**
 * 看板接口的错误出口：不把内部错误（SQL、表名、堆栈、服务器路径）返回给前端。
 *
 * 平台默认的全局异常过滤器会把未知异常的 stack / cause 原样返回；看板是给业务同学看的，
 * 所以在接口层先兜住：完整错误只写服务端日志，前端只拿到友好文案 + 排查编号（ref），
 * 前端再把 ref 打到浏览器控制台，方便对照服务端日志排查。
 */
export class DashboardUnavailableException extends HttpException {
  constructor(ref: string) {
    super(
      { code: 'DASHBOARD_UNAVAILABLE', message: '看板数据暂时不可用，稍后会自动重试', ref },
      HttpStatus.SERVICE_UNAVAILABLE,
    );
  }
}

/** 短排查编号：日志里搜它就能找到对应的完整错误 */
export const newErrorRef = (): string =>
  `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;

/** 开发 / 预览环境才把错误摘要带给前端控制台；线上只给排查编号 */
export const exposeDetail = (): boolean => process.env.NODE_ENV !== 'production';

/** 包一层：业务异常（HttpException）原样抛出，其余转成 DashboardUnavailableException 并记日志 */
export const guard = async <T>(logger: Logger, label: string, run: () => Promise<T>): Promise<T> => {
  try {
    return await run();
  } catch (e: unknown) {
    if (e instanceof HttpException) throw e;
    const ref: string = newErrorRef();
    logger.error(`[${ref}] ${label} 失败`, e instanceof Error ? e.stack : String(e));
    throw new DashboardUnavailableException(ref);
  }
};
