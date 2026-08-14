Component({
  properties: {
    active: { type: String, value: 'home' },
  },
  methods: {
    go(e: WechatMiniprogram.TouchEvent) {
      const url = String(e.currentTarget.dataset.url)
      const pages = getCurrentPages()
      const current = pages[pages.length - 1]
      if (current && `/${current.route}` === url) return
      wx.redirectTo({ url })
    },
  },
})
