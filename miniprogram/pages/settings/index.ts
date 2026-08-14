import { ALLERGEN_OPTIONS, MEAT_OPTIONS } from '../../core/copy'
import { api } from '../../services/api'

Page({
  data: {
    sceneDefault: 'takeout',
    dietType: 'omnivore',
    spiceLevel: 2,
    avoidText: '',
    allergenOptions: ALLERGEN_OPTIONS.map((o) => ({ ...o, on: false })),
    meatOptions: MEAT_OPTIONS.map((o) => ({ ...o, on: false })),
    lunchScene: '',
    dinnerScene: '',
    saving: false,
  },
  async onShow() {
    try {
      const prefs = await api.getPreferences()
      const allergens = (prefs.allergens as string[]) || []
      const avoidIngredients = ((prefs.avoid_ingredients as string[]) || [])
      const avoidCategories = ((prefs.avoid_categories as string[]) || [])
      const meatKeys = new Set([...avoidIngredients, ...avoidCategories])
      const byMeal = (prefs.scene_by_meal as Record<string, string>) || {}
      this.setData({
        sceneDefault: String(prefs.scene_default || 'takeout'),
        dietType: String(prefs.diet_type || 'omnivore'),
        spiceLevel: Number(prefs.spice_level ?? 2),
        avoidText: avoidIngredients.filter((item) => !MEAT_OPTIONS.some((m) => m.key === item)).join('、'),
        allergenOptions: ALLERGEN_OPTIONS.map((o) => ({ ...o, on: allergens.includes(o.key) })),
        meatOptions: MEAT_OPTIONS.map((o) => ({ ...o, on: meatKeys.has(o.key) })),
        lunchScene: byMeal.lunch || '',
        dinnerScene: byMeal.dinner || '',
      })
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '加载失败', icon: 'none' })
    }
  },
  onScene(e: WechatMiniprogram.TouchEvent) {
    this.setData({ sceneDefault: String(e.currentTarget.dataset.value) })
  },
  onMealScene(e: WechatMiniprogram.TouchEvent) {
    const meal = String(e.currentTarget.dataset.meal)
    const value = String(e.currentTarget.dataset.value)
    if (meal === 'lunch') this.setData({ lunchScene: this.data.lunchScene === value ? '' : value })
    if (meal === 'dinner') this.setData({ dinnerScene: this.data.dinnerScene === value ? '' : value })
  },
  onDiet(e: WechatMiniprogram.TouchEvent) {
    this.setData({ dietType: String(e.currentTarget.dataset.value) })
  },
  onSpice(e: WechatMiniprogram.TouchEvent) {
    this.setData({ spiceLevel: Number(e.currentTarget.dataset.value) })
  },
  onAvoid(e: WechatMiniprogram.Input) {
    this.setData({ avoidText: e.detail.value })
  },
  toggleAllergen(e: WechatMiniprogram.TouchEvent) {
    const key = String(e.currentTarget.dataset.key)
    this.setData({
      allergenOptions: this.data.allergenOptions.map((o) => (o.key === key ? { ...o, on: !o.on } : o)),
    })
  },
  toggleMeat(e: WechatMiniprogram.TouchEvent) {
    const key = String(e.currentTarget.dataset.key)
    this.setData({
      meatOptions: this.data.meatOptions.map((o) => (o.key === key ? { ...o, on: !o.on } : o)),
    })
  },
  async save() {
    this.setData({ saving: true })
    const sceneByMeal: Record<string, string> = {}
    if (this.data.lunchScene) sceneByMeal.lunch = this.data.lunchScene
    if (this.data.dinnerScene) sceneByMeal.dinner = this.data.dinnerScene
    try {
      await api.putPreferences({
        scene_default: this.data.sceneDefault,
        diet_type: this.data.dietType,
        spice_level: this.data.spiceLevel,
        allergens: this.data.allergenOptions.filter((o) => o.on).map((o) => o.key),
        avoid_ingredients: this.data.avoidText
          .split(/[,，、\s]+/)
          .map((s) => s.trim())
          .filter(Boolean)
          .concat(this.data.meatOptions.filter((o) => o.on && o.kind === 'ingredient').map((o) => o.key)),
        avoid_categories: this.data.meatOptions.filter((o) => o.on && o.kind === 'category').map((o) => o.key),
        scene_by_meal: Object.keys(sceneByMeal).length ? sceneByMeal : null,
      })
      wx.showToast({ title: '已保存', icon: 'success' })
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '保存失败', icon: 'none' })
    } finally {
      this.setData({ saving: false })
    }
  },
})
