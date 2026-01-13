// pages/settings/settings.js
const app = getApp()

Page({
  data: {
    // 随机扰动参数
    lineSpacingSigma: 5,
    fontSizeSigma: 2,
    wordSpacingSigma: 3,
    perturbXSigma: 3,
    perturbYSigma: 3,
    perturbThetaSigma: 0.01,
    
    // 涂改痕迹参数
    strikethroughProbability: 0,
    strikethroughLengthSigma: 10,
    strikethroughWidthSigma: 2,
    strikethroughAngleSigma: 0.05,
    strikethroughWidth: 3,
    
    // 墨水深度
    inkDepthSigma: 0,
    
    // API 地址
    apiBaseUrl: 'http://localhost:5000'
  },

  onLoad() {
    this.loadSettings()
  },

  loadSettings() {
    const settings = app.globalData.settings
    this.setData({
      lineSpacingSigma: settings.lineSpacingSigma,
      fontSizeSigma: settings.fontSizeSigma,
      wordSpacingSigma: settings.wordSpacingSigma,
      perturbXSigma: settings.perturbXSigma,
      perturbYSigma: settings.perturbYSigma,
      perturbThetaSigma: settings.perturbThetaSigma,
      strikethroughProbability: settings.strikethroughProbability,
      strikethroughLengthSigma: settings.strikethroughLengthSigma,
      strikethroughWidthSigma: settings.strikethroughWidthSigma,
      strikethroughAngleSigma: settings.strikethroughAngleSigma,
      strikethroughWidth: settings.strikethroughWidth,
      inkDepthSigma: settings.inkDepthSigma,
      apiBaseUrl: app.globalData.apiBaseUrl
    })
  },

  // 行间距扰动
  onLineSpacingSigmaChange(e) {
    const value = e.detail.value
    this.setData({ lineSpacingSigma: value })
    this.saveSettings()
  },

  // 字体大小扰动
  onFontSizeSigmaChange(e) {
    const value = e.detail.value
    this.setData({ fontSizeSigma: value })
    this.saveSettings()
  },

  // 字间距扰动
  onWordSpacingSigmaChange(e) {
    const value = e.detail.value
    this.setData({ wordSpacingSigma: value })
    this.saveSettings()
  },

  // 横向偏移扰动
  onPerturbXSigmaChange(e) {
    const value = e.detail.value
    this.setData({ perturbXSigma: value })
    this.saveSettings()
  },

  // 纵向偏移扰动
  onPerturbYSigmaChange(e) {
    const value = e.detail.value
    this.setData({ perturbYSigma: value })
    this.saveSettings()
  },

  // 旋转扰动
  onPerturbThetaSigmaChange(e) {
    const value = e.detail.value / 100 // 转换为小数
    this.setData({ perturbThetaSigma: value })
    this.saveSettings()
  },

  // 涂改概率
  onStrikethroughProbabilityChange(e) {
    const value = e.detail.value / 100
    this.setData({ strikethroughProbability: value })
    this.saveSettings()
  },

  // 涂改长度扰动
  onStrikethroughLengthSigmaChange(e) {
    const value = e.detail.value
    this.setData({ strikethroughLengthSigma: value })
    this.saveSettings()
  },

  // 涂改宽度扰动
  onStrikethroughWidthSigmaChange(e) {
    const value = e.detail.value
    this.setData({ strikethroughWidthSigma: value })
    this.saveSettings()
  },

  // 涂改角度扰动
  onStrikethroughAngleSigmaChange(e) {
    const value = e.detail.value / 100
    this.setData({ strikethroughAngleSigma: value })
    this.saveSettings()
  },

  // 涂改线宽
  onStrikethroughWidthChange(e) {
    const value = e.detail.value
    this.setData({ strikethroughWidth: value })
    this.saveSettings()
  },

  // 墨水深度扰动
  onInkDepthSigmaChange(e) {
    const value = e.detail.value
    this.setData({ inkDepthSigma: value })
    this.saveSettings()
  },

  // API 地址变化
  onApiUrlChange(e) {
    const value = e.detail.value
    this.setData({ apiBaseUrl: value })
  },

  // 保存 API 地址
  onSaveApiUrl() {
    app.globalData.apiBaseUrl = this.data.apiBaseUrl
    wx.setStorageSync('apiBaseUrl', this.data.apiBaseUrl)
    wx.showToast({ title: '已保存', icon: 'success' })
  },

  // 保存设置到全局
  saveSettings() {
    app.saveSettings({
      lineSpacingSigma: this.data.lineSpacingSigma,
      fontSizeSigma: this.data.fontSizeSigma,
      wordSpacingSigma: this.data.wordSpacingSigma,
      perturbXSigma: this.data.perturbXSigma,
      perturbYSigma: this.data.perturbYSigma,
      perturbThetaSigma: this.data.perturbThetaSigma,
      strikethroughProbability: this.data.strikethroughProbability,
      strikethroughLengthSigma: this.data.strikethroughLengthSigma,
      strikethroughWidthSigma: this.data.strikethroughWidthSigma,
      strikethroughAngleSigma: this.data.strikethroughAngleSigma,
      strikethroughWidth: this.data.strikethroughWidth,
      inkDepthSigma: this.data.inkDepthSigma
    })
  },

  // 重置为默认值
  onResetDefaults() {
    wx.showModal({
      title: '重置设置',
      content: '确定要恢复所有设置为默认值吗？',
      success: (res) => {
        if (res.confirm) {
          this.setData({
            lineSpacingSigma: 5,
            fontSizeSigma: 2,
            wordSpacingSigma: 3,
            perturbXSigma: 3,
            perturbYSigma: 3,
            perturbThetaSigma: 0.01,
            strikethroughProbability: 0,
            strikethroughLengthSigma: 10,
            strikethroughWidthSigma: 2,
            strikethroughAngleSigma: 0.05,
            strikethroughWidth: 3,
            inkDepthSigma: 0
          })
          this.saveSettings()
          wx.showToast({ title: '已重置', icon: 'success' })
        }
      }
    })
  }
})
