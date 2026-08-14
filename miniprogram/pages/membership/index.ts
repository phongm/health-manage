import { api } from '../../services/api'

Page({
  data: {
    plan: 'free',
    note: '',
    quotas: [] as { key: string; value: number }[],
  },
  async onShow() {
    try {
      const data = await api.membership()
      const quotas = data.quotas || {}
      this.setData({
        plan: data.plan,
        note: data.note,
        quotas: [
          { key: '每日推荐', value: quotas.recommend_daily },
          { key: '每餐换一换', value: quotas.swap_per_meal },
          { key: '每日拍照解析', value: quotas.parse_image_daily },
          { key: '多日食谱天数', value: quotas.plan_days },
        ],
      })
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '加载失败', icon: 'none' })
    }
  },
})
