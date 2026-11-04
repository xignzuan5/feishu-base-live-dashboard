/**
 * 看板风格（主题）注册表。
 *
 * 每套风格 = 一组 CSS 变量（见 dashboard.css 中 html[data-dash-style=...]）
 *          + 一份图表配色（本文件 CHART_PALETTES）。
 * 图表分类色均经 dataviz validate_palette.js 校验：
 *   - espresso / neon 使用深色参考板（6 色，深底 ALL PASS）
 *   - oat 使用浅色参考板（6 色，ALL PASS；3 色对比度 < 3:1 → 图上必须带直接标签或表格）
 * 新增风格：复制一份 palette + 一段 CSS 变量，跑一遍校验脚本再上线。
 */
export const DASH_STYLES = ['espresso', 'oat', 'neon', 'sky', 'graphite', 'celadon', 'abyss', 'pine'] as const;
export type DashStyle = (typeof DASH_STYLES)[number];
export const isDashStyle = (v: string): v is DashStyle =>
  (DASH_STYLES as readonly string[]).includes(v);

/** 设计调性：决定推荐风格与版式（参考 pbi-report-design 的 design identity） */
export type DesignTone = 'restrained' | 'corporate' | 'editorial' | 'technical';

export interface DashStyleMeta {
  key: DashStyle;
  label: string;
  description: string;
  /** 适用场景（风格画廊展示） */
  bestFor: string;
  tone: DesignTone;
  mode: 'dark' | 'light';
  /** 画廊缩略预览：背景 / 面板 / 文字 / 强调色 / 边框 */
  preview: { bg: string; panel: string; text: string; muted: string; accent: string; border: string };
  /** 风格切换器里的色块预览 */
  swatches: [string, string, string];
}

export const DASH_STYLE_META: Record<DashStyle, DashStyleMeta> = {
  espresso: {
    key: 'espresso',
    label: '深烘焙',
    description: '暖调深色，长时间盯屏不刺眼',
    bestFor: '门店 / 运营值守、夜间看盘',
    tone: 'technical',
    mode: 'dark',
    swatches: ['#14110f', '#e0a458', '#3987e5'],
    preview: { bg: '#14110f', panel: '#1c1815', text: '#f3ece2', muted: '#8f8377', accent: '#e0a458', border: '#2c2520' },
  },
  oat: {
    key: 'oat',
    label: '燕麦白',
    description: '暖白纸感，打印和截图都干净',
    bestFor: '零售 / 餐饮品牌的经营周报',
    tone: 'corporate',
    mode: 'light',
    swatches: ['#f5f1ea', '#8b5a2b', '#2a78d6'],
    preview: { bg: '#f5f1ea', panel: '#fffdf9', text: '#1f1a16', muted: '#8a7f73', accent: '#8b5a2b', border: '#e8dfd2' },
  },
  neon: {
    key: 'neon',
    label: '霓虹大屏',
    description: '深蓝底、青色发光描边，远看也醒目',
    bestFor: '展厅、活动现场、指挥中心大屏',
    tone: 'technical',
    mode: 'dark',
    swatches: ['#060b1a', '#22d3ee', '#9085e9'],
    preview: { bg: '#060b1a', panel: '#0d1836', text: '#e6f1ff', muted: '#6d82a8', accent: '#22d3ee', border: '#1d3566' },
  },
  sky: {
    key: 'sky',
    label: '晴空',
    description: '冷白底、蓝色强调，规整克制',
    bestFor: '销售复盘、项目周会、对上汇报',
    tone: 'corporate',
    mode: 'light',
    swatches: ['#f4f6f9', '#3370ff', '#1f2329'],
    preview: { bg: '#f4f6f9', panel: '#ffffff', text: '#1f2329', muted: '#8f959e', accent: '#3370ff', border: '#e4e7ec' },
  },
  graphite: {
    key: 'graphite',
    label: '墨石',
    description: '中性深灰，只留一个青色强调',
    bestFor: '财务 / 运维监控，信息密度高的场景',
    tone: 'restrained',
    mode: 'dark',
    swatches: ['#121417', '#3fb8af', '#e8eaed'],
    preview: { bg: '#121417', panel: '#1a1d21', text: '#e8eaed', muted: '#80868b', accent: '#3fb8af', border: '#2a2e33' },
  },
  celadon: {
    key: 'celadon',
    label: '青瓷',
    description: '灰绿纸面、衬线标题，安静耐读',
    bestFor: '人力 / 组织盘点、品牌与内容报告',
    tone: 'editorial',
    mode: 'light',
    swatches: ['#eef2ef', '#2f7d6d', '#17201c'],
    preview: { bg: '#eef2ef', panel: '#fbfcfb', text: '#17201c', muted: '#6b7a73', accent: '#2f7d6d', border: '#d9e1dc' },
  },
  abyss: {
    key: 'abyss',
    label: '深海',
    description: '深青底、无发光装饰，大字号沉稳投屏',
    bestFor: '会议室电视、管理层晨会投屏',
    tone: 'restrained',
    mode: 'dark',
    swatches: ['#0a1620', '#4fc3d9', '#f2c14e'],
    preview: { bg: '#0a1620', panel: '#0d1b26', text: '#e3eef3', muted: '#7896a5', accent: '#4fc3d9', border: '#1a3140' },
  },
  pine: {
    key: 'pine',
    label: '松针',
    description: '墨绿底配珊瑚色，稳重而有记忆点',
    bestFor: '高管驾驶舱、经营分析会',
    tone: 'editorial',
    mode: 'dark',
    swatches: ['#0e1814', '#ff8a65', '#e6efe9'],
    preview: { bg: '#0e1814', panel: '#13201b', text: '#e6efe9', muted: '#7f978b', accent: '#ff8a65', border: '#22342c' },
  },
};

