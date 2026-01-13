// pages/about/about.js
Page({
  data: {
    version: '1.0.0',
    features: [
      {
        title: '自定义字体',
        desc: '支持上传自己的 TTF 字体文件，创建独特的手写风格'
      },
      {
        title: '背景图片',
        desc: '上传背景图片，或自动生成带横线的笔记本背景'
      },
      {
        title: '多种参数',
        desc: '调整边距、间距、随机扰动等参数，让效果更自然'
      },
      {
        title: '涂改痕迹',
        desc: '模拟手写时的涂改效果，增加真实感'
      },
      {
        title: '文档解析',
        desc: '支持从 Word、PDF、TXT 文档中提取文字'
      },
      {
        title: 'PDF 导出',
        desc: '一键生成 PDF 文件，方便打印和分享'
      }
    ]
  },

  onLoad() {
    
  },

  // 复制项目地址
  onCopyLink() {
    wx.setClipboardData({
      data: 'https://github.com/14790897/handwriting_web',
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success' })
      }
    })
  },

  // 分享
  onShareAppMessage() {
    return {
      title: '手写文字生成器 - 将文字转为手写效果',
      path: '/pages/index/index'
    }
  }
})
