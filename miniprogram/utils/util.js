// utils/util.js
// 通用工具函数

/**
 * 格式化时间
 */
function formatTime(date) {
  const year = date.getFullYear()
  const month = date.getMonth() + 1
  const day = date.getDate()
  const hour = date.getHours()
  const minute = date.getMinutes()
  const second = date.getSeconds()

  return `${[year, month, day].map(formatNumber).join('/')} ${[hour, minute, second].map(formatNumber).join(':')}`
}

function formatNumber(n) {
  n = n.toString()
  return n[1] ? n : `0${n}`
}

/**
 * 显示加载提示
 */
function showLoading(title = '加载中...') {
  wx.showLoading({
    title: title,
    mask: true
  })
}

/**
 * 隐藏加载提示
 */
function hideLoading() {
  wx.hideLoading()
}

/**
 * 显示成功提示
 */
function showSuccess(title) {
  wx.showToast({
    title: title,
    icon: 'success',
    duration: 2000
  })
}

/**
 * 显示错误提示
 */
function showError(title) {
  wx.showToast({
    title: title,
    icon: 'error',
    duration: 2000
  })
}

/**
 * 显示确认对话框
 */
function showConfirm(title, content) {
  return new Promise((resolve, reject) => {
    wx.showModal({
      title: title,
      content: content,
      success(res) {
        if (res.confirm) {
          resolve(true)
        } else {
          resolve(false)
        }
      },
      fail() {
        reject(new Error('显示对话框失败'))
      }
    })
  })
}

/**
 * 防抖函数
 */
function debounce(fn, delay = 300) {
  let timer = null
  return function (...args) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn.apply(this, args)
    }, delay)
  }
}

/**
 * 节流函数
 */
function throttle(fn, delay = 300) {
  let lastTime = 0
  return function (...args) {
    const now = Date.now()
    if (now - lastTime >= delay) {
      lastTime = now
      fn.apply(this, args)
    }
  }
}

module.exports = {
  formatTime,
  showLoading,
  hideLoading,
  showSuccess,
  showError,
  showConfirm,
  debounce,
  throttle
}
