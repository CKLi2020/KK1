# Ping++ 支付集成配置说明

## 📋 集成完成清单

✅ 已安装 Ping++ Python SDK (`pingpp`)
✅ 已创建支付服务模块 (`payment_service.py`)
✅ 已添加支付API端点 (create-charge, check-status, webhook)
✅ 已集成前端二维码支付界面
✅ 已实现支付状态轮询机制

---

## 🔧 配置步骤

### 1️⃣ 注册 Ping++ 账号

1. 访问 https://www.pingxx.com/
2. 注册账号（个人/企业）
3. 完成实名认证

### 2️⃣ 获取 API 密钥

登录 Ping++ 控制台后：

1. 进入"应用管理"
2. 创建应用（或使用已有应用）
3. 获取以下信息：
   - **API Key (sk_live_xxx或sk_test_xxx)**
   - **App ID (app_xxx)**

### 3️⃣ 配置环境变量

在项目根目录创建/修改 `.env` 文件：

```env
# Ping++ 配置
PINGPP_API_KEY=sk_test_your_api_key_here
PINGPP_APP_ID=app_your_app_id_here

# 本地测试模式（true=模拟支付，false=真实支付）
LOCAL_TEST_MODE=true
```

### 4️⃣ 配置支付渠道

在 Ping++ 控制台：

1. 进入"渠道配置"
2. 开通支付渠道：
   - **微信支付**：需要微信商户号
   - **支付宝支付**：需要支付宝商户号

### 5️⃣ 配置 Webhook（可选，用于异步通知）

1. 在 Ping++ 控制台设置 Webhook URL：
   ```
   https://your-domain.com/api/payment/webhook
   ```

2. 下载 Ping++ 公钥（用于验证签名）：
   - 保存为 `pingpp_public_key.pem`
   - 放在 backend 目录下

---

## 🧪 测试流程

### 本地测试模式

当前代码已配置为测试模式 (`LOCAL_TEST_MODE=true`)：

1. ✅ **无需真实支付**：会生成模拟二维码
2. ✅ **自动通过**：2秒后自动标记为"已支付"
3. ✅ **立即生成相思豆**

**测试步骤：**
```bash
# 1. 安装依赖
cd backend
poetry install

# 2. 启动后端
python app.py

# 3. 启动前端
cd ../frontend_payment
python -m http.server 8081

# 4. 访问浏览器
# http://localhost:8081
```

### 生产环境部署

修改 `.env`：
```env
LOCAL_TEST_MODE=false
PINGPP_API_KEY=sk_live_your_real_api_key
PINGPP_APP_ID=app_your_real_app_id
```

---

## 📡 API 端点说明

### 1. 创建支付凭据
```
POST /api/payment/create-charge
```

**请求参数：**
```json
{
  "package_id": 3,
  "channel": "wx_pub_qr"  // 或 "alipay_qr"
}
```

**响应示例：**
```json
{
  "status": "success",
  "data": {
    "charge": {
      "id": "ch_xxx",
      "credential": {
        "wx_pub_qr": {
          "code_url": "weixin://wxpay/bizpayurl?pr=xxx"
        }
      }
    },
    "order_no": "LS20231220123456789012",
    "package": { ... }
  }
}
```

### 2. 查询支付状态
```
POST /api/payment/check-status
```

**请求参数：**
```json
{
  "charge_id": "ch_xxx"
}
```

**响应示例：**
```json
{
  "status": "success",
  "paid": true,
  "loveseed_info": {
    "order_no": "LS20231220123456789012",
    "loveseed_code": "789012",
    "download_count": 20,
    "package_name": "热门套餐"
  }
}
```

### 3. Webhook 回调
```
POST /api/payment/webhook
```

Ping++ 会在支付成功后自动调用此接口。

---

## 💳 支付渠道说明

### 微信支付
- **PC端**：`wx_pub_qr` - 生成二维码扫码支付
- **手机端**：`wx_wap` - 跳转微信APP支付

### 支付宝支付
- **PC端**：`alipay_qr` - 生成二维码扫码支付
- **手机端**：`alipay_wap` - 跳转支付宝APP支付

---

## 🎯 前端集成说明

### 二维码生成
使用 QRCode.js 库：
```html
<script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"></script>
```

### 支付流程
1. 用户选择套餐
2. 点击支付按钮
3. 显示二维码弹窗
4. 用户扫码支付
5. 前端每2秒轮询支付状态
6. 支付成功后显示相思豆

---

## ⚠️ 注意事项

### 1. 安全性
- ✅ 生产环境必须使用HTTPS
- ✅ API Key 绝不能暴露在前端代码中
- ✅ Webhook 必须验证签名

### 2. 费率
- Ping++ 手续费：约 2-3%
- 微信支付费率：0.6%
- 支付宝费率：0.6%

### 3. 资质要求
- 个人用户：需实名认证
- 企业用户：需营业执照、对公账户

---

## 🚀 快速启动

```bash
# 1. 安装依赖
cd backend
poetry install

# 2. 配置环境变量
cp ../.env_template .env
# 编辑 .env，填入 Ping++ API Key

# 3. 启动后端
python app.py

# 4. 新终端启动前端
cd frontend_payment
python -m http.server 8081

# 5. 访问测试
# http://localhost:8081
```

---

## 📞 技术支持

- Ping++ 官方文档：https://www.pingxx.com/docs
- Ping++ Python SDK：https://github.com/PingPlusPlus/pingpp-python

---

## ✅ 完成状态

- ✅ 后端 Ping++ SDK 集成
- ✅ 支付API接口实现
- ✅ 二维码支付界面
- ✅ 支付状态轮询
- ✅ 相思豆生成
- ⏳ 生产环境配置（需要你的 Ping++ 账号信息）

**下一步：**
1. 注册 Ping++ 账号
2. 获取 API Key
3. 修改 `.env` 配置
4. 测试真实支付流程
