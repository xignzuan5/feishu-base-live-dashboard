/**
 * 实体固定配色：同一个实体（某品类、某渠道…）在所有图表里永远是同一个颜色，
 * 颜色跟着实体走，不跟着排名走（排名变化、筛选后系列变少都不会「换色」）。
 *
 * 每一组是同一维度的取值，组内顺序 = 分类色槽位顺序（最多 6 个，第 7 个起折叠为「其他」）。
 * 换一张多维表格时，把这里改成你的维度取值；不在表里的实体按出现顺序取色。
 */
export const ENTITY_GROUPS: string[][] = [
  ['意式咖啡', '手冲精品', '茶饮', '轻食', '烘焙', '周边'],
  ['堂食', '到店自提', '小程序外送', '美团外卖', '饿了么', '企业团购'],
  ['旗舰店', '标准店', '快取店', '校园店'],
  ['华东', '华北', '华南', '西南', '华中'],
  ['热', '冰', '少冰'],
  ['女', '男', '未知'],
  ['会员总数', '窗口内活跃'],
  ['会员订单', '非会员订单'],
  ['5 星', '4 星', '3 星', '2 星', '1 星'],
];

const INDEX = new Map<string, number>();
const register = (group: string[]): void => {
  group.forEach((name: string, i: number) => {
    if (!INDEX.has(name)) INDEX.set(name, i);
  });
};
ENTITY_GROUPS.forEach(register);

/** 运行时追加实体组（配置驱动看板从需求说明里带过来：状态、阶段、类型等） */
export const registerEntityGroups = (groups: string[][]): void => groups.forEach(register);

/** 实体的分类色槽位；未登记的实体用调用方给的出现顺序 */
export const entitySlot = (name: string, fallback: number): number => INDEX.get(name) ?? fallback;
