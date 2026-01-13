# 部署与布置指南（后端 + 前端 + 小程序）

本指南涵盖开发环境和生产环境两种常见场景下的布置步骤，包含环境准备、后端（Flask）部署方案、前端（Vue）部署、微信小程序发布要点、反向代理（Nginx）和示例 `systemd`、`docker-compose` 配置。

**注意**：本指南提供可复制的示例配置，请根据你的实际域名、路径、用户与安全策略调整。

---

## 一、配置管理说明

为了避免在多个地方重复设置配置而导致遗漏或不一致，本项目采用统一配置管理。

### 核心配置变量统一管理

**`LOCAL_TEST_MODE`**: 控制本地测试模式开关
- `true`: 本地开发/测试模式，使用本地地址
- `false`: 生产部署模式，使用服务器地址

**`SERVER_IP`**: 服务器公网IP地址

### 各组件配置位置

#### 1. 小程序配置
**文件**: `miniprogram/app.js` 中的 `globalData`
```javascript
globalData: {
  // 配置：本地测试模式开关
  LOCAL_TEST_MODE: true,  // 本地测试时设为true，部署时设为false
  SERVER_IP: '47.107.148.252',  // 服务器公网地址
  
  // 其他全局配置...
}
```

#### 2. Web前端配置
**文件**: `web_frontend/app.js` 顶部
```javascript
// 部署配置：设置为false时自动使用服务器地址
const LOCAL_TEST_MODE = true;  // 本地测试时设为true，部署时设为false
const SERVER_IP = '47.107.148.252';  // 服务器公网地址
```

#### 3. 后端配置
**方式**: 通过环境变量设置
- Docker: 在 `docker-compose.yml` 或 `.env` 文件中设置
- Systemd: 在服务文件中设置环境变量

### 部署时的统一修改步骤

**本地开发 → 生产部署**:
1. 将 `miniprogram/app.js` 中的 `LOCAL_TEST_MODE` 改为 `false`
2. 将 `web_frontend/app.js` 中的 `LOCAL_TEST_MODE` 改为 `false`  
3. 通过 `.env` 文件或环境变量设置后端的 `LOCAL_TEST_MODE=false`

**生产部署 → 本地开发**:
1. 将上述配置改回 `true`

这样确保了所有组件的配置保持一致，避免了配置遗漏的问题。

---

## 二、准备工作

- 操作系统：推荐使用 Ubuntu 20.04/22.04 或 CentOS 7/8（以下示例基于 Ubuntu）
- 安装基本工具：`git`, `curl`, `python3`, `python3-venv`, `nginx`, `docker`（如需容器化）
- 建议为服务创建单独的系统用户（例如 `handwrite`）以降低权限风险

示例（Ubuntu）:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip nginx
```

将代码克隆到目标服务器：

```bash
cd /srv
sudo git clone https://github.com/your/repo.git handwriting_web
sudo chown -R $USER:$USER handwriting_web
cd handwriting_web
```

---

## 三、后端（Flask）部署

后端位于 `backend/`。提供两种常见的部署方式：使用 `gunicorn`+`systemd`（推荐生产）或 Docker Compose。

### 方式 A — Gunicorn + systemd（推荐）

1. 创建并激活虚拟环境，安装依赖：

```bash
cd handwriting_web/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 配置环境变量（示例，使用 `.env` 或 systemd 环境文件）

重要变量包括：
- `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
- `WX_APPID`, `WX_SECRET`（若部署小程序后端必须配置）
- `APP_NAME`（水印显示的名称）
- `LOCAL_TEST_MODE=false`（生产一定要关闭）

示例 systemd 环境文件 `/etc/systemd/system/handwrite.service`：

```ini
[Unit]
Description=Handwriting Web Backend
After=network.target

