import { DISCLAIMER, NUTRIENT_LABEL } from '../../core/copy'
import { api } from '../../services/api'

type Achieve = { key: string; intake: number; target: number; ratio: number; cap: boolean; label: string }
type Micro = { key: string; intake: number | null; target: number | null; unknown: boolean; label: string }
type Structure = { category: string; label: string; count: number; pct: number }

Page({
  data: {
    start: '',
    end: '',
    loggedDays: 0,
    avgKcal: 0,
    targetKcal: 0,
    protein: 0,
    proteinTarget: 0,
    weightDelta: '',
    topFoods: [] as { name: string; count: number }[],
    days: [] as { date: string; logged: boolean; kcal: number }[],
    achievement: [] as Achieve[],
    micros: [] as Micro[],
    structure: [] as Structure[],
    disclaimer: DISCLAIMER,
  },
  async onShow() {
    try {
      const data = await api.weeklyReport()
      const avg = (data.avg_intake as Record<string, number>) || {}
      const target = (data.target as Record<string, number>) || {}
      const weight = (data.weight as { delta?: number | null }) || {}
      const days = ((data.days as { date: string; logged: boolean; intake: Record<string, number> }[]) || []).map(
        (d) => ({
          date: d.date.slice(5),
          logged: d.logged,
          kcal: Math.round(d.intake?.energy_kcal || 0),
        }),
      )
      this.setData({
        start: String(data.start || ''),
        end: String(data.end || ''),
        loggedDays: Number(data.logged_days || 0),
        avgKcal: Math.round(avg.energy_kcal || 0),
        targetKcal: Math.round(target.energy_kcal || 0),
        protein: Math.round(avg.protein_g || 0),
        proteinTarget: Math.round(target.protein_g || 0),
        weightDelta: weight.delta == null ? '本周暂无足够体重记录' : `本周体重变化 ${weight.delta} kg`,
        topFoods: (data.top_foods as { name: string; count: number }[]) || [],
        days,
        achievement: ((data.achievement as Omit<Achieve, 'label'>[]) || []).map((row) => ({
          ...row,
          label: NUTRIENT_LABEL[row.key] || row.key,
        })),
        micros: ((data.micros as Omit<Micro, 'label'>[]) || []).map((row) => ({
          ...row,
          label: NUTRIENT_LABEL[row.key] || row.key,
        })),
        structure: (data.structure as Structure[]) || [],
      })
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '加载失败', icon: 'none' })
    }
  },
})
