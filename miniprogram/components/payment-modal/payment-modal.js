const app = getApp()

Component({
  properties: {
    show: {
      type: Boolean,
      value: false
    },
    charCount: {
      type: Number,
      value: 0
    }
  },

  data: {
    isLoggedIn: false,
    isVip: false,
    daysRemaining: 0,
    // freeCharLimit removed — no client-side limit enforced
    packages: [],
    selectedPackageId: null,
    loading: false
  },

  observers: {
    'show': function(show) {
      if (show) {
        this.loadUserInfo()
        this.loadPackages()
      }
    }
  },

  methods: {
    // 阻止滑动穿透
    preventTouchMove() {
      return false
    },

    // 加载用户信息
    loadUserInfo() {
      const userInfo = app.globalData.userInfo
      this.setData({
        isLoggedIn: userInfo.isLoggedIn,
        daysRemaining: userInfo.daysRemaining
      })
    },

    // 加载套餐列表
    async loadPackages() {
      try {
        const data = await app.getPackages()
        this.setData({
          packages: data.packages
        })
      } catch (e) {
        console.error('加载套餐失败:', e)
      }
    },

    // 关闭弹窗
    onClose() {
      this.setData({ selectedPackageId: null })
      this.triggerEvent('close')
    },

    // 选择免费试用（不再提示或限制字数）
    onSelectFree() {
      this.triggerEvent('selectFree', { 
        useFreeMode: true
      })
    },

    // 选择套餐
    onSelectPackage(e) {
      const id = e.currentTarget.dataset.id
      this.setData({ selectedPackageId: id })
    },

    // 支付
    async onPay() {
      // Purchasing has been disabled
      wx.showModal({
        title: '购买已禁用',
        content: '购买会员功能已被移除，无法进行支付。',
        showCancel: false
      })
    }
  }
})
