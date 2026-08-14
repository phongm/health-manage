import { api } from '../../services/api'

Page({
  data: {
    barcode: '',
    name: '',
    imageFileId: '',
    saving: false,
  },
  onName(e: WechatMiniprogram.Input) {
    this.setData({ name: e.detail.value })
  },
  async scan() {
    try {
      const res = await wx.scanCode({ onlyFromCamera: false })
      this.setData({ barcode: res.result || '' })
    } catch {
      wx.showToast({ title: '未扫到条码', icon: 'none' })
    }
  },
  async pickPhoto() {
    try {
      const res = await wx.chooseImage({ count: 1, sizeType: ['compressed'] })
      this.setData({ imageFileId: res.tempFilePaths[0] || '' })
    } catch {
      wx.showToast({ title: '未选择图片', icon: 'none' })
    }
  },
  async submit() {
    if (!this.data.barcode && !this.data.name.trim()) {
      wx.showToast({ title: '请填写名称或扫码', icon: 'none' })
      return
    }
    this.setData({ saving: true })
    try {
      const result = await api.contribute({
        barcode: this.data.barcode || null,
        name: this.data.name.trim() || null,
        image_file_id: this.data.imageFileId || null,
      })
      wx.showToast({ title: result.message || '已提交', icon: 'none' })
      this.setData({ barcode: '', name: '', imageFileId: '' })
    } catch (err) {
      wx.showToast({ title: err instanceof Error ? err.message : '提交失败', icon: 'none' })
    } finally {
      this.setData({ saving: false })
    }
  },
})
