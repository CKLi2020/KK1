文档已移动到 docs/

请查看 `docs/miniprogram/README.md` 获取小程序相关文档。
## 部署到生产环境

### 后端部署

1. 准备一台有公网 IP 的服务器
2. 安装 Python 3.8+ 和依赖
3. 配置 HTTPS（小程序强制要求）
4. 使用 Gunicorn + Nginx 部署

```bash
# 安装依赖
pip install -r requirements.txt
pip install gunicorn

# 启动服务
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 小程序发布

1. 在 [微信公众平台](https://mp.weixin.qq.com/) 注册小程序账号
2. 获取正式 AppID
3. 在「开发」-「开发管理」-「开发设置」中配置服务器域名
4. 修改 `app.js` 中的 `apiBaseUrl` 为你的服务器地址
5. 在开发者工具中点击「上传」
6. 在微信公众平台提交审核

## API 接口

小程序专用的后端接口：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/miniprogram/fonts` | GET | 获取可用字体列表 |
| `/api/miniprogram/preview` | POST | 预览（返回 base64 图片） |
| `/api/miniprogram/generate` | POST | 生成完整文件 |
| `/api/miniprogram/download/<id>` | GET | 下载生成的文件 |

## 注意事项

1. **HTTPS 要求**：正式发布时，后端必须使用 HTTPS
2. **域名备案**：服务器域名需要在工信部备案
3. **文件大小**：上传的字体文件建议不超过 5MB
4. **超时限制**：小程序请求超时为 60 秒，大文本生成可能需要优化

## 自定义图标

如需启用 TabBar 导航，请在 `images/` 目录下放置以下图标：
- edit.png / edit-active.png
- settings.png / settings-active.png  
- info.png / info-active.png

然后取消 `app.json` 中 tabBar 配置的注释。
