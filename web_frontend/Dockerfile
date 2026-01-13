# 使用官方 Nginx 镜像作为基础
FROM nginx:alpine

# 将本地的 web_frontend 目录下的所有文件复制到 Nginx 的默认网站根目录
COPY . /usr/share/nginx/html

# 暴露 80 端口
EXPOSE 80

# 启动 Nginx 服务
CMD ["nginx", "-g", "daemon off;"]
