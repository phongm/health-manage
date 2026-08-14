import { api } from '../../services/api'

Page({
  data: {
    targetKcal: 0,
    excluded: false,
  },
  onShow() {
    this.load()
  },
  async load() {
    try {
      const profile = await api.getProfile()
      this.setData({
        targetKcal: Math.round(Number(profile.target_kcal || 0)),
        excluded: Boolean(profile.is_excluded),
      })
    } catch {
      this.setData({ targetKcal: 0 })
    }
  },
  go(e: WechatMiniprogram.TouchEvent) {
    wx.navigateTo({ url: String(e.currentTarget.dataset.url) })
  },
  async exportData() {
    try {
      const data = await api.exportData()
      await wx.setClipboardData({ data: JSON.stringify(data) })
      wx.showToast({ title: '已复制到剪贴板', icon: 'success' })
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '导出失败', icon: 'none' })
    }
  },
})
