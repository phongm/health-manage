import { api } from '../../services/api'

Page({
  data: {
    loading: true,
    error: '',
  },
  onShow() {
    this.bootstrap()
  },
  async bootstrap() {
    this.setData({ loading: true, error: '' })
    try {
      const login = await wx.login()
      const session = await api.login(login.code)
      const app = getApp<{ globalData: { token: string } }>()
      app.globalData.token = session.token
      wx.setStorageSync('token', session.token)
      if (!session.profile_completed) {
        wx.redirectTo({ url: '/pages/onboarding/index' })
        return
      }
      wx.redirectTo({ url: '/pages/home/index' })
    } catch (err) {
      this.setData({
        loading: false,
        error: err instanceof Error ? err.message : '登录失败，请检查后端是否已启动',
      })
    }
  },
  retry() {
    this.bootstrap()
  },
})
