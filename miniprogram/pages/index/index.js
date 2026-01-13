// pages/index/index.js
const api = require('../../utils/api')
const util = require('../../utils/util')

const app = getApp()

Page({
  data: {
    // 输入文本
    text: `                        《东风破》
                        词：方文山 曲：周杰伦

一盏离愁孤灯伫立在窗口，我在门后假装你人还没走，旧地如重游月圆更寂寞，夜半清醒的烛火不忍苛责我。一壶漂泊浪迹天涯难入喉，你走之后酒暖回忆思念瘦，水向东流时间怎么偷，花开就一次成熟我却错过。谁在用琵琶弹奏一曲东风破，岁月在墙上剥落看见小时候，犹记得那年我们都还很年幼，而如今琴声幽幽我的等候你没听过。谁在用琵琶弹奏一曲东风破，枫叶将故事染色结局我看透，篱笆外的古道我牵着你走过，荒烟蔓草的年头就连分手都很沉默。

一壶漂泊浪迹天涯难入喉，你走之后酒暖回忆思念瘦，水向东流时间怎么偷，花开就一次成熟我却错过。谁在用琵琶弹奏一曲东风破，岁月在墙上剥落看见小时候，犹记得那年我们都还很年幼，而如今琴声幽幽我的等候你没听过。谁在用琵琶弹奏一曲东风破，枫叶将故事染色结局我看透，篱笆外的古道我牵着你走过，荒烟蔓草的年头就连分手都很沉默。

谁在用琵琶弹奏一曲东风破，岁月在墙上剥落看见小时候，犹记得那年我们都还很年幼，而如今琴声幽幽我的等候你没听过。谁在用琵琶弹奏一曲东风破，枫叶将故事染色结局我看透，篱笆外的古道我牵着你走过，荒烟蔓草的年头就连分手都很沉默。`,
    textLength: 0,
    isDefaultText: true,  // 标记是否为默认文本
    
    // 用户状态
    showLoginModal: false,
    isLoggedIn: false,
    isVip: false,
    userInfo: {},
    pendingAction: null,  // 'preview', 'generate', 'generatePDF'
    
    // 相思豆弹窗
    showLoveseedModal: false,
    currentActionType: '',  // 'generate' 或 'generatePDF'
    
    // 字体相关
    fonts: [],
    fontIndex: 0,
    customFontPath: '',
    customFontName: '',
    
    // 背景相关
    useCustomBackground: false,
    backgroundPath: '',
    
    // 基础参数
    fontSize: 90,
    lineSpacing: 120,
    wordSpacing: 10,
    
    // 边距
    marginTop: 150,
    marginBottom: 150,
    marginLeft: 150,
    marginRight: 150,
    
    // 纸张规格
    paperSizes: ['A4', 'A3', 'A5', 'B4', 'B5', 'Letter'],
    paperSizeIndex: 0,  // 默认 A4
    width: 2480,
    height: 3508,
    
    // 纸张类型
    paperTypes: ['红色信纸', '绿色信纸', '蓝色信纸', '方格信纸', '纯白纸', '上传背景图片'],
    paperTypeIndex: 0,  // 默认红色信纸
    isUnderlined: true,  // 根据纸张类型自动设置
    lineColor: 'red',  // 横线颜色
    paperType: 'lined',  // 纸张类型: plain, lined, grid
    
    // 预览图片
    previewImage: '',
    previewImages: [],  // 多页预览图片数组
    currentPreviewPage: 0,  // 当前预览页码
    totalPreviewPages: 0,  // 总页数
    
    // 全屏预览弹窗
    showPreviewModal: false,
    
    // 加载状态
    loading: false,
    loadingText: ''
  },

  onLoad() {
    this.loadFonts()
    this.loadSettings()
    this.checkUserStatus()
    
    // 计算默认文本的字数
    const defaultText = this.data.text
    this.setData({
      textLength: defaultText.length
    })
    
    // 检查是否需要显示登录提示
    setTimeout(() => {
      if (app.globalData.showLoginPrompt && !app.globalData.userInfo.isLoggedIn) {
        this.setData({ showLoginModal: true })
        app.globalData.showLoginPrompt = false
      }
    }, 500)
  },

  onShow() {
    // 从设置页返回时刷新设置
    this.loadSettings()
    this.checkUserStatus()
  },

  // 检查用户状态
  checkUserStatus() {
    const userInfo = app.globalData.userInfo
    this.setData({
      isLoggedIn: userInfo.isLoggedIn,
      userInfo: userInfo
    })
  },

  // 加载字体列表
  async loadFonts() {
    try {
      const fonts = await api.getFonts()
      app.globalData.fonts = fonts
      
      const fontNames = fonts.map(f => f.name)
      fontNames.unshift('请选择字体')
      
      this.setData({ fonts: fontNames })
      
      // 默认选择司马彦硬笔手写体
      const defaultIndex = fonts.findIndex(f => f.filename.includes('司马彦'))
      if (defaultIndex >= 0) {
        this.setData({ fontIndex: defaultIndex + 1 })
        // 保存到全局设置
        app.globalData.settings.selectedFont = fonts[defaultIndex].filename
      }
    } catch (err) {
      console.error('加载字体失败:', err)
      wx.showToast({ title: '加载字体失败', icon: 'none' })
    }
  },

  // 加载保存的设置
  loadSettings() {
    const settings = app.globalData.settings
    this.setData({
      fontSize: settings.fontSize,
      lineSpacing: settings.lineSpacing,
      wordSpacing: settings.wordSpacing,
      marginTop: settings.marginTop,
      marginBottom: settings.marginBottom,
      marginLeft: settings.marginLeft,
      marginRight: settings.marginRight,
      width: settings.width,
      height: settings.height,
      isUnderlined: settings.isUnderlined
    })
  },

  // 文本输入变化
  onTextInput(e) {
    const text = e.detail.value
    const { isDefaultText } = this.data
    
    // 如果是默认文本，用户开始输入时清空
    if (isDefaultText && text.length > 0) {
      this.setData({
        text: text,
        textLength: text.length,
        isDefaultText: false
      })
    } else {
      this.setData({
        text: text,
        textLength: text.length
      })
    }
  },

  // 选择字体
  onFontChange(e) {
    const index = parseInt(e.detail.value)
    this.setData({ fontIndex: index })
    
    if (index > 0) {
      const font = app.globalData.fonts[index - 1]
      app.saveSettings({ selectedFont: font.filename })
    }
  },

  // 上传自定义字体
  onUploadFont() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['ttf', 'TTF'],
      success: (res) => {
        const file = res.tempFiles[0]
        this.setData({
          customFontPath: file.path,
          customFontName: file.name,
          fontIndex: 0
        })
        wx.showToast({ title: '字体已选择', icon: 'success' })
      }
    })
  },

  // 上传背景图片 - 显示选择方式
  onUploadBackground() {
    wx.showActionSheet({
      itemList: ['从相册选择', '拍照', '从微信聊天记录选择'],
      success: (res) => {
        if (res.tapIndex === 0) {
          // 从相册选择
          this.uploadBackgroundFromAlbum()
        } else if (res.tapIndex === 1) {
          // 拍照
          this.uploadBackgroundFromCamera()
        } else if (res.tapIndex === 2) {
          // 从微信聊天记录选择
          this.uploadBackgroundFromChat()
        }
      }
    })
  },

  // 从相册选择背景图
  uploadBackgroundFromAlbum() {
    wx.chooseImage({
      count: 1,
      sizeType: ['original'],
      sourceType: ['album'],
      success: (res) => {
        this.setData({
          backgroundPath: res.tempFilePaths[0],
          useCustomBackground: true
        })
        wx.showToast({ title: '背景已选择', icon: 'success' })
      }
    })
  },

  // 拍照选择背景图
  uploadBackgroundFromCamera() {
    wx.chooseImage({
      count: 1,
      sizeType: ['original'],
      sourceType: ['camera'],
      success: (res) => {
        this.setData({
          backgroundPath: res.tempFilePaths[0],
          useCustomBackground: true
        })
        wx.showToast({ title: '背景已选择', icon: 'success' })
      }
    })
  },

  // 从微信聊天记录选择背景图
  uploadBackgroundFromChat() {
    wx.chooseMessageFile({
      count: 1,
      type: 'image',
      success: (res) => {
        this.setData({
          backgroundPath: res.tempFiles[0].path,
          useCustomBackground: true
        })
        wx.showToast({ title: '背景已选择', icon: 'success' })
      }
    })
  },

  // 清除背景图片
  onClearBackground() {
    this.setData({
      backgroundPath: '',
      useCustomBackground: false
    })
  },

  // 上传文档 - 显示选择方式
  onUploadDocument() {
    wx.showActionSheet({
      itemList: ['从设备选择文件', '从微信聊天记录选择'],
      success: (res) => {
        if (res.tapIndex === 0) {
          // 从设备选择
          this.uploadDocumentFromDevice()
        } else if (res.tapIndex === 1) {
          // 从微信聊天记录选择
          this.uploadDocumentFromChat()
        }
      }
    })
  },

  // 从设备选择文档
  uploadDocumentFromDevice() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['doc', 'docx', 'pdf', 'txt'],
      success: async (res) => {
        const file = res.tempFiles[0]
        await this.parseUploadedDocument(file)
      }
    })
  },

  // 从微信聊天记录选择文档
  uploadDocumentFromChat() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['doc', 'docx', 'pdf', 'txt'],
      success: async (res) => {
        const file = res.tempFiles[0]
        await this.parseUploadedDocument(file)
      }
    })
  },

  // 解析上传的文档
  async parseUploadedDocument(file) {
    this.setData({ loading: true, loadingText: '解析文档中...' })
    
    try {
      const text = await api.parseDocument(file.path)
      this.setData({
        text: text,
        textLength: text.length,
        isDefaultText: false  // 上传文档后不是默认文本
      })
      wx.showToast({ title: '解析成功', icon: 'success' })
    } catch (err) {
      wx.showToast({ title: err.message || '解析失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  // 参数滑块变化
  onFontSizeChange(e) {
    this.setData({ fontSize: e.detail.value })
  },

  onLineSpacingChange(e) {
    this.setData({ lineSpacing: e.detail.value })
  },

  onWordSpacingChange(e) {
    this.setData({ wordSpacing: e.detail.value })
  },

  // 边距输入变化
  onMarginTopChange(e) {
    this.setData({ marginTop: parseInt(e.detail.value) || 0 })
  },

  onMarginBottomChange(e) {
    this.setData({ marginBottom: parseInt(e.detail.value) || 0 })
  },

  onMarginLeftChange(e) {
    this.setData({ marginLeft: parseInt(e.detail.value) || 0 })
  },

  onMarginRightChange(e) {
    this.setData({ marginRight: parseInt(e.detail.value) || 0 })
  },

  // 尺寸变化
  onWidthChange(e) {
    this.setData({ width: parseInt(e.detail.value) || 2480 })
  },

  onHeightChange(e) {
    this.setData({ height: parseInt(e.detail.value) || 3508 })
  },

  // 纸张规格切换
  onPaperSizeChange(e) {
    const index = parseInt(e.detail.value)
    // 纸张规格对应的尺寸（300DPI）
    const paperDimensions = {
      'A4': { width: 2480, height: 3508 },
      'A3': { width: 3508, height: 4961 },
      'A5': { width: 1748, height: 2480 },
      'B4': { width: 2953, height: 4169 },
      'B5': { width: 2079, height: 2953 },
      'Letter': { width: 2550, height: 3300 }
    }
    const paperName = this.data.paperSizes[index]
    const dimensions = paperDimensions[paperName]
    
    this.setData({ 
      paperSizeIndex: index,
      width: dimensions.width,
      height: dimensions.height
    })
  },

  // 纸张类型变更
  onPaperTypeChange(e) {
    const index = parseInt(e.detail.value)
    // 纯白纸(0), 红色信纸(1), 绿色信纸(2), 方格信纸(3), 上传背景图片(4)
    let isUnderlined = false
    let lineColor = 'red'
    let paperType = 'plain'
    
    switch (index) {
      case 0:  // 红色信纸
        isUnderlined = true
        lineColor = 'red'
        paperType = 'lined'
        break
      case 1:  // 绿色信纸
        isUnderlined = true
        lineColor = 'green'
        paperType = 'lined'
        break
      case 2:  // 蓝色信纸
        isUnderlined = true
        lineColor = 'blue'
        paperType = 'lined'
        break
      case 3:  // 方格信纸
        paperType = 'grid'
        break
      case 4:  // 纯白纸
        paperType = 'plain'
        break
      case 5:  // 上传背景图片
        // 弹出选择方式
        wx.showActionSheet({
          itemList: ['从相册选择', '拍照', '从微信聊天记录选择'],
          success: (actionRes) => {
            if (actionRes.tapIndex === 0) {
              // 从相册选择
              wx.chooseImage({
                count: 1,
                sizeType: ['original'],
                sourceType: ['album'],
                success: (res) => {
                  this.setData({
                    backgroundPath: res.tempFilePaths[0],
                    useCustomBackground: true,
                    paperTypeIndex: index
                  })
                  wx.showToast({ title: '背景图片已上传', icon: 'success' })
                }
              })
            } else if (actionRes.tapIndex === 1) {
              // 拍照
              wx.chooseImage({
                count: 1,
                sizeType: ['original'],
                sourceType: ['camera'],
                success: (res) => {
                  this.setData({
                    backgroundPath: res.tempFilePaths[0],
                    useCustomBackground: true,
                    paperTypeIndex: index
                  })
                  wx.showToast({ title: '背景图片已上传', icon: 'success' })
                }
              })
            } else if (actionRes.tapIndex === 2) {
              // 从微信聊天记录选择
              wx.chooseMessageFile({
                count: 1,
                type: 'image',
                success: (res) => {
                  this.setData({
                    backgroundPath: res.tempFiles[0].path,
                    useCustomBackground: true,
                    paperTypeIndex: index
                  })
                  wx.showToast({ title: '背景图片已上传', icon: 'success' })
                }
              })
            }
          }
        })
        return  // 直接返回，不执行后面的 setData
    }
    
    // 非上传背景图片模式时，清除自定义背景
    this.setData({ 
      paperTypeIndex: index,
      isUnderlined: isUnderlined,
      lineColor: lineColor,
      paperType: paperType,
      useCustomBackground: false,
      backgroundPath: ''
    })
  },

  // 预览前检查
  onPreviewCheck() {
    if (!this.validateInput()) return
    // 取消付费弹窗逻辑：所有用户均可直接预览（非VIP仍可生成，带水印）
    this.doPreview(false)
  },

  // 预览
  async onPreview() {
    this.onPreviewCheck()
  },

  // 实际执行预览
  async doPreview(useFreeMode) {
    if (!this.validateInput()) return
    
    this.setData({ loading: true, loadingText: '生成预览中...' })
    
    try {
      const params = this.buildParams()
      params.useFreeMode = useFreeMode
      params.openid = app.globalData.userInfo.openid || ''
      
      const fontPath = this.data.customFontPath || null
      const bgPath = this.data.useCustomBackground ? this.data.backgroundPath : null
      
      const result = await api.preview(params, fontPath, bgPath)
      
      // 支持多页预览
      const images = result.images || [result.image]
      this.setData({ 
        previewImages: images,
        previewImage: images[0],  // 第一页用于小预览
        currentPreviewPage: 0,
        totalPreviewPages: images.length,
        showPreviewModal: true
      })
      
      // 不再提示水印，后端已移除水印渲染
    } catch (err) {
      wx.showToast({ title: err.message || '预览失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  // 关闭全屏预览弹窗
  onClosePreviewModal() {
    this.setData({ showPreviewModal: false })
  },

  // 点击预览区域打开全屏预览
  onOpenPreviewModal() {
    if (this.data.previewImages.length > 0) {
      this.setData({ showPreviewModal: true })
    }
  },

  // swiper 页面切换
  onPreviewPageChange(e) {
    this.setData({ currentPreviewPage: e.detail.current })
  },

  // 上一页
  onPrevPage() {
    if (this.data.currentPreviewPage > 0) {
      this.setData({ currentPreviewPage: this.data.currentPreviewPage - 1 })
    }
  },

  // 下一页
  onNextPage() {
    if (this.data.currentPreviewPage < this.data.totalPreviewPages - 1) {
      this.setData({ currentPreviewPage: this.data.currentPreviewPage + 1 })
    }
  },

  // 生成图片前检查
  onGenerateCheck() {
    if (!this.validateInput()) return
    // 新逻辑：提示用户输入相思豆
    this.showLoveseedInput('generate')
  },

  // 生成图片
  async onGenerate() {
    this.onGenerateCheck()
  },

  // 实际执行生成图片
  async doGenerate(useFreeMode) {
    if (!this.validateInput()) return
    
    const confirmed = await util.showConfirm('生成图片', '将生成完整的手写图片并保存到相册，是否继续？')
    if (!confirmed) return
    
    this.setData({ loading: true, loadingText: '生成图片中...' })
    
    try {
      const params = this.buildParams()
      params.useFreeMode = useFreeMode
      params.openid = app.globalData.userInfo.openid || ''
      
      const fontPath = this.data.customFontPath || null
      const bgPath = this.data.useCustomBackground ? this.data.backgroundPath : null
      
      const result = await api.generate(params, false, fontPath, bgPath)
      
      // 保存所有图片到相册
      const images = result.images || []
      const totalCount = images.length
      let savedCount = 0
      let failedCount = 0
      
      this.setData({ loadingText: `保存图片中 (0/${totalCount})...` })
      
      for (let i = 0; i < images.length; i++) {
        try {
          // 将 base64 转换为临时文件
          const base64Data = images[i].replace(/^data:image\/\w+;base64,/, '')
          const filePath = `${wx.env.USER_DATA_PATH}/temp_image_${i}.png`
          const fs = wx.getFileSystemManager()
          fs.writeFileSync(filePath, base64Data, 'base64')
          
          // 保存到相册
          await new Promise((resolve, reject) => {
            wx.saveImageToPhotosAlbum({
              filePath: filePath,
              success: () => {
                savedCount++
                this.setData({ loadingText: `保存图片中 (${savedCount}/${totalCount})...` })
                resolve()
              },
              fail: (err) => {
                failedCount++
                reject(err)
              }
            })
          })
          
          // 删除临时文件
          fs.unlinkSync(filePath)
        } catch (err) {
          console.error('保存图片失败:', err)
        }
      }
      
      if (savedCount > 0) {
        wx.showModal({
          title: '保存成功',
          content: `已保存 ${savedCount} 张图片到相册${failedCount > 0 ? `，${failedCount} 张失败` : ''}`,
          showCancel: false
        })
      } else {
        wx.showToast({ title: '保存失败，请授权相册权限', icon: 'none' })
      }
    } catch (err) {
      wx.showToast({ title: err.message || '生成失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  // 生成PDF前检查
  onGeneratePDFCheck() {
    if (!this.validateInput()) return
    // 新逻辑：提示用户输入相思豆
    this.showLoveseedInput('generatePDF')
  },

  // 生成 PDF
  async onGeneratePDF() {
    this.onGeneratePDFCheck()
  },

  // 实际执行生成PDF
  async doGeneratePDF(useFreeMode) {
    if (!this.validateInput()) return
    
    const confirmed = await util.showConfirm('生成PDF', '将生成包含所有页的 PDF 文件，是否继续？')
    if (!confirmed) return
    
    this.setData({ loading: true, loadingText: '生成PDF中...' })
    
    try {
      const params = this.buildParams()
      params.useFreeMode = useFreeMode
      params.openid = app.globalData.userInfo.openid || ''
      
      const fontPath = this.data.customFontPath || null
      const bgPath = this.data.useCustomBackground ? this.data.backgroundPath : null
      
      const result = await api.generate(params, true, fontPath, bgPath)
      
      // 下载 PDF 文件
      this.setData({ loadingText: '下载PDF中...' })
      const filePath = await api.downloadFile(result.file_id)
      
      // 直接打开 PDF 预览，右上角菜单可以保存或分享
      wx.openDocument({
        filePath: filePath,
        fileType: 'pdf',
        showMenu: true,
        success: () => {
          wx.showToast({ 
            title: `PDF已生成(${result.page_count}页)`, 
            icon: 'success' 
          })
        },
        fail: () => {
          wx.showToast({ title: '无法打开PDF', icon: 'none' })
        }
      })
    } catch (err) {
      wx.showToast({ title: err.message || '生成失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  // 预览图片点击（放大查看）
  onPreviewImageTap() {
    if (this.data.previewImage) {
      wx.previewImage({
        urls: [this.data.previewImage],
        current: this.data.previewImage
      })
    }
  },

  // 验证输入
  validateInput() {
    if (!this.data.text.trim()) {
      wx.showToast({ title: '请输入文字内容', icon: 'none' })
      return false
    }
    
    if (this.data.fontIndex === 0 && !this.data.customFontPath) {
      wx.showToast({ title: '请选择字体', icon: 'none' })
      return false
    }
    
    return true
  },

  // 构建参数
  buildParams() {
    const settings = app.globalData.settings
    let fontOption = ''
    
    if (this.data.fontIndex > 0) {
      fontOption = app.globalData.fonts[this.data.fontIndex - 1].filename
    }
    
    return {
      text: this.data.text,
      fontSize: this.data.fontSize,
      lineSpacing: this.data.lineSpacing,
      wordSpacing: this.data.wordSpacing,
      marginTop: this.data.marginTop,
      marginBottom: this.data.marginBottom,
      marginLeft: this.data.marginLeft,
      marginRight: this.data.marginRight,
      width: this.data.useCustomBackground ? undefined : this.data.width,
      height: this.data.useCustomBackground ? undefined : this.data.height,
      useCustomBackground: this.data.useCustomBackground,
      isUnderlined: this.data.isUnderlined,
      lineColor: this.data.lineColor,
      paperType: this.data.paperType,
      fontOption: fontOption,
      // 高级参数使用全局设置
      fill: settings.fill,
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
      inkDepthSigma: settings.inkDepthSigma
    }
  },

  // 清空内容
  onClear() {
    // 真正清空内容，方便用户输入自己的文本
    this.setData({
      text: '',
      textLength: 0,
      previewImage: '',
      isDefaultText: false  // 标记为非默认文本
    })
    wx.showToast({ title: '已清空', icon: 'success' })
  },

  // ==================== 登录弹窗事件 ====================
  
  onLoginModalClose() {
    this.setData({ showLoginModal: false })
  },

  onLoginModalSkip() {
    this.setData({ showLoginModal: false })
  },

  onLoginModalSuccess(e) {
    this.setData({ 
      showLoginModal: false,
      isLoggedIn: true
    })
  },

  // ==================== 付费弹窗事件 ====================
  
  onPaymentModalClose() {
    // payment modal removed
    this.setData({ pendingAction: '' })
  },

  onPaymentSelectFree(e) {
    this.setData({})
    // 用户选择后也不需要 special free mode — just execute pending action normally
    const action = this.data.pendingAction
    if (action === 'preview') {
      this.doPreview(false)
    } else if (action === 'generate') {
      this.doGenerate(false)
    } else if (action === 'generatePDF') {
      this.doGeneratePDF(false)
    }
    this.setData({ pendingAction: '' })
  },

  onPaymentNeedLogin() {
    this.setData({ showLoginModal: true })
  },

  onPaymentSuccess() {
    // 支付成功后刷新用户状态
    this.checkUserStatus()
    
    // 然后执行待执行的操作（作为VIP）
    const action = this.data.pendingAction
    if (action === 'preview') {
      this.doPreview(false)
    } else if (action === 'generate') {
      this.doGenerate(false)
    } else if (action === 'generatePDF') {
      this.doGeneratePDF(false)
    }
    
    this.setData({ pendingAction: '' })
  },

  // ==================== 相思豆功能 ====================

  // 显示相思豆输入框
  showLoveseedInput(actionType) {
    // 使用自定义弹窗
    this.setData({
      showLoveseedModal: true,
      currentActionType: actionType
    })
  },

  // 相思豆弹窗关闭
  onLoveseedModalClose() {
    this.setData({
      showLoveseedModal: false,
      currentActionType: ''
    })
  },

  // 相思豆确认
  async onLoveseedConfirm(e) {
    const { code, actionType } = e.detail
    
    // 关闭弹窗
    this.setData({ showLoveseedModal: false })
    
    // 验证并执行
    await this.verifyAndExecute(code, actionType)
  },

  // 获取相思豆（跳转到购买页面）
  onGetLoveseed() {
    this.openPaymentPage()
  },

  // 打开支付页面（引导用户在浏览器中打开）
  openPaymentPage() {
    // 从全局配置获取测试模式设置
    const LOCAL_TEST_MODE = app.globalData.LOCAL_TEST_MODE;
    const SERVER_IP = app.globalData.SERVER_IP;
    
    // 根据模式选择支付页面地址
    const paymentUrl = LOCAL_TEST_MODE 
      ? 'http://127.0.0.1:2345/payment/index.html'  // 本地测试地址
      : `http://${SERVER_IP}:2345/payment/index.html`;  // 服务器地址 
    
    // 微信小程序无法直接启动外部浏览器，采用优化方案：复制链接并引导
    wx.setClipboardData({
      data: paymentUrl,
      success: () => {
        wx.showModal({
          title: '🫘 获取相思豆',
          content: '链接已复制到剪贴板！\n\n请打开手机浏览器，粘贴链接即可获取相思豆。',
          confirmText: '知道了',
          showCancel: false,
          success: () => {
            // 显示引导提示
            wx.showToast({
              title: '请在浏览器中打开',
              icon: 'none',
              duration: 2000
            })
          }
        })
      },
      fail: () => {
        wx.showToast({
          title: '复制失败，请重试',
          icon: 'none'
        })
      }
    })
  },

  // 验证相思豆并执行操作
  async verifyAndExecute(loveseedCode, actionType) {
    try {
      // 验证格式
      if (loveseedCode.length !== 6 || !/^\d{6}$/.test(loveseedCode)) {
        wx.showToast({ title: '相思豆格式不正确，应为6位数字', icon: 'none', duration: 2000 })
        return
      }

      wx.showLoading({ title: '验证中...' })

      // 调用后端验证 API
      const res = await api.verifyLoveseedCode(loveseedCode)
      wx.hideLoading()

      if (res.valid) {
        const data = res.data
        const billingType = data.billing_type || 'count'
        
        let content = ''
        if (billingType === 'duration') {
          // 按时间套餐：显示到期时间
          const expireTime = data.expire_time
          if (expireTime) {
            // 计算剩余天数
            const expireDate = new Date(expireTime)
            const now = new Date()
            const remainingDays = Math.ceil((expireDate - now) / (1000 * 60 * 60 * 24))
            content = `有效期剩余${remainingDays}天（至${expireTime.split(' ')[0]}）\n是否继续生成？`
          } else {
            content = '有效期内无限次使用，是否继续生成？'
          }
        } else {
          // 按次数套餐：显示剩余次数
          const remaining = data.remaining_downloads
          content = `剩余${remaining}次下载机会，是否继续生成？`
        }
        
        wx.showModal({
          title: '相思豆有效',
          content: content,
          confirmText: '继续',
          cancelText: '取消',
          success: async (modalRes) => {
            if (modalRes.confirm) {
              // 执行生成操作，并消耗下载次数
              if (actionType === 'generate') {
                await this.doGenerateWithLoveseed(loveseedCode)
              } else if (actionType === 'generatePDF') {
                await this.doGeneratePDFWithLoveseed(loveseedCode)
              }
            }
          }
        })
      } else {
        wx.showToast({ title: '相思豆无效或已用尽', icon: 'none', duration: 2000 })
      }
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: err.message || '验证失败', icon: 'none', duration: 2000 })
    }
  },

  // 使用相思豆生成图片
  async doGenerateWithLoveseed(loveseedCode) {
    if (!this.validateInput()) return

    this.setData({ loading: true, loadingText: '生成图片中...' })

    try {
      const params = this.buildParams()
      params.openid = app.globalData.userInfo.openid || ''
      params.loveseedCode = loveseedCode

      const fontPath = this.data.customFontPath || null
      const bgPath = this.data.useCustomBackground ? this.data.backgroundPath : null

      // 调用生成 API，后端会自动消耗相思豆
      const result = await api.generateWithLoveseed(params, false, fontPath, bgPath)

      // 保存所有图片到相册
      const images = result.images || []
      const totalCount = images.length
      let savedCount = 0
      let failedCount = 0

      this.setData({ loadingText: `保存图片中 (0/${totalCount})...` })

      for (let i = 0; i < images.length; i++) {
        try {
          // 将 base64 转换为临时文件
          const base64Data = images[i].replace(/^data:image\/\w+;base64,/, '')
          const filePath = `${wx.env.USER_DATA_PATH}/temp_image_${i}.png`
          const fs = wx.getFileSystemManager()
          fs.writeFileSync(filePath, base64Data, 'base64')

          // 保存到相册
          await new Promise((resolve, reject) => {
            wx.saveImageToPhotosAlbum({
              filePath: filePath,
              success: () => {
                savedCount++
                this.setData({ loadingText: `保存图片中 (${savedCount}/${totalCount})...` })
                resolve()
              },
              fail: (err) => {
                failedCount++
                reject(err)
              }
            })
          })

          // 删除临时文件
          fs.unlinkSync(filePath)
        } catch (err) {
          console.error('保存图片失败:', err)
        }
      }

      if (savedCount > 0) {
        // 根据 billing_type 显示不同的提示
        const billingType = result.billing_type || 'count'
        let remainingInfo = ''
        
        if (billingType === 'duration') {
          // 按时间套餐：显示到期时间
          const expireTime = result.expire_time
          if (expireTime) {
            const expireDate = new Date(expireTime)
            const now = new Date()
            const remainingDays = Math.ceil((expireDate - now) / (1000 * 60 * 60 * 24))
            remainingInfo = `有效期剩余：${remainingDays}天（至${expireTime.split(' ')[0]}）`
          } else {
            remainingInfo = '有效期内无限次使用'
          }
        } else {
          // 按次数套餐：显示剩余次数
          remainingInfo = `剩余下载次数：${result.remaining_downloads || 0} 次`
        }
        
        wx.showModal({
          title: '生成成功',
          content: `已保存 ${savedCount} 张图片到相册${failedCount > 0 ? `，${failedCount} 张失败` : ''}\n\n${remainingInfo}`,
          showCancel: false
        })
      } else {
        wx.showToast({ title: '保存失败，请授权相册权限', icon: 'none' })
      }
    } catch (err) {
      wx.showToast({ title: err.message || '生成失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  // 使用相思豆生成PDF
  async doGeneratePDFWithLoveseed(loveseedCode) {
    if (!this.validateInput()) return

    this.setData({ loading: true, loadingText: '生成PDF中...' })

    try {
      const params = this.buildParams()
      params.openid = app.globalData.userInfo.openid || ''
      params.loveseedCode = loveseedCode

      const fontPath = this.data.customFontPath || null
      const bgPath = this.data.useCustomBackground ? this.data.backgroundPath : null

      // 调用生成 API，后端会自动消耗相思豆
      const result = await api.generateWithLoveseed(params, true, fontPath, bgPath)

      // 下载 PDF 文件
      this.setData({ loadingText: '下载PDF中...' })
      const filePath = await api.downloadFile(result.file_id)

      // 直接打开 PDF 预览，右上角菜单可以保存或分享
      wx.openDocument({
        filePath: filePath,
        fileType: 'pdf',
        showMenu: true,
        success: () => {
          // 根据 billing_type 显示不同的提示
          const billingType = result.billing_type || 'count'
          let remainingInfo = ''
          
          if (billingType === 'duration') {
            // 按时间套餐：显示到期时间
            const expireTime = result.expire_time
            if (expireTime) {
              const expireDate = new Date(expireTime)
              const now = new Date()
              const remainingDays = Math.ceil((expireDate - now) / (1000 * 60 * 60 * 24))
              remainingInfo = `有效期剩余：${remainingDays}天（至${expireTime.split(' ')[0]}）`
            } else {
              remainingInfo = '有效期内无限次使用'
            }
          } else {
            // 按次数套餐：显示剩余次数
            remainingInfo = `剩余下载次数：${result.remaining_downloads || 0} 次`
          }
          
          wx.showModal({
            title: '生成成功',
            content: `PDF已生成(${result.page_count}页)\n\n${remainingInfo}`,
            showCancel: false
          })
        },
        fail: () => {
          wx.showToast({ title: '无法打开PDF', icon: 'none' })
        }
      })
    } catch (err) {
      wx.showToast({ title: err.message || '生成失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  }
})
