import { computeProfileTargets } from '../../core/nutrition/index'
import {
  ALLERGEN_OPTIONS,
  EXCLUDE_TEXT,
  HEALTH_FLAG_OPTIONS,
  MEAT_OPTIONS,
  WARNING_TEXT,
} from '../../core/copy'
import { api } from '../../services/api'
import type { ActivityLevel, Gender, Goal } from '../../core/nutrition/types'

const ACTIVITY_LABELS = ['久坐', '轻度活动', '中度活动', '高强度', '极高强度']
const SPICE_LABELS = ['不吃辣', '微辣', '中辣', '嗜辣']

Page({
  data: {
    step: 1,
    gender: 2 as Gender,
    birthYear: 1995,
    heightCm: 165,
    weightKg: 60,
    activityLevel: 2 as ActivityLevel,
    activityLabels: ACTIVITY_LABELS,
    activityLabel: ACTIVITY_LABELS[1],
    goal: 1 as Goal,
    goalRateKgWk: 0.5,
    targetKcal: 0,
    warningTexts: [] as string[],
    excluded: false,
    excludeText: '',
    sceneDefault: 'takeout',
    spiceLevel: 2,
    spiceLabels: SPICE_LABELS,
    dietType: 'omnivore',
    avoidText: '',
    allergenOptions: ALLERGEN_OPTIONS.map((o) => ({ ...o, on: false })),
    meatOptions: MEAT_OPTIONS.map((o) => ({ ...o, on: false })),
    healthOptions: HEALTH_FLAG_OPTIONS.map((o) => ({ ...o, on: o.key === 'none' })),
    healthFlags: ['none'] as string[],
    saving: false,
  },
  onLoad() {
    this.recompute()
  },
  onGender(e: WechatMiniprogram.TouchEvent) {
    this.setData({ gender: Number(e.currentTarget.dataset.value) as Gender })
    this.recompute()
  },
  onField(e: WechatMiniprogram.Input) {
    const field = e.currentTarget.dataset.field as string
    this.setData({ [field]: Number(e.detail.value) } as Record<string, number>)
    this.recompute()
  },
  onActivity(e: WechatMiniprogram.PickerChange) {
    const activityLevel = (Number(e.detail.value) + 1) as ActivityLevel
    this.setData({ activityLevel, activityLabel: ACTIVITY_LABELS[Number(e.detail.value)] })
    this.recompute()
  },
  onScene(e: WechatMiniprogram.TouchEvent) {
    this.setData({ sceneDefault: String(e.currentTarget.dataset.value) })
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
    const allergenOptions = this.data.allergenOptions.map((o) =>
      o.key === key ? { ...o, on: !o.on } : o,
    )
    this.setData({ allergenOptions, selectedAllergens: allergenOptions.filter((o) => o.on).map((o) => o.key) })
  },
  toggleMeat(e: WechatMiniprogram.TouchEvent) {
    const key = String(e.currentTarget.dataset.key)
    this.setData({
      meatOptions: this.data.meatOptions.map((o) => (o.key === key ? { ...o, on: !o.on } : o)),
    })
  },
  toggleHealth(e: WechatMiniprogram.TouchEvent) {
    const key = String(e.currentTarget.dataset.key)
    let flags = this.data.healthFlags.slice()
    if (key === 'none') {
      flags = ['none']
    } else {
      flags = flags.filter((k) => k !== 'none')
      flags = flags.includes(key) ? flags.filter((k) => k !== key) : flags.concat(key)
      if (!flags.length) flags = ['none']
    }
    this.setData({
      healthFlags: flags,
      healthOptions: HEALTH_FLAG_OPTIONS.map((o) => ({ ...o, on: flags.includes(o.key) })),
    })
    this.recompute()
  },
  recompute() {
    const result = computeProfileTargets(
      {
        gender: this.data.gender,
        birthYear: this.data.birthYear,
        heightCm: this.data.heightCm,
        weightKg: this.data.weightKg,
        activityLevel: this.data.activityLevel,
        goal: this.data.goal,
        goalRateKgWk: this.data.goalRateKgWk,
        healthFlags: this.data.healthFlags,
      },
      new Date().getFullYear(),
    )
    this.setData({
      targetKcal: result.targetKcal,
      warningTexts: result.warnings.map((w) => WARNING_TEXT[w] || w),
      excluded: result.isExcluded,
      excludeText: result.excludeReason ? EXCLUDE_TEXT[result.excludeReason] || result.excludeReason : '',
    })
  },
  next() {
    this.setData({ step: 2 })
  },
  back() {
    this.setData({ step: 1 })
  },
  async submit() {
    this.setData({ saving: true })
    try {
      const profile = await api.putProfile({
        gender: this.data.gender,
        birth_year: this.data.birthYear,
        height_cm: this.data.heightCm,
        weight_kg: this.data.weightKg,
        activity_level: this.data.activityLevel,
        goal: this.data.goal,
        goal_rate_kg_wk: this.data.goalRateKgWk,
        health_flags: this.data.healthFlags,
      })
      const avoidIngredients = this.data.avoidText
        .split(/[,，、\s]+/)
        .map((s) => s.trim())
        .filter(Boolean)
        .concat(this.data.meatOptions.filter((o) => o.on && o.kind === 'ingredient').map((o) => o.key))
      const avoidCategories = this.data.meatOptions.filter((o) => o.on && o.kind === 'category').map((o) => o.key)
      await api.putPreferences({
        scene_default: this.data.sceneDefault,
        spice_level: this.data.spiceLevel,
        diet_type: this.data.dietType,
        avoid_ingredients: avoidIngredients,
        allergens: this.data.allergenOptions.filter((o) => o.on).map((o) => o.key),
        avoid_categories: avoidCategories,
      })
      wx.setStorageSync('profile', profile)
      wx.redirectTo({ url: '/pages/home/index' })
    } catch (err) {
      wx.showToast({
        title: err instanceof Error ? err.message : '保存失败',
        icon: 'none',
      })
    } finally {
      this.setData({ saving: false })
    }
  },
})
