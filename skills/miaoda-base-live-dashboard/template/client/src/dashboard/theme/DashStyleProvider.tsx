import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import {
  CHART_PALETTES,
  DASH_STYLE_META,
  isDashStyle,
  type ChartPalette,
  type DashStyle,
  type DashStyleMeta,
} from './styles';
import './dashboard.css';

const STORAGE_KEY = 'dash-style';

interface DashStyleContextValue {
  style: DashStyle;
  meta: DashStyleMeta;
  palette: ChartPalette;
  setStyle: (s: DashStyle) => void;
}

const DashStyleContext = createContext<DashStyleContextValue | null>(null);

const readInitialStyle = (fallback: DashStyle): DashStyle => {
  try {
    const fromUrl: string | null = new URLSearchParams(window.location.search).get('style');
    if (fromUrl && isDashStyle(fromUrl)) return fromUrl;
    const saved: string | null = window.localStorage.getItem(STORAGE_KEY);
    if (saved && isDashStyle(saved)) return saved;
  } catch {
    // 隐私模式等场景读不到存储，使用默认风格
  }
  return fallback;
};

interface DashStyleProviderProps {
  defaultStyle?: DashStyle;
  children: React.ReactNode;
}

export const DashStyleProvider: React.FC<DashStyleProviderProps> = ({ defaultStyle = 'espresso', children }) => {
  const [style, setStyleState] = useState<DashStyle>(() => readInitialStyle(defaultStyle));

  useEffect(() => {
    const root: HTMLElement = document.documentElement;
    root.dataset.dashStyle = style;
    root.classList.toggle('dark', DASH_STYLE_META[style].mode === 'dark');
    return () => {
      delete root.dataset.dashStyle;
      root.classList.remove('dark');
    };
  }, [style]);

  const setStyle = useCallback((s: DashStyle) => {
    setStyleState(s);
    try {
      window.localStorage.setItem(STORAGE_KEY, s);
    } catch {
      // 存不下就只在本次会话生效
    }
  }, []);

  const value = useMemo<DashStyleContextValue>(
    () => ({ style, meta: DASH_STYLE_META[style], palette: CHART_PALETTES[style], setStyle }),
    [style, setStyle],
  );

  return <DashStyleContext.Provider value={value}>{children}</DashStyleContext.Provider>;
};

export const useDashStyle = (): DashStyleContextValue => {
  const ctx: DashStyleContextValue | null = useContext(DashStyleContext);
  if (!ctx) throw new Error('useDashStyle 必须在 <DashStyleProvider> 内使用');
  return ctx;
};
