# Handwriting Web — 功能与使用说明（项目概览）

本文档总结当前仓库支持的功能、运行与调试步骤、重要接口、数据库要点与生产注意事项，便于团队理解与维护。

## 一、项目结构概览
- `backend/`：Flask 后端服务，处理小程序接口、会员、订单、图片生成与水印处理。
- `frontend/`：Vue 前端（网站版）
- `miniprogram/`：微信小程序（正式）
- `mysql/`：MySQL 初始化脚本
- `ttf_files/`、`font_assets/`：字体资源

## 二、主要功能列表（已实现）
1. 文本手写化生成（图片/PDF）
   文档已移动到 docs/

   请查看 `docs/PROJECT_FEATURES.md` 获取项目概览文档。
   - 登录（通过 `wx.login()` 获取 code -> 换取 openid / 本地模拟）
