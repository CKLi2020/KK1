# 手写文字生成 - 微信小程序版

## 项目结构

```
miniprogram/
├── app.js              # 小程序入口文件
├── app.json            # 小程序配置
├── app.wxss            # 全局样式
├── project.config.json # 项目配置
├── pages/
│   ├── index/          # 主页 - 文字输入、参数设置、预览
│   ├── settings/       # 高级设置页 - 随机扰动参数
+│   └── about/          # 关于页面
├── utils/
│   ├── api.js          # API 请求封装
│   └── util.js         # 通用工具函数
└── images/             # 图标资源（需自行添加）
```

## 本地开发步骤

### 1. 启动后端服务器

```bash
cd backend
python app.py
```

后端将在 `http://localhost:5000` 启动。

...（内容已迁移）
