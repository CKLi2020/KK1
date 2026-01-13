// utils/api.js
// API 请求封装

const app = getApp()

/**
 * 获取 API 基础地址
 */
function getBaseUrl() {
  return app.globalData.apiBaseUrl
}

/**
 * 获取可用字体列表
 */
function getFonts() {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${getBaseUrl()}/api/miniprogram/fonts`,
      method: 'GET',
      success(res) {
        if (res.statusCode === 200 && res.data.status === 'success') {
          resolve(res.data.fonts)
        } else {
          reject(new Error(res.data.message || '获取字体列表失败'))
        }
      },
      fail(err) {
        reject(new Error('网络请求失败'))
      }
    })
  })
}

/**
 * 预览手写效果（返回 base64 图片）
 * @param {Object} params 参数对象
 * @param {String} fontFilePath 字体文件路径（可选）
 * @param {String} backgroundFilePath 背景图片路径（可选）
 */
function preview(params, fontFilePath, backgroundFilePath) {
  return new Promise((resolve, reject) => {
    const formData = buildFormData(params)
    
    // 如果有自定义字体文件
    if (fontFilePath) {
      wx.uploadFile({
        url: `${getBaseUrl()}/api/miniprogram/preview`,
        filePath: fontFilePath,
        name: 'font_file',
        formData: formData,
        success(res) {
          handleResponse(res, resolve, reject)
        },
        fail(err) {
          reject(new Error('上传失败'))
        }
      })
    } else if (backgroundFilePath) {
      // 如果有背景图片
      wx.uploadFile({
        url: `${getBaseUrl()}/api/miniprogram/preview`,
        filePath: backgroundFilePath,
        name: 'background_image',
        formData: formData,
        success(res) {
          handleResponse(res, resolve, reject)
        },
        fail(err) {
          reject(new Error('上传失败'))
        }
      })
    } else {
      // 纯参数请求
      wx.request({
        url: `${getBaseUrl()}/api/miniprogram/preview`,
        method: 'POST',
        header: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        data: formData,
        success(res) {
          if (res.statusCode === 200 && res.data.status === 'success') {
            resolve(res.data)
          } else {
            reject(new Error(res.data.message || '预览生成失败'))
          }
        },
        fail(err) {
          reject(new Error('网络请求失败'))
        }
      })
    }
  })
}

/**
 * 生成完整文件（ZIP 或 PDF）
 * @param {Object} params 参数对象
 * @param {Boolean} pdfMode 是否生成 PDF
 * @param {String} fontFilePath 字体文件路径（可选）
 * @param {String} backgroundFilePath 背景图片路径（可选）
 */
function generate(params, pdfMode = false, fontFilePath, backgroundFilePath) {
  return new Promise((resolve, reject) => {
    const formData = buildFormData(params)
    formData.pdf_save = pdfMode ? 'true' : 'false'
    
    if (fontFilePath) {
      wx.uploadFile({
        url: `${getBaseUrl()}/api/miniprogram/generate`,
        filePath: fontFilePath,
        name: 'font_file',
        formData: formData,
        success(res) {
          handleResponse(res, resolve, reject)
        },
        fail(err) {
          reject(new Error('上传失败'))
        }
      })
    } else if (backgroundFilePath) {
      wx.uploadFile({
        url: `${getBaseUrl()}/api/miniprogram/generate`,
        filePath: backgroundFilePath,
        name: 'background_image',
        formData: formData,
        success(res) {
          handleResponse(res, resolve, reject)
        },
        fail(err) {
          reject(new Error('上传失败'))
        }
      })
    } else {
      wx.request({
        url: `${getBaseUrl()}/api/miniprogram/generate`,
        method: 'POST',
        header: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        data: formData,
        success(res) {
          if (res.statusCode === 200 && res.data.status === 'success') {
            resolve(res.data)
          } else {
            reject(new Error(res.data.message || '生成失败'))
          }
        },
        fail(err) {
          reject(new Error('网络请求失败'))
        }
      })
    }
  })
}

/**
 * 下载生成的文件
 * @param {String} fileId 文件 ID
 */
function downloadFile(fileId) {
  return new Promise((resolve, reject) => {
    wx.downloadFile({
      url: `${getBaseUrl()}/api/miniprogram/download/${fileId}`,
      success(res) {
        if (res.statusCode === 200) {
          resolve(res.tempFilePath)
        } else {
          reject(new Error('下载失败'))
        }
      },
      fail(err) {
        reject(new Error('下载失败'))
      }
    })
  })
}

/**
 * 解析上传的文档
 * @param {String} filePath 文件路径
 */
function parseDocument(filePath) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${getBaseUrl()}/api/textfileprocess`,
      filePath: filePath,
      name: 'file',
      success(res) {
        try {
          const data = JSON.parse(res.data)
          if (data.text) {
            resolve(data.text)
          } else {
            reject(new Error('解析文档失败'))
          }
        } catch (e) {
          reject(new Error('解析响应失败'))
        }
      },
      fail(err) {
        reject(new Error('上传失败'))
      }
    })
  })
}

/**
 * 构建表单数据
 */
