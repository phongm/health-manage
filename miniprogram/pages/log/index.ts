import { api, type FoodItem } from '../../services/api'
import { todayStr } from '../../utils/format'

type CartItem = {
  food_id: number
  name: string
  grams: number
  portion_label: string
  kcal: number
  need_confirm?: boolean
}

Page({
  data: {
    mealType: 'lunch',
    mealTypes: [
      { key: 'breakfast', label: '早餐' },
      { key: 'lunch', label: '午餐' },
      { key: 'dinner', label: '晚餐' },
      { key: 'snack', label: '加餐' },
    ],
    q: '',
    sentence: '',
    imageHint: '',
    listening: false,
    results: [] as FoodItem[],
    cart: [] as CartItem[],
    hot: [] as FoodItem[],
    saving: false,
    inputSource: 'text',
  },
  searchTimer: 0 as number,
  onLoad(query: Record<string, string>) {
    if (query.meal) this.setData({ mealType: query.meal })
    this.loadHot()
  },
  async loadHot() {
    try {
      const cached = wx.getStorageSync('hot_foods') as FoodItem[] | ''
      if (cached && Array.isArray(cached) && cached.length) {
        this.setData({ hot: cached })
      }
      const data = await api.hotFoods()
      this.setData({ hot: data.items })
      wx.setStorageSync('hot_foods', data.items)
    } catch {
      if (!this.data.hot.length) this.setData({ hot: [] })
    }
  },
  onMeal(e: WechatMiniprogram.TouchEvent) {
    this.setData({ mealType: String(e.currentTarget.dataset.key) })
  },
  onQuery(e: WechatMiniprogram.Input) {
    this.setData({ q: e.detail.value })
    if (this.searchTimer) clearTimeout(this.searchTimer)
    this.searchTimer = setTimeout(() => {
      this.doSearch()
    }, 280) as unknown as number
  },
  async doSearch() {
    const q = this.data.q.trim()
    if (!q) {
      this.setData({ results: [] })
      return
    }
    try {
      const data = await api.searchFoods(q)
      this.setData({ results: data.items })
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '搜索失败', icon: 'none' })
    }
  },
  onSentence(e: WechatMiniprogram.Input) {
    this.setData({ sentence: e.detail.value })
  },
  onImageHint(e: WechatMiniprogram.Input) {
    this.setData({ imageHint: e.detail.value })
  },
  applyParsed(parsed: { items: CartItem[]; unresolved?: string[] }, source: 'text' | 'voice' | 'image') {
    if (!parsed.items.length) {
      wx.showToast({ title: '没有识别到食物', icon: 'none' })
      return
    }
    const cart = this.data.cart.concat(
      parsed.items.map((item) => ({
        food_id: item.food_id,
        name: item.name,
        grams: item.grams,
        portion_label: item.portion_label,
        kcal: item.kcal || 0,
        need_confirm: Boolean(item.need_confirm) || source === 'image',
      })),
    )
    this.setData({ cart, inputSource: source })
    if (parsed.unresolved?.length) {
      wx.showToast({ title: `未识别：${parsed.unresolved[0]}`, icon: 'none' })
    }
  },
  async parseSentence() {
    const text = this.data.sentence.trim()
    if (!text) return
    try {
      const parsed = await api.parseText(text)
      this.applyParsed(parsed as unknown as { items: CartItem[]; unresolved?: string[] }, 'text')
      this.setData({ sentence: '' })
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '解析失败', icon: 'none' })
    }
  },
  startVoice() {
    try {
      const plugin = requirePlugin('WechatSI') as {
        getRecordRecognitionManager: () => {
          start: (opts: { duration: number; lang: string }) => void
          stop: () => void
          onStart?: (cb: () => void) => void
          onStop: (cb: (res: { result: string }) => void) => void
          onError: (cb: (err: { msg?: string }) => void) => void
        }
      }
      const manager = plugin.getRecordRecognitionManager()
      manager.onStop(async (res) => {
        this.setData({ listening: false, sentence: res.result || this.data.sentence })
        const text = (res.result || '').trim()
        if (!text) return
        try {
          const parsed = await api.parseText(text)
          this.applyParsed(parsed as unknown as { items: CartItem[]; unresolved?: string[] }, 'voice')
          this.setData({ sentence: '' })
        } catch (err) {
          wx.showToast({ title: err instanceof Error ? err.message : '解析失败', icon: 'none' })
        }
      })
      manager.onError(() => {
        this.setData({ listening: false })
        wx.showToast({ title: '语音转文字失败，请改用文字录入', icon: 'none' })
      })
      this.setData({ listening: true })
      manager.start({ duration: 15000, lang: 'zh_CN' })
    } catch {
      wx.showToast({ title: '语音插件未开通，请用文字录入', icon: 'none' })
    }
  },
  async pickImage() {
    const hint = this.data.imageHint.trim()
    if (!hint) {
      wx.showToast({ title: '请先在备注里写下食物名称', icon: 'none' })
      return
    }
    try {
      await new Promise<void>((resolve, reject) => {
        wx.chooseImage({
          count: 1,
          success: () => resolve(),
          fail: reject,
        })
      })
      const parsed = await api.parseImage(hint)
      this.applyParsed(
        {
          items: parsed.items.map((item) => ({
            food_id: item.food_id,
            name: item.name,
            grams: item.grams,
            portion_label: item.portion_label,
            kcal: 0,
            need_confirm: true,
          })),
          unresolved: parsed.unresolved,
        },
        'image',
      )
      this.setData({ imageHint: '' })
      wx.showToast({ title: '已按备注解析，请确认份量', icon: 'none' })
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '图片解析失败', icon: 'none' })
    }
  },
  pickFood(e: WechatMiniprogram.TouchEvent) {
    const source = String(e.currentTarget.dataset.source)
    const index = Number(e.currentTarget.dataset.index)
    const food = (source === 'hot' ? this.data.hot : this.data.results)[index]
    if (!food) return
    const labels = food.portions.map((p) => `${p.label}（${p.grams}g）`)
    wx.showActionSheet({
      itemList: labels.length ? labels : ['100克'],
      success: (res) => {
        const portion = food.portions[res.tapIndex] || { label: '100克', grams: 100, is_default: true }
        const kcal = Math.round(((food.nutrients_per_100g.energy_kcal || 0) * portion.grams) / 100)
        const cart = this.data.cart.concat({
          food_id: food.food_id,
          name: food.name,
          grams: portion.grams,
          portion_label: portion.label,
          kcal,
        })
        this.setData({ cart, q: '', results: [] })
      },
    })
  },
  async confirmCart(e: WechatMiniprogram.TouchEvent) {
    const index = Number(e.currentTarget.dataset.index)
    const cart = this.data.cart.slice()
    const item = cart[index]
    if (!item) return
    try {
      const food = await api.getFood(item.food_id)
      const labels = food.portions.map((p) => `${p.label}（${p.grams}g）`)
      wx.showActionSheet({
        itemList: labels.length ? labels : ['确认当前份量'],
        success: (res) => {
          const portion = food.portions[res.tapIndex]
          if (portion) {
            cart[index] = {
              ...item,
              grams: portion.grams,
              portion_label: portion.label,
              need_confirm: false,
            }
          } else {
            cart[index] = { ...item, need_confirm: false }
          }
          this.setData({ cart })
        },
      })
    } catch {
      cart[index] = { ...item, need_confirm: false }
      this.setData({ cart })
    }
  },
  removeCart(e: WechatMiniprogram.TouchEvent) {
    const index = Number(e.currentTarget.dataset.index)
    const cart = this.data.cart.filter((_, i) => i !== index)
    this.setData({ cart })
  },
  async submit() {
    if (!this.data.cart.length) {
      wx.showToast({ title: '先选一种食物', icon: 'none' })
      return
    }
    if (this.data.cart.some((item) => item.need_confirm)) {
      wx.showToast({ title: '请先确认待确认的份量', icon: 'none' })
      return
    }
    this.setData({ saving: true })
    try {
      await api.createIntake({
        log_date: todayStr(),
        meal_type: this.data.mealType,
        input_source: this.data.inputSource || 'text',
        items: this.data.cart.map((item) => ({
          food_id: item.food_id,
          grams: item.grams,
          portion_label: item.portion_label,
        })),
      })
      wx.redirectTo({ url: '/pages/home/index' })
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '保存失败', icon: 'none' })
    } finally {
      this.setData({ saving: false })
    }
  },
})
