// app.js
App({
  onLaunch() {
    try {
    // 初始化云开发（如需要）
    // wx.cloud.init({ env: 'your-env-id' })
    
    // 加载保存的设置
    this.loadSettings()
    
    // 加载用户登录状态
    this.loadUserInfo()
    
    // 延迟显示登录提示弹窗（让页面先加载完成）
    setTimeout(() => {
      if (!this.globalData.userInfo.isLoggedIn) {
        this.globalData.showLoginPrompt = true
      }
    }, 1000)
    } catch (e) {
      // 记录启动期错误，便于在微信开发者工具中查看
      try {
        const errInfo = (e && e.stack) ? e.stack : String(e)
        wx.setStorageSync('lastStartupError', errInfo)
        console.error('启动期捕获异常:', errInfo)
      } catch (ee) {
        console.error('记录启动错误失败:', ee)
      }
      throw e
    }
  },

  globalData: {
    // 配置：本地测试模式开关
    LOCAL_TEST_MODE: true,  // 本地测试时设为true，部署时设为false
    SERVER_IP: '47.107.148.252',  // 服务器公网地址
    
    // API 服务器地址 - 本地开发时使用
    apiBaseUrl: 'http://localhost:5000',
    
    // 用户信息
      userInfo: {
        isLoggedIn: false,
        openid: '',
        nickname: '',
        avatarUrl: '',
        isAdmin: false,
        memberType: 'guest',
        daysRemaining: 0
      },
    
    // 是否显示登录提示弹窗
    showLoginPrompt: false,
    
    // 默认参数设置
    settings: {
      fontSize: 90,
      lineSpacing: 120,
      wordSpacing: 10,
      marginTop: 150,
      marginBottom: 150,
      marginLeft: 150,
      marginRight: 150,
      width: 2480,
      height: 3508,
      fill: '(0, 0, 0, 255)',
      lineSpacingSigma: 5,
      fontSizeSigma: 2,
      wordSpacingSigma: 3,
      perturbXSigma: 3,
      perturbYSigma: 3,
      perturbThetaSigma: 0.01,
      strikethroughProbability: 0,
      strikethroughLengthSigma: 10,  // 给涂改线一定长度
      strikethroughWidthSigma: 2,    // 线宽扰动
      strikethroughAngleSigma: 0.05, // 角度扰动
      strikethroughWidth: 3,         // 默认线宽
      inkDepthSigma: 0,
      isUnderlined: false,
      selectedFont: ''
    },
    
    // 可用字体列表
    fonts: [],
    
    // 套餐列表
    packages: []
  },

  // 加载保存的设置
  loadSettings() {
    try {
      const savedSettings = wx.getStorageSync('settings')
      if (savedSettings) {
        this.globalData.settings = { ...this.globalData.settings, ...savedSettings }
      }
    } catch (e) {
      console.error('加载设置失败:', e)
    }
  },

  // 保存设置
  saveSettings(settings) {
    try {
      this.globalData.settings = { ...this.globalData.settings, ...settings }
      wx.setStorageSync('settings', this.globalData.settings)
    } catch (e) {
      console.error('保存设置失败:', e)
    }
  },

  // 加载用户登录状态
  loadUserInfo() {
    try {
      const savedUserInfo = wx.getStorageSync('userInfo')
      if (savedUserInfo && savedUserInfo.openid) {
        this.globalData.userInfo = { ...this.globalData.userInfo, ...savedUserInfo }
        // 刷新用户信息（检查会员是否过期等）
        this.refreshUserInfo()
      }
    } catch (e) {
      console.error('加载用户信息失败:', e)
    }
  },

  // 保存用户信息
  saveUserInfo(userInfo) {
    try {
      this.globalData.userInfo = { ...this.globalData.userInfo, ...userInfo }
      wx.setStorageSync('userInfo', this.globalData.userInfo)
    } catch (e) {
      console.error('保存用户信息失败:', e)
    }
  },

  // 刷新用户信息
  refreshUserInfo() {
    const { openid } = this.globalData.userInfo
    if (!openid) return

    wx.request({
      url: `${this.globalData.apiBaseUrl}/api/miniprogram/user/info`,
      method: 'GET',
      header: {
        'X-Openid': openid
      },
      success: (res) => {
        if (res.data.status === 'success' && res.data.data) {
          const data = res.data.data
          this.saveUserInfo({
            isLoggedIn: data.isLoggedIn,
            isVip: data.isVip,
            isAdmin: data.isAdmin || false,
            memberType: data.memberType,
            daysRemaining: data.daysRemaining
          })
        }
      }
    })
  },

  // 微信登录
  wxLogin() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (loginRes) => {
          if (loginRes.code) {
            // 发送 code 到后端换取 openid
            wx.request({
              url: `${this.globalData.apiBaseUrl}/api/miniprogram/login`,
              method: 'POST',
              data: {
                code: loginRes.code
              },
              success: (res) => {
                if (res.data.status === 'success' && res.data.data) {
                  const data = res.data.data
                  this.saveUserInfo({
                    isLoggedIn: true,
                    openid: data.openid,
                    nickname: data.nickname || '',
                    avatarUrl: data.avatarUrl || '',
                    isVip: data.isVip,
                    isAdmin: data.isAdmin || false,
                    memberType: data.memberType,
                    daysRemaining: data.daysRemaining
                  })
                  resolve(this.globalData.userInfo)
                } else {
                  reject(new Error(res.data.message || '登录失败'))
                }
              },
              fail: (err) => {
                reject(new Error('网络请求失败'))
              }
            })
          } else {
            reject(new Error('获取登录凭证失败'))
          }
        },
        fail: (err) => {
          reject(new Error('微信登录失败'))
        }
      })
    })
  },

  // 退出登录
  logout() {
    this.globalData.userInfo = {
      isLoggedIn: false,
      openid: '',
      nickname: '',
      avatarUrl: '',
      isVip: false,
      isAdmin: false,
      memberType: 'guest',
      daysRemaining: 0,
      // freeCharLimit removed
    }
    wx.removeStorageSync('userInfo')
  },

  // 获取套餐列表
  getPackages() {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${this.globalData.apiBaseUrl}/api/miniprogram/packages`,
        method: 'GET',
        success: (res) => {
          if (res.data.status === 'success' && res.data.data) {
            this.globalData.packages = res.data.data.packages
            resolve(res.data.data)
          } else {
            reject(new Error('获取套餐失败'))
          }
        },
        fail: () => {
          reject(new Error('网络请求失败'))
        }
      })
    })
  }
  ,
  // 全局错误处理器：记录错误信息到本地存储，便于开发者工具查看
  onError(err) {
    try {
      const info = (err && err.stack) ? err.stack : String(err)
      wx.setStorageSync('lastStartupError', info)
      console.error('全局捕获异常:', info)
    } catch (e) {
      console.error('记录全局错误失败:', e)
    }
  }
})
