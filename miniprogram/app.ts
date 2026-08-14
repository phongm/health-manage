import { KEYS, createStorage } from './core/storage/index'

App({
  globalData: {
    token: '' as string,
  },
  onLaunch() {
    const storage = createStorage({
      get: (key) => wx.getStorageSync(key),
      set: (key, value) => wx.setStorageSync(key, value),
      remove: (key) => wx.removeStorageSync(key),
      info: () => wx.getStorageInfoSync(),
    })
    const token = storage.get<string>(KEYS.token)
    if (token) {
      this.globalData.token = token
      import('./services/api').then(({ api }) => api.sync().catch(() => undefined))
    }
  },
})
