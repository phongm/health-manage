import { api } from '../../services/api'
import { todayStr } from '../../utils/format'

function daysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  const month = `${d.getMonth() + 1}`.padStart(2, '0')
  const day = `${d.getDate()}`.padStart(2, '0')
  return `${d.getFullYear()}-${month}-${day}`
}

Page({
  data: {
    weight: '',
    today: todayStr(),
    trend: '' as string,
    bars: [] as { date: string; kg: number; height: number }[],
  },
  onShow() {
    this.load()
  },
  onWeight(e: WechatMiniprogram.Input) {
    this.setData({ weight: e.detail.value })
  },
  async load() {
    try {
      const data = await api.getWeight(daysAgo(29), todayStr())
      const values = data.ma7.length ? data.ma7 : data.logs
      const max = Math.max(...values.map((v) => v.weight_kg), 1)
      const min = Math.min(...values.map((v) => v.weight_kg), max)
      const span = Math.max(max - min, 1)
      this.setData({
        bars: values.slice(-14).map((v) => ({
          date: v.log_date.slice(5),
          kg: v.weight_kg,
          height: Math.round(((v.weight_kg - min) / span) * 160 + 40),
        })),
        trend:
          data.trend_kg_per_week == null
            ? '记录几天后可以看到周趋势'
            : `近一周约 ${data.trend_kg_per_week > 0 ? '+' : ''}${data.trend_kg_per_week} kg`,
      })
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '加载失败', icon: 'none' })
    }
  },
  async save() {
    const weight = Number(this.data.weight)
    if (!weight) {
      wx.showToast({ title: '请输入体重', icon: 'none' })
      return
    }
    try {
      await api.putWeight({ log_date: todayStr(), weight_kg: weight })
      this.setData({ weight: '' })
      this.load()
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '保存失败', icon: 'none' })
    }
  },
})