function buildFormData(params) {
  const settings = app.globalData.settings
  
  return {
    text: params.text || '',
    font_size: String(params.fontSize || settings.fontSize),
    line_spacing: String(params.lineSpacing || settings.lineSpacing),
    word_spacing: String((params.wordSpacing || settings.wordSpacing) - 20),
    fill: params.fill || settings.fill,
    left_margin: String(params.marginLeft || settings.marginLeft),
    top_margin: String(params.marginTop || settings.marginTop),
    right_margin: String(params.marginRight || settings.marginRight),
    bottom_margin: String(params.marginBottom || settings.marginBottom),
    width: String(params.width || settings.width),
    height: String(params.height || settings.height),
    line_spacing_sigma: String(params.lineSpacingSigma || settings.lineSpacingSigma),
    font_size_sigma: String(params.fontSizeSigma || settings.fontSizeSigma),
    word_spacing_sigma: String(params.wordSpacingSigma || settings.wordSpacingSigma),
    perturb_x_sigma: String(params.perturbXSigma || settings.perturbXSigma),
    perturb_y_sigma: String(params.perturbYSigma || settings.perturbYSigma),
    perturb_theta_sigma: String(params.perturbThetaSigma || settings.perturbThetaSigma),
    strikethrough_probability: String(params.strikethroughProbability || settings.strikethroughProbability),
    strikethrough_length_sigma: String(params.strikethroughLengthSigma || settings.strikethroughLengthSigma),
    strikethrough_width_sigma: String(params.strikethroughWidthSigma || settings.strikethroughWidthSigma),
    strikethrough_angle_sigma: String(params.strikethroughAngleSigma || settings.strikethroughAngleSigma),
    strikethrough_width: String(params.strikethroughWidth || settings.strikethroughWidth),
    ink_depth_sigma: String(params.inkDepthSigma || settings.inkDepthSigma),
    isUnderlined: params.isUnderlined ? 'true' : 'false',
    line_color: params.lineColor || 'red',
    paper_type: params.paperType || 'plain',
    font_option: params.fontOption || settings.selectedFont,
    // 用户相关参数
    openid: params.openid || '',
    use_free_mode: params.useFreeMode ? 'true' : 'false'
  }
}

/**
 * 处理上传响应
 */
function handleResponse(res, resolve, reject) {
  try {
    const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
    if (data.status === 'success') {
      resolve(data)
    } else {
      reject(new Error(data.message || '请求失败'))
    }
  } catch (e) {
    reject(new Error('解析响应失败'))
  }
}

/**
 * 验证相思豆
 * @param {String} loveseedCode 6位相思豆
 */
function verifyLoveseedCode(loveseedCode) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${getBaseUrl()}/api/loveseed/verify`,
      method: 'POST',
      header: {
        'Content-Type': 'application/json'
      },
      data: {
        loveseed_code: loveseedCode
      },
      success(res) {
        if (res.statusCode === 200 && res.data.status === 'success') {
          resolve(res.data)
        } else {
          reject(new Error(res.data.message || '验证失败'))
        }
      },
      fail(err) {
        reject(new Error('网络请求失败'))
      }
    })
  })
}

/**
 * 使用相思豆生成（会自动消耗一次下载次数）
 * @param {Object} params 参数对象
 * @param {Boolean} pdfMode 是否生成 PDF
 * @param {String} fontFilePath 字体文件路径（可选）
 * @param {String} backgroundFilePath 背景图片路径（可选）
 */
function generateWithLoveseed(params, pdfMode = false, fontFilePath, backgroundFilePath) {
  return new Promise((resolve, reject) => {
    const formData = buildFormData(params)
    formData.pdf_save = pdfMode ? 'true' : 'false'
    formData.loveseed_code = params.loveseedCode
    
    // 直接调用生成 API，后端会自动验证并消耗相思豆
    if (fontFilePath) {
      wx.uploadFile({
        url: `${getBaseUrl()}/api/miniprogram/generate`,
        filePath: fontFilePath,
        name: 'font_file',
        formData: formData,
        success(res) {
          handleGenerateResponse(res, resolve, reject)
        },
        fail(err) {
          reject(new Error('上传失败'))
        }
      })
    } else if (backgroundFilePath) {
      wx.uploadFile({
        url: `${getBaseUrl()}/api/miniprogram/generate`,
        filePath: backgroundFilePath,
        name: 'background_image',
        formData: formData,
        success(res) {
          handleGenerateResponse(res, resolve, reject)
        },
        fail(err) {
          reject(new Error('上传失败'))
        }
      })
    } else {
      wx.request({
        url: `${getBaseUrl()}/api/miniprogram/generate`,
        method: 'POST',
        header: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        data: formData,
        success(res) {
          if (res.statusCode === 200 && res.data.status === 'success') {
            resolve(res.data)
          } else {
            reject(new Error(res.data.message || '生成失败'))
          }
        },
        fail(err) {
          reject(new Error('网络请求失败'))
        }
      })
    }
  })
}

/**
 * 处理生成响应（带相思豆信息）
 */
function handleGenerateResponse(res, resolve, reject) {
  try {
    const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
    if (data.status === 'success') {
      resolve(data)
    } else {
      reject(new Error(data.message || '请求失败'))
    }
  } catch (e) {
    reject(new Error('解析响应失败'))
  }
}

module.exports = {
  getFonts,
  preview,
  generate,
  downloadFile,
  parseDocument,
  verifyLoveseedCode,
  generateWithLoveseed
}