[Service]
User=handwrite
Group=handwrite
WorkingDirectory=/srv/handwriting_web/backend
Environment="PATH=/srv/handwriting_web/backend/.venv/bin"
Environment="LOCAL_TEST_MODE=false"
Environment="MYSQL_HOST=127.0.0.1"
Environment="MYSQL_USER=handwrite"
Environment="MYSQL_PASSWORD=secret"
Environment="MYSQL_DATABASE=handwriting"
ExecStart=/srv/handwriting_web/backend/.venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable handwrite.service
sudo systemctl start handwrite.service
sudo journalctl -u handwrite.service -f
```

### 方式 B — Docker Compose（推荐用于快速部署）

项目已提供完整的 Docker Compose 配置，支持一键部署所有服务。

#### 1. 环境准备

确保服务器已安装 Docker 和 Docker Compose：

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker

# CentOS/RHEL
sudo yum install -y docker docker-compose
sudo systemctl enable docker
sudo systemctl start docker

# 添加用户到 docker 组（可选，避免每次使用 sudo）
sudo usermod -aG docker $USER
# 注销重新登录生效
```

#### 2. 克隆项目代码

```bash
cd /srv
sudo git clone https://github.com/your/repo.git handwriting_web
sudo chown -R $USER:$USER handwriting_web
cd handwriting_web
```

#### 3. 配置环境变量

复制并修改环境配置文件：

```bash
cp .env_template .env
nano .env  # 或使用其他编辑器
```

**关键配置项说明**：

```bash
# 生产部署必须设为 false
LOCAL_TEST_MODE=false

# 数据库配置（建议修改默认密码）
MYSQL_USER=handwrite_user
MYSQL_PASSWORD=your_secure_password_here
MYSQL_DATABASE=handwriting_db

# 支付配置（如需支付功能）
PINGPP_API_KEY=your_pingpp_api_key
PINGPP_APP_ID=your_pingpp_app_id

# 微信小程序配置（如需小程序功能）
WX_APPID=your_wechat_app_id
WX_SECRET=your_wechat_app_secret

# 管理员配置（可选）
ADMIN_OPENIDS=admin_openid1,admin_openid2
```

#### 4. 前端配置修改

修改前端配置以适配生产环境：

```bash
# 编辑 web_frontend/app.js
nano web_frontend/app.js
```

将以下配置修改为生产模式：
```javascript
const LOCAL_TEST_MODE = false;  // 改为 false
const SERVER_IP = 'your_server_ip';  // 替换为实际服务器IP
```

#### 5. 小程序配置修改（如果部署小程序）

```bash
# 编辑 miniprogram/app.js
nano miniprogram/app.js
```

修改全局配置：
```javascript
globalData: {
  LOCAL_TEST_MODE: false,  // 改为 false
  SERVER_IP: 'your_server_ip',  // 替换为实际服务器IP
  apiBaseUrl: 'https://your-domain.com',  // 生产API地址
  // ...
}
```

#### 6. 启动服务

使用 Docker Compose 启动所有服务：

```bash
# 后台启动所有服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 仅查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f mysql
```

#### 7. 服务验证

启动后，验证各服务是否正常运行：

```bash
# 检查后端API
curl http://localhost:5000/api/health

# 检查前端访问
curl http://localhost:2345

# 检查数据库连接
docker-compose exec mysql mysql -u root -p${MYSQL_PASSWORD} -e "SHOW DATABASES;"
```

**服务端口说明**：
- **前端**: `http://your-server-ip:2345`
- **后端API**: `http://your-server-ip:5000`
- **管理后台**: `http://your-server-ip:2345/payment/admin.html`
- **MySQL**: `localhost:3306`（仅容器内部访问）

#### 8. 管理后台访问

项目提供了Web端管理后台，用于管理订单和相思豆码。

**访问地址**: `http://your-server-ip:2345/payment/admin.html`

**默认管理员账户**：
- 用户名: `admin`
- 密码: `admin123`

**管理后台功能**：
- 📋 订单列表：查看所有支付订单
- 💎 相思豆管理：查看所有相思豆码的使用情况
- ➕ 创建相思豆：手动创建相思豆码
- 🏗️ 站点配置：配置ICP备案、版权信息、友情链接等

**安全建议**：
```bash
# 生产环境建议修改默认管理员密码
# 编辑 web_frontend/payment/admin.html 中的 ADMIN_CREDENTIALS
nano web_frontend/payment/admin.html

# 搜索并修改这部分：
# const ADMIN_CREDENTIALS = {
#     username: 'your_admin_username',
#     password: 'your_secure_password'
# };
```

**小程序管理功能**：
小程序中的管理页面已被移除，但仍保留管理员权限系统。具有管理员权限的用户在小程序首页会看到"👑 管理"按钮，可以进行基本的用户管理操作。