export interface ChartPalette {
  /** 分类色：按固定顺序取，禁止循环；超过 6 类折叠为「其他」 */
  categorical: string[];
  /** 单序列（同一指标的量级）用色 */
  single: string;
  /** 单序列的柔和填充（面积图渐变底色） */
  singleSoft: string;
  /** 对比周期（昨日 / 上一周期）用色：弱化灰 */
  compare: string;
  /** 顺序色阶（热力图）：同一色相，由弱到强 */
  sequential: string[];
  /** 状态色：保留色，只用于好/警告/严重，且必须配图标 + 文字 */
  status: { good: string; warning: string; critical: string };
  text: { primary: string; secondary: string; muted: string };
  grid: string;
  axis: string;
  surface: string;
  tooltipBg: string;
  tooltipBorder: string;
  /** 霓虹风格给数据线加发光 */
  glow: number;
}

const DARK_CATEGORICAL: string[] = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300'];
const LIGHT_CATEGORICAL: string[] = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300'];

export const CHART_PALETTES: Record<DashStyle, ChartPalette> = {
  espresso: {
    categorical: DARK_CATEGORICAL,
    single: '#e0a458',
    singleSoft: 'rgba(224, 164, 88, 0.22)',
    compare: '#75695f',
    sequential: ['#2a221c', '#47331f', '#6b4622', '#935d27', '#bb782f', '#df9a45', '#f5c27c'],
    status: { good: '#5cc58a', warning: '#e5b04a', critical: '#f07167' },
    text: { primary: '#f3ece2', secondary: '#c4b8aa', muted: '#8f8377' },
    grid: 'rgba(243, 236, 226, 0.07)',
    axis: 'rgba(243, 236, 226, 0.18)',
    surface: '#1c1815',
    tooltipBg: '#2a2420',
    tooltipBorder: '#3d342d',
    glow: 0,
  },
  oat: {
    categorical: LIGHT_CATEGORICAL,
    single: '#2a78d6',
    singleSoft: 'rgba(42, 120, 214, 0.14)',
    compare: '#b4a999',
    sequential: ['#eef4fc', '#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95'],
    status: { good: '#2f9e5b', warning: '#c27a00', critical: '#d64545' },
    text: { primary: '#1f1a16', secondary: '#5b5148', muted: '#8a7f73' },
    grid: 'rgba(31, 26, 22, 0.07)',
    axis: 'rgba(31, 26, 22, 0.2)',
    surface: '#fffdf9',
    tooltipBg: '#ffffff',
    tooltipBorder: '#e6ddd0',
    glow: 0,
  },
  sky: {
    categorical: LIGHT_CATEGORICAL,
    single: '#3370ff',
    singleSoft: 'rgba(51, 112, 255, 0.12)',
    compare: '#b8bec8',
    sequential: ['#edf3ff', '#cfdfff', '#a6c3ff', '#7aa4ff', '#4d84ff', '#2f63e0', '#1e46a8'],
    status: { good: '#2ea121', warning: '#de7802', critical: '#e22e28' },
    text: { primary: '#1f2329', secondary: '#4e5969', muted: '#8f959e' },
    grid: 'rgba(31, 35, 41, 0.07)',
    axis: 'rgba(31, 35, 41, 0.18)',
    surface: '#ffffff',
    tooltipBg: '#ffffff',
    tooltipBorder: '#e4e7ec',
    glow: 0,
  },
  graphite: {
    categorical: DARK_CATEGORICAL,
    single: '#3fb8af',
    singleSoft: 'rgba(63, 184, 175, 0.16)',
    compare: '#5f6368',
    sequential: ['#1d2427', '#1d3b3a', '#1f524f', '#246a65', '#2c847d', '#3fb8af', '#8fe0d8'],
    status: { good: '#4fc28a', warning: '#e8b04a', critical: '#f07167' },
    text: { primary: '#e8eaed', secondary: '#bdc1c6', muted: '#80868b' },
    grid: 'rgba(232, 234, 237, 0.06)',
    axis: 'rgba(232, 234, 237, 0.16)',
    surface: '#1a1d21',
    tooltipBg: '#24282d',
    tooltipBorder: '#363b41',
    glow: 0,
  },
  celadon: {
    categorical: LIGHT_CATEGORICAL,
    single: '#2f7d6d',
    singleSoft: 'rgba(47, 125, 109, 0.12)',
    compare: '#aab7b0',
    sequential: ['#eef5f2', '#d2e8e0', '#a9d2c4', '#7cb8a6', '#4f9c88', '#2f7d6d', '#1d5a4e'],
    status: { good: '#2f9e5b', warning: '#b7791f', critical: '#c53030' },
    text: { primary: '#17201c', secondary: '#45534c', muted: '#6b7a73' },
    grid: 'rgba(23, 32, 28, 0.07)',
    axis: 'rgba(23, 32, 28, 0.2)',
    surface: '#fbfcfb',
    tooltipBg: '#ffffff',
    tooltipBorder: '#d9e1dc',
    glow: 0,
  },
  abyss: {
    categorical: DARK_CATEGORICAL,
    single: '#4fc3d9',
    singleSoft: 'rgba(79, 195, 217, 0.16)',
    compare: '#4d6878',
    sequential: ['#102330', '#123447', '#13495f', '#156179', '#1b7c93', '#2f9fb7', '#7fd8e8'],
    status: { good: '#47c78a', warning: '#f2c14e', critical: '#f2766b' },
    text: { primary: '#e3eef3', secondary: '#a9c2ce', muted: '#7896a5' },
    grid: 'rgba(227, 238, 243, 0.06)',
    axis: 'rgba(227, 238, 243, 0.16)',
    surface: '#0d1b26',
    tooltipBg: '#132634',
    tooltipBorder: '#22394a',
    glow: 0,
  },
  pine: {
    categorical: DARK_CATEGORICAL,
    single: '#ff8a65',
    singleSoft: 'rgba(255, 138, 101, 0.16)',
    compare: '#56695f',
    sequential: ['#17241f', '#2a3326', '#4a4029', '#6d4d2f', '#934f3a', '#c76449', '#ff9a78'],
    status: { good: '#5cc58a', warning: '#e8b04a', critical: '#f26d6d' },
    text: { primary: '#e6efe9', secondary: '#b5c6bc', muted: '#7f978b' },
    grid: 'rgba(230, 239, 233, 0.06)',
    axis: 'rgba(230, 239, 233, 0.16)',
    surface: '#13201b',
    tooltipBg: '#1b2b24',
    tooltipBorder: '#2b4037',
    glow: 0,
  },
  neon: {
    categorical: DARK_CATEGORICAL,
    single: '#22d3ee',
    singleSoft: 'rgba(34, 211, 238, 0.18)',
    compare: '#4a5d85',
    sequential: ['#0e1a38', '#0f2b55', '#0f4170', '#0f5b8a', '#1279a4', '#1fa3c4', '#6fe3f2'],
    status: { good: '#34d399', warning: '#fbbf24', critical: '#fb7185' },
    text: { primary: '#e6f1ff', secondary: '#a9bddf', muted: '#6d82a8' },
    grid: 'rgba(120, 170, 255, 0.08)',
    axis: 'rgba(120, 170, 255, 0.25)',
    surface: '#0b1430',
    tooltipBg: '#0f1b3d',
    tooltipBorder: '#1f3a73',
    glow: 10,
  },
};
