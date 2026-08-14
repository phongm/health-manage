import { api } from '../../services/api'
import { todayStr } from '../../utils/format'

Page({
  data: {
    exercises: [] as { id: number; name: string }[],
    selectedId: 0,
    selectedName: '请选择',
    duration: 30,
    intensity: 2,
    logs: [] as { id: number; name: string; duration_min: number; kcal_burned: number }[],
  },
  onShow() {
    this.load()
  },
  async load() {
    try {
      const [types, logs] = await Promise.all([api.listExercises(), api.listExerciseLogs(todayStr())])
      this.setData({
        exercises: types.items,
        logs: logs.items,
        selectedId: this.data.selectedId || types.items[0]?.id || 0,
        selectedName: this.data.selectedName === '请选择' ? types.items[0]?.name || '请选择' : this.data.selectedName,
      })
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '加载失败', icon: 'none' })
    }
  },
  pickType() {
    const names = this.data.exercises.map((e) => e.name)
    wx.showActionSheet({
      itemList: names,
      success: (res) => {
        const item = this.data.exercises[res.tapIndex]
        this.setData({ selectedId: item.id, selectedName: item.name })
      },
    })
  },
  onDuration(e: WechatMiniprogram.Input) {
    this.setData({ duration: Number(e.detail.value) || 0 })
  },
  onIntensity(e: WechatMiniprogram.TouchEvent) {
    this.setData({ intensity: Number(e.currentTarget.dataset.value) })
  },
  async save() {
    if (!this.data.selectedId || !this.data.duration) {
      wx.showToast({ title: '请选择运动和时长', icon: 'none' })
      return
    }
    try {
      await api.createExercise({
        log_date: todayStr(),
        exercise_id: this.data.selectedId,
        duration_min: this.data.duration,
        intensity: this.data.intensity,
      })
      this.load()
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '保存失败', icon: 'none' })
    }
  },
  async remove(e: WechatMiniprogram.TouchEvent) {
    try {
      await api.deleteExercise(Number(e.currentTarget.dataset.id))
      this.load()
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '删除失败', icon: 'none' })
    }
  },
})