#### 8. 生产环境优化

**配置反向代理（推荐）**：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        proxy_pass http://localhost:2345;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 后端API
    location /api/ {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 处理大文件上传
        client_max_body_size 50M;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

**SSL/HTTPS 配置**（小程序必需）：
```bash
# 使用 Let's Encrypt 获取免费证书
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

#### 9. 代码更新流程

当您在本地修改代码后，需要将更新部署到服务器。以下是推荐的更新流程：

##### 方式一：Git + Docker 更新（推荐）

**前置条件：设置Git仓库**

首先需要设置Git仓库，有以下几种方式：

**选项A：使用GitHub/GitLab等托管服务（推荐）**

1. **创建远程仓库**：
```bash
# 在GitHub/GitLab上创建一个新仓库，然后在本地项目目录执行：
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/your-username/handwriting_web.git
git push -u origin main
```

2. **服务器克隆仓库**：
```bash
# 在服务器上
cd /srv
sudo git clone https://github.com/your-username/handwriting_web.git
sudo chown -R $USER:$USER handwriting_web
cd handwriting_web
```

**选项B：直接在服务器设置Git仓库**

1. **在服务器上创建裸仓库**：
```bash
# 在服务器上创建Git裸仓库
sudo mkdir -p /opt/git/handwriting_web.git
cd /opt/git/handwriting_web.git
sudo git init --bare
sudo chown -R $USER:$USER /opt/git/handwriting_web.git

# 创建工作目录
cd /srv
git clone /opt/git/handwriting_web.git
sudo chown -R $USER:$USER handwriting_web
```

2. **本地添加服务器为远程仓库**：
```bash
# 在本地项目目录
git init  # 如果还没有初始化
git add .
git commit -m "Initial commit"
git remote add production user@your-server-ip:/opt/git/handwriting_web.git
git push production main
```

**选项C：使用rsync直接同步（适用于简单场景）**

如果不想使用Git，可以直接同步文件：
```bash
# 从本地同步到服务器
rsync -avz --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
  /path/to/local/handwriting_web/ user@your-server-ip:/srv/handwriting_web/

# 然后在服务器上重启服务
ssh user@your-server-ip "cd /srv/handwriting_web && docker-compose down && docker-compose up -d --build"
```

**推荐的完整Git工作流程：**

**1. 本地提交代码**：
```bash
# 在本地开发机器上
git add .
git commit -m "描述您的更改"
git push origin main  # 或您的主分支名称
```

**2. 服务器拉取更新**：
```bash
# 登录到服务器
ssh user@your-server-ip
cd /srv/handwriting_web

# 拉取最新代码
git pull origin main

# 检查文件差异（可选）
git log --oneline -5  # 查看最近5次提交
git diff HEAD~1 HEAD  # 查看最新提交的差异
```

**3. 重建并重启服务**：
```bash
# 停止现有服务
docker-compose down

# 重新构建并启动（会自动应用代码更改）
docker-compose up -d --build

# 验证服务状态
docker-compose ps
docker-compose logs -f backend frontend
```

##### 方式二：选择性服务更新

如果只修改了特定服务的代码，可以只重建相关服务：

**仅更新后端**：
```bash
# 重建后端服务
docker-compose up -d --build backend

# 查看后端日志
docker-compose logs -f backend
```

**仅更新前端**：
```bash
# 重建前端服务  
docker-compose up -d --build frontend

# 查看前端日志
docker-compose logs -f frontend
```

##### 方式三：零停机更新（生产环境推荐）

**1. 创建新版本容器**：
```bash
# 拉取代码
git pull origin main

# 构建新镜像（不停止现有服务）
docker-compose build

# 逐个重启服务
docker-compose up -d --no-deps backend  # 先更新后端
sleep 10  # 等待后端启动
docker-compose up -d --no-deps frontend  # 再更新前端
```

**2. 健康检查**：
```bash
# 检查服务是否正常
curl -f http://localhost:5000/api/health || echo "后端异常"
curl -f http://localhost:2345 || echo "前端异常"

# 检查数据库连接
docker-compose exec backend python -c "
import os
import mysql.connector
try:
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DATABASE')
    )
    print('数据库连接正常')
    conn.close()
