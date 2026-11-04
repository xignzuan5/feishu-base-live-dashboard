import React from 'react';

import { cn } from '@/lib/utils';

interface PanelProps {
  title: string;
  subtitle?: string;
  /** 标题右侧：图表类型切换、说明等 */
  actions?: React.ReactNode;
  className?: string;
  bodyClassName?: string;
  children: React.ReactNode;
}

/** 所有看板面板的统一外壳；外观由 html[data-dash-style] 决定 */
export const Panel: React.FC<PanelProps> = ({ title, subtitle, actions, className, bodyClassName, children }) => (
  <section className={cn('dash-panel flex min-w-0 flex-col p-4', className)} aria-label={title}>
    <header className="mb-3 flex flex-wrap items-start justify-between gap-2">
      <div className="min-w-0">
        <h2 className="dash-panel-title truncate text-sm">{title}</h2>
        {subtitle ? <p className="dash-subtle mt-0.5 truncate text-xs">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </header>
    <div className={cn('flex min-h-0 flex-1 flex-col', bodyClassName)}>{children}</div>
  </section>
);

interface PanelStateProps {
  height?: number;
  message?: string;
}

export const PanelEmpty: React.FC<PanelStateProps> = ({ height = 200, message = '当前筛选下暂无数据' }) => (
  <div className="dash-subtle flex items-center justify-center text-sm" style={{ height }}>
    {message}
  </div>
);
