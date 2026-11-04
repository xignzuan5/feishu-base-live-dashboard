/**
 * 看板全局配置：换一张多维表格时，先改这里。
 */
export const DASHBOARD_CONFIG = {
  /** 看板标题（页头展示） */
  title: '鹿野咖啡经营实时看板',
  /** 业务时区：自然日、小时分桶都按它算 */
  timezone: 'Asia/Shanghai',
  /** 数据源多维表格链接（页头「数据源」按钮跳转） */
  baseUrl: 'https://your-tenant.feishu.cn/base/<base_token>',
  /** 不计入营收的订单状态 */
  invalidStatuses: ['已退款', '已取消'],
  /** 营业时段（热力图横轴、今日目标按已过营业时长折算） */
  businessHours: { open: 7, close: 22 },
} as const;
