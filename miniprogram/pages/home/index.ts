import { DISCLAIMER, SCENE_LABEL, type Scene } from '../../core/copy'
import { ApiError, api, type Dashboard, type Recommendation } from '../../services/api'
import { MEAL_LABEL, todayStr } from '../../utils/format'

const SWAP_REASONS = [
  { key: 'not_available', label: '买不到 / 做不了' },
  { key: 'dont_like', label: '不喜欢' },
  { key: 'too_much', label: '份量太大' },
  { key: 'other', label: '换一个看看' },
]

Page({
  data: {
    date: todayStr(),
    remainingKcal: 0,
    targetKcal: 0,
    intakeKcal: 0,
    protein: 0,
    proteinTarget: 0,
    cho: 0,
    choTarget: 0,
    fat: 0,
    fatTarget: 0,
    fiber: 0,
    fiberTarget: 0,
    sodium: 0,
    sodiumTarget: 0,
    exerciseCredited: 0,
    meals: [] as { key: string; label: string; kcal: number; logged: boolean }[],
    items: [] as Dashboard['items'],
    excluded: false,
    excludeText: '',
    error: '',
    rec: null as Recommendation | null,
    recLoading: false,
    recError: '',
    nextMealLabel: '',
    sceneLabel: '',
    scene: '',
    avoid: [] as { title: string; reason: string; level: string }[],
    disclaimer: DISCLAIMER,
    accepting: false,
  },
  onShow() {
    this.load()
  },
  applyDash(dash: Dashboard) {
    const meals = ['breakfast', 'lunch', 'dinner', 'snack'].map((key) => ({
      key,
      label: MEAL_LABEL[key],
      kcal: dash.meals[key]?.kcal || 0,
      logged: Boolean(dash.meals[key]?.logged),
    }))
    this.setData({
      date: dash.date,
      remainingKcal: Math.round(dash.remaining.energy_kcal || 0),
      targetKcal: Math.round(dash.target.energy_kcal || 0),
      intakeKcal: Math.round(dash.intake.energy_kcal || 0),
      protein: Math.round(dash.intake.protein_g || 0),
      proteinTarget: Math.round(dash.target.protein_g || 0),
      cho: Math.round(dash.intake.cho_g || 0),
      choTarget: Math.round(dash.target.cho_g || 0),
      fat: Math.round(dash.intake.fat_g || 0),
      fatTarget: Math.round(dash.target.fat_g || 0),
      fiber: Math.round(dash.intake.fiber_g || 0),
      fiberTarget: Math.round(dash.target.fiber_g || 0),
      sodium: Math.round(dash.intake.sodium_mg || 0),
      sodiumTarget: Math.round(dash.target.sodium_mg || 0),
      exerciseCredited: Math.round(dash.exercise?.credited_kcal || 0),
      meals,
      items: dash.items,
      nextMealLabel: MEAL_LABEL[dash.next_meal] || dash.next_meal,
    })
  },
  async load() {
    try {
      const [dash, profile] = await Promise.all([api.getDashboard(todayStr()), api.getProfile().catch(() => null)])
      const excluded = Boolean(profile && profile.is_excluded)
      this.applyDash(dash)
      this.setData({
        excluded,
        excludeText: excluded ? '当前仅提供记录功能，暂不提供饮食建议。' : '',
        error: '',
      })
      if (excluded) {
        this.setData({ rec: null, avoid: [] })
        return
      }
      await this.loadRecommend(dash.next_meal)
    } catch (err) {
      this.setData({ error: err instanceof Error ? err.message : '加载失败' })
    }
  },
  async loadRecommend(mealType?: string, scene?: string) {
    this.setData({ recLoading: true, recError: '' })
    try {
      const rec = await api.recommend({
        date: todayStr(),
        meal_type: mealType,
        scene: scene || this.data.scene || undefined,
      })
      this.setData({
        rec,
        scene: rec.scene,
        sceneLabel: SCENE_LABEL[rec.scene as Scene] || rec.scene,
        avoid: rec.avoid_list || [],
        nextMealLabel: MEAL_LABEL[rec.meal_type] || rec.meal_type,
        recLoading: false,
      })
    } catch (err) {
      if (err instanceof ApiError && err.code === 3001) {
        this.setData({ excluded: true, excludeText: err.message, rec: null, recLoading: false })
        return
      }
      this.setData({ recError: err instanceof Error ? err.message : '推荐暂时不可用', recLoading: false })
      try {
        const avoid = await api.avoidList(todayStr())
        this.setData({ avoid: avoid.items })
      } catch {
        this.setData({ avoid: [] })
      }
    }
  },
  goLog() {
    const meal = this.data.rec?.meal_type || ''
    wx.redirectTo({ url: meal ? `/pages/log/index?meal=${meal}` : '/pages/log/index' })
  },
  onScene(e: WechatMiniprogram.TouchEvent) {
    const scene = String(e.currentTarget.dataset.value)
    this.setData({ scene, sceneLabel: SCENE_LABEL[scene as Scene] || scene })
    this.loadRecommend(this.data.rec?.meal_type, scene)
  },
  async acceptRec() {
    const rec = this.data.rec
    if (!rec?.items?.length) return
    this.setData({ accepting: true })
    try {
      const result = await api.createIntake({
        log_date: todayStr(),
        meal_type: rec.meal_type,
        input_source: 'recommend',
        from_rec_id: rec.rec_id,
        items: rec.items.map((item) => ({
          food_id: item.food_id,
          grams: item.grams,
          portion_label: item.portion_label,
        })),
      })
      this.applyDash(result.today)
      wx.showToast({ title: '已记入今日', icon: 'success' })
      await this.loadRecommend(result.today.next_meal)
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '记录失败', icon: 'none' })
    } finally {
      this.setData({ accepting: false })
    }
  },
  async ignoreRec() {
    const rec = this.data.rec
    if (!rec) return
    try {
      await api.feedback(rec.rec_id, 'ignore', rec.items.map((i) => i.food_id))
    } catch {
      // ignore
    }
    this.goLog()
  },
  swapItem(e: WechatMiniprogram.TouchEvent) {
    const rec = this.data.rec
    if (!rec) return
    const foodId = Number(e.currentTarget.dataset.id)
    const item = rec.items.find((i) => i.food_id === foodId)
    if (!item || !item.swappable) {
      wx.showToast({ title: '这一项暂不建议替换', icon: 'none' })
      return
    }
    if (rec.swaps_remaining <= 0) {
      wx.showToast({ title: '本餐换一换次数已用完', icon: 'none' })
      return
    }
    wx.showActionSheet({
      itemList: SWAP_REASONS.map((r) => r.label),
      success: async (res) => {
        const reason = SWAP_REASONS[res.tapIndex].key
        try {
          const next = await api.swap(rec.rec_id, foodId, reason)
          this.setData({ rec: next, avoid: next.avoid_list || [] })
        } catch (err) {
          wx.showToast({ title: err instanceof Error ? err.message : '替换失败', icon: 'none' })
        }
      },
    })
  },
  async removeItem(e: WechatMiniprogram.TouchEvent) {
    const id = Number(e.currentTarget.dataset.id)
    try {
      const result = await api.deleteIntake(id)
      this.applyDash(result.today)
      if (!this.data.excluded) await this.loadRecommend(result.today.next_meal)
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '删除失败', icon: 'none' })
    }
  },
})
