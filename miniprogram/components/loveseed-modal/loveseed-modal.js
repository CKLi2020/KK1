// components/loveseed-modal/loveseed-modal.js
Component({
  properties: {
    show: {
      type: Boolean,
      value: false
    },
    actionType: {
      type: String,
      value: ''
    }
  },

  data: {
    inputValue: ''
  },

  methods: {
    // 防止遮罩层滚动穿透
    preventMove() {},

    // 输入改变
    onInput(e) {
      const value = e.detail.value
      // 只允许输入数字，最多6位
      const filtered = value.replace(/[^\d]/g, '').slice(0, 6)
      this.setData({ inputValue: filtered })
    },

    // 确认使用相思豆
    onConfirm() {
      const code = this.data.inputValue.trim()
      
      if (!code) {
        wx.showToast({
          title: '请输入相思豆',
          icon: 'none'
        })
        return
      }

      if (code.length !== 6) {
        wx.showToast({
          title: '相思豆应为6位数字',
          icon: 'none'
        })
        return
      }

      // 触发确认事件
      this.triggerEvent('confirm', {
        code: code,
        actionType: this.data.actionType
      })

      // 清空输入并关闭
      this.setData({ inputValue: '' })
    },

    // 获取相思豆
    onGetLoveseed() {
      // 触发获取相思豆事件
      this.triggerEvent('getloveseed')
      
      // 关闭弹窗
      this.onClose()
    },

    // 关闭弹窗
    onClose() {
      this.setData({ inputValue: '' })
      this.triggerEvent('close')
    }
  }
})
