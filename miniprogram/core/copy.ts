export type Scene = 'takeout' | 'canteen' | 'homecook'

export const WARNING_TEXT: Record<string, string> = {
  rate_too_aggressive: '你设定的减重速率过快，已为你调整为更安全的方案',
  below_bmr: '目标热量低于基础代谢，已上调到更安全的水平',
  below_floor: '目标热量低于安全下限，已按安全下限执行',
}

export const EXCLUDE_TEXT: Record<string, string> = {
  diabetes: '当前版本暂不为该情况提供饮食建议，建议咨询专业人士',
  hypertension: '当前版本暂不为该情况提供饮食建议，建议咨询专业人士',
  kidney: '当前版本暂不为该情况提供饮食建议，建议咨询专业人士',
  pregnant: '当前版本暂不为该情况提供饮食建议，建议咨询专业人士',
  lactating: '当前版本暂不为该情况提供饮食建议，建议咨询专业人士',
  eating_disorder: '当前版本暂不为该情况提供饮食建议，建议咨询专业人士',
  underage: '当前版本仅面向 18 岁及以上用户',
  low_bmi: '当前体重偏低，不提供减脂方案，建议咨询专业人士',
}

export const DISCLAIMER = '以上为记录与统计参考，不是医疗建议。特殊情况请咨询专业人士。'

export const SCENE_LABEL: Record<Scene, string> = {
  takeout: '外卖',
  canteen: '食堂',
  homecook: '自己做',
}

export const ALLERGEN_OPTIONS = [
  { key: 'peanut', label: '花生' },
  { key: 'shrimp', label: '虾' },
  { key: 'crab', label: '蟹' },
  { key: 'fish', label: '鱼' },
  { key: 'egg', label: '鸡蛋' },
  { key: 'milk', label: '牛奶' },
  { key: 'wheat', label: '小麦' },
  { key: 'soy', label: '大豆' },
]

export const HEALTH_FLAG_OPTIONS = [
  { key: 'none', label: '以上都没有' },
  { key: 'diabetes', label: '糖尿病' },
  { key: 'hypertension', label: '高血压' },
  { key: 'kidney', label: '肾病' },
  { key: 'pregnant', label: '孕期' },
  { key: 'lactating', label: '哺乳期' },
  { key: 'eating_disorder', label: '进食障碍史' },
]

export const MEAT_OPTIONS = [
  { key: 'pork', label: '猪肉', kind: 'ingredient' as const },
  { key: 'beef', label: '牛肉', kind: 'ingredient' as const },
  { key: 'chicken', label: '鸡肉', kind: 'ingredient' as const },
  { key: 'organ_meat', label: '内脏', kind: 'category' as const },
]

export const NUTRIENT_LABEL: Record<string, string> = {
  energy_kcal: '热量',
  protein_g: '蛋白质',
  cho_g: '碳水',
  fat_g: '脂肪',
  fiber_g: '膳食纤维',
  sodium_mg: '钠',
  calcium_mg: '钙',
  iron_mg: '铁',
  vitamin_a_ug: '维生素A',
  vitamin_c_mg: '维生素C',
}