except Exception as e:
    print(f'数据库连接失败: {e}')
"
```

##### 更新前的安全检查

**1. 备份重要数据**：
```bash
# 备份数据库
docker-compose exec mysql mysqldump \
  -u root -p${MYSQL_PASSWORD} ${MYSQL_DATABASE} \
  > backup_$(date +%Y%m%d_%H%M%S).sql

# 备份配置文件
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# 备份用户上传的文件（如果有）
tar -czf uploads_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  logs/ ttf_files/ output/ temp/ 2>/dev/null || echo "部分目录不存在，跳过"
```

**2. 测试配置更改**：
```bash
# 检查 docker-compose 配置是否有效
docker-compose config

# 检查环境变量是否正确
docker-compose config | grep -E "(MYSQL_|LOCAL_TEST_MODE|WX_)"
```

##### 回滚流程

如果更新后发现问题，可以快速回滚：

**1. Git 回滚**：
```bash
# 查看提交历史
git log --oneline -10

# 回滚到上一个版本
git reset --hard HEAD~1  # 回滚1个提交
# 或回滚到特定提交
git reset --hard <commit-hash>

# 重新构建服务
docker-compose down
docker-compose up -d --build
```

**2. 数据库回滚**（如果有数据库更改）：
```bash
# 停止服务
docker-compose down

# 恢复数据库备份
docker-compose up -d mysql
sleep 30  # 等待MySQL启动

# 导入备份
docker-compose exec mysql mysql \
  -u root -p${MYSQL_PASSWORD} ${MYSQL_DATABASE} \
  < backup_YYYYMMDD_HHMMSS.sql

# 重启所有服务
docker-compose up -d
```

##### 自动化更新脚本示例

创建自动化更新脚本 `update.sh`：

```bash
#!/bin/bash
set -e  # 遇到错误时停止

echo "🚀 开始更新部署..."

# 1. 备份
echo "📦 创建备份..."
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

docker-compose exec mysql mysqldump -u root -p${MYSQL_PASSWORD} ${MYSQL_DATABASE} > "$BACKUP_DIR/database.sql"
cp .env "$BACKUP_DIR/"

# 2. 拉取代码
echo "📥 拉取最新代码..."
git pull origin main

# 3. 检查配置
echo "🔍 检查配置..."
docker-compose config > /dev/null

# 4. 更新服务
echo "🔄 更新服务..."
docker-compose down
docker-compose up -d --build

# 5. 健康检查
echo "🏥 健康检查..."
sleep 30

if curl -f http://localhost:5000/api/health > /dev/null 2>&1; then
    echo "✅ 后端健康检查通过"
else
    echo "❌ 后端健康检查失败"
    exit 1
fi

if curl -f http://localhost:2345 > /dev/null 2>&1; then
    echo "✅ 前端健康检查通过"
else
    echo "❌ 前端健康检查失败"
    exit 1
fi

echo "🎉 更新完成！"
echo "📊 服务状态："
docker-compose ps
```

使用方法：
```bash
chmod +x update.sh
./update.sh
```

##### 常见问题处理

**1. 端口占用**：
```bash
# 查看端口占用
sudo netstat -tlnp | grep :2345
sudo netstat -tlnp | grep :5000

# 强制停止容器
docker-compose kill
docker-compose rm -f
```

**2. 磁盘空间不足**：
```bash
# 清理无用的Docker镜像
docker system prune -a

# 清理旧的备份文件
find backups/ -type f -mtime +7 -delete  # 删除7天前的备份
```

**3. 配置文件冲突**：
```bash
# 查看配置差异
git diff HEAD~1 HEAD -- .env_template
git diff HEAD~1 HEAD -- docker-compose.yml

# 手动合并配置更改
nano .env
```

通过以上流程，您可以安全、高效地更新部署在服务器上的代码，同时保证服务的稳定性和数据安全。

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷（谨慎使用）
docker-compose down -v

# 重启特定服务
docker-compose restart backend
docker-compose restart frontend

# 更新代码后重新构建
git pull
docker-compose down
docker-compose up -d --build

# 备份数据库
docker-compose exec mysql mysqldump -u root -p${MYSQL_PASSWORD} ${MYSQL_DATABASE} > backup.sql

# 进入容器调试
docker-compose exec backend bash
docker-compose exec mysql mysql -u root -p

# 查看资源使用情况
docker stats
```

#### 10. 故障排除

**常见问题**：

1. **端口被占用**：
```bash
sudo netstat -tlnp | grep :2345
sudo netstat -tlnp | grep :5000
```

2. **数据库连接失败**：
```bash
# 检查数据库容器状态
docker-compose logs mysql
# 验证数据库配置
docker-compose exec mysql mysql -u ${MYSQL_USER} -p${MYSQL_PASSWORD} -e "SHOW DATABASES;"
```

3. **内存不足**：
```bash
# 检查系统资源
free -h
df -h
# 适当增加 swap 或升级服务器配置
```

4. **权限问题**：
```bash
# 修复文件权限
sudo chown -R $USER:$USER /srv/handwriting_web
# 确保日志目录可写
mkdir -p logs
chmod 755 logs
```

---

## 四、反向代理（Nginx）

推荐在前端外层使用 Nginx 作为 SSL/TLS 终端和静态文件服务，同时对后端进行反向代理与超时配置（避免长请求被中断）。

示例 Nginx 配置（`/etc/nginx/sites-available/handwrite`）:

```nginx
server {
    listen 80;
    server_name your.domain.com;

    # 重定向到 https（如果使用 TLS）
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your.domain.com;

    ssl_certificate /etc/letsencrypt/live/your.domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your.domain.com/privkey.pem;

    client_max_body_size 50M;
    proxy_read_timeout 600s; # 延长读超时，防止长时间图片生成中断
    proxy_connect_timeout 60s;

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    # 前端静态资源（若已构建）
    location / {
        root /srv/handwriting_web/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

启用并重载 Nginx：

```bash
sudo ln -s /etc/nginx/sites-available/handwrite /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 五、前端（Vue）部署

开发模式：使用 `npm run serve`。
生产构建并托管静态文件：

```bash
cd /srv/handwriting_web/frontend
npm install
npm run build
```

构建后，`dist/` 目录包含静态站点，将其放到 Nginx `root` 指定位置（例如 `/srv/handwriting_web/frontend/dist`）。

注意：如果网站与小程序共享后端，请确保小程序中配置的域名和 Nginx 中的 `server_name` 与 HTTPS 配置一致。

---

## 六、微信小程序发布要点

1. 小程序后端必须使用 HTTPS 且域名需在微信后台配置为业务域名
2. 配置 `WX_APPID` 与 `WX_SECRET` 到后端环境变量
3. 在微信公众平台添加服务器域名并上传代码进行审核

本地调试提示：在微信开发者工具中可勾选“不校验合法域名、TLS 版本以及 HTTPS 证书”，以便访问本地后端（只用于调试）。真机测试必须使用公网 HTTPS。

---

## 七、运维与监控建议

- 日志：将后端日志写入 `/var/log/handwrite/` 或使用 `journalctl` 管理
- 备份：定期备份 MySQL 数据库与重要上传文件
- 性能：使用 `gunicorn` worker 数量与硬件核数相匹配；图片生成为 CPU 密集型任务，考虑使用专用队列（Redis + Celery）异步处理
- 安全：生产中关闭 `LOCAL_TEST_MODE`，不要暴露开发专用接口（例如 `/api/dev/*`）

---

## 八、示例运维命令（快速参考）

#### 10. 常用运维命令

```bash
# 启动/停止服务
sudo systemctl start handwrite.service
sudo systemctl stop handwrite.service

# 查看日志
sudo journalctl -u handwrite.service -f

# Nginx reload
sudo systemctl reload nginx

# Docker Compose
cd /srv/handwriting_web
docker-compose up -d --build
docker-compose logs -f
```

---

如果你需要，我可以：

- 把本文档拆成更细的 `docs/DEPLOY_BACKEND.md`, `docs/DEPLOY_FRONTEND.md`, `docs/DEPLOY_MINIPROGRAM.md`；
- 根据你的目标服务器（Ubuntu/CentOS/Alpine）生成可直接运行的脚本；
- 或者我可以现在在你的服务器上执行部分命令（例如生成 systemd 文件或 Nginx 配置）。
