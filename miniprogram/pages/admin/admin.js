Page({
  onLoad() {
    wx.showModal({
      title: '页面已移除',
      content: '管理页面已被移除',
      showCancel: false,
      success() {
        wx.navigateBack()
      }
    })
  }
})
