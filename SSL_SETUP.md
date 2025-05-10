# SSL 证书配置说明

## 1. 使用 Let's Encrypt 免费证书

### 自动配置（推荐）
如果使用 Render 部署，SSL 证书会自动配置，无需手动操作。

### 手动配置
如果需要手动配置 SSL 证书，请按以下步骤操作：

1. 安装 Certbot：
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install certbot

# CentOS
sudo yum install certbot
```

2. 获取证书：
```bash
sudo certbot certonly --standalone -d youtump3.me -d www.youtump3.me
```

3. 证书文件位置：
- 证书：`/etc/letsencrypt/live/youtump3.me/fullchain.pem`
- 私钥：`/etc/letsencrypt/live/youtump3.me/privkey.pem`

## 2. 配置 Nginx（如果使用）

1. 安装 Nginx：
```bash
sudo apt-get install nginx
```

2. 创建 Nginx 配置：
```nginx
server {
    listen 443 ssl;
    server_name youtump3.me www.youtump3.me;

    ssl_certificate /etc/letsencrypt/live/youtump3.me/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/youtump3.me/privkey.pem;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name youtump3.me www.youtump3.me;
    return 301 https://$server_name$request_uri;
}
```

3. 启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/youtump3.me /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 3. 证书自动续期

Let's Encrypt 证书有效期为 90 天，需要定期续期：

1. 测试续期：
```bash
sudo certbot renew --dry-run
```

2. 添加自动续期任务：
```bash
sudo crontab -e
```

添加以下内容：
```
0 0 1 * * certbot renew --quiet
```

## 4. 安全建议

1. 启用 HTTP/2
2. 配置 HSTS
3. 使用强密码套件
4. 定期更新证书
5. 监控证书过期时间

## 5. 故障排除

如果遇到 SSL 问题：

1. 检查证书是否过期：
```bash
sudo certbot certificates
```

2. 检查 Nginx 配置：
```bash
sudo nginx -t
```

3. 查看 Nginx 错误日志：
```bash
sudo tail -f /var/log/nginx/error.log
```

4. 检查防火墙设置：
```bash
sudo ufw status
```

## 6. 注意事项

1. 确保域名 DNS 已正确配置
2. 保持服务器时间同步
3. 定期备份证书
4. 监控证书状态
5. 及时更新系统和软件包 