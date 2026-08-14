import { ApiError, api, type Recommendation } from '../../services/api'
import { MEAL_LABEL, todayStr } from '../../utils/format'

Page({
  data: {
    days: [] as { date: string; meals: Recommendation[] }[],
    loading: false,
    error: '',
  },
  onShow() {
    this.load()
  },
  async load() {
    this.setData({ loading: true, error: '' })
    try {
      const data = await api.recommendPlan(todayStr(), 3)
      this.setData({
        days: data.days.map((day) => ({
          ...day,
          meals: day.meals.map((meal) => ({ ...meal, meal_label: MEAL_LABEL[meal.meal_type] || meal.meal_type })),
        })),
        loading: false,
      })
    } catch (err) {
      const message = err instanceof ApiError ? err.message : err instanceof Error ? err.message : '加载失败'
      this.setData({ error: message, loading: false, days: [] })
    }
  },
  async accept(e: WechatMiniprogram.TouchEvent) {
    const dayIndex = Number(e.currentTarget.dataset.day)
    const mealIndex = Number(e.currentTarget.dataset.meal)
    const rec = this.data.days[dayIndex]?.meals[mealIndex]
    if (!rec) return
    try {
      await api.createIntake({
        log_date: this.data.days[dayIndex].date,
        meal_type: rec.meal_type,
        input_source: 'recommend',
        from_rec_id: rec.rec_id,
        items: rec.items.map((item) => ({
          food_id: item.food_id,
          grams: item.grams,
          portion_label: item.portion_label,
        })),
      })
      wx.showToast({ title: '已记入', icon: 'success' })
      wx.redirectTo({ url: '/pages/home/index' })
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '记录失败', icon: 'none' })
    }
  },
})
