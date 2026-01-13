const app = getApp()

Component({
  properties: {
    show: {
      type: Boolean,
      value: false
    }
  },

  data: {
    loading: false
  },

  methods: {
    // 阻止滑动穿透
    preventTouchMove() {
      return false
    },

    // 关闭弹窗
    onClose() {
      this.triggerEvent('close')
    },

    // 跳过登录
    onSkip() {
      this.triggerEvent('skip')
    },

    // 微信登录
    async onLogin() {
      if (this.data.loading) return
      
      this.setData({ loading: true })
      
      try {
        const userInfo = await app.wxLogin()
        wx.showToast({
          title: '登录成功',
          icon: 'success'
        })
        this.triggerEvent('success', { userInfo })
      } catch (error) {
        wx.showToast({
          title: error.message || '登录失败',
          icon: 'none'
        })
      } finally {
        this.setData({ loading: false })
      }
    }
  }
})
