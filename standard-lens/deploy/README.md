# 部署说明

以下命令默认在**仓库根目录**执行（标注了 `cd` 的除外），路径与 `deploy/systemd/standard-lens-api.service`、`deploy/nginx/standard-lens.conf` 保持一致：

- 后端：`/opt/standard-lens/backend`
- 前端静态文件：`/var/www/standard-lens`
- API：`127.0.0.1:8000`（只监听本机，由 Nginx 反向代理）

## 1. MySQL 8

```bash
mysql -u root -p < deploy/mysql/init.sql
```

先修改 `init.sql` 中的默认密码。若数据库在另一台机器上，需要把用户主机从 `localhost` 改为应用服务器地址，并同步调整 `backend/.env`。

## 2. 后端

```bash
sudo mkdir -p /opt/standard-lens
sudo rsync -a --delete backend/ /opt/standard-lens/backend/
sudo rsync -a --delete deploy/ /opt/standard-lens/deploy/
cd /opt/standard-lens/backend

sudo python3.12 -m venv .venv
sudo .venv/bin/pip install -r requirements.txt

sudo cp .env.example .env
sudo nano .env                 # 填写 APP_ENV=production、MySQL 账号、ADMIN_SYNC_TOKEN 等
sudo chmod 600 .env
```

执行数据库迁移：

```bash
sudo .venv/bin/python -m scripts.init_db
sudo .venv/bin/python -m alembic upgrade head
```

安装并启动 systemd 服务：

```bash
sudo cp /opt/standard-lens/deploy/systemd/standard-lens-api.service /etc/systemd/system/
sudo chown -R www-data:www-data /opt/standard-lens
sudo systemctl daemon-reload
sudo systemctl enable --now standard-lens-api
sudo systemctl status standard-lens-api
```

查看日志：

```bash
sudo journalctl -u standard-lens-api -f
```

## 3. 前端

在构建机或服务器上：

```bash
cd frontend
npm ci
npm run build

sudo mkdir -p /var/www/standard-lens
sudo rsync -a --delete dist/ /var/www/standard-lens/
```

`dist/` 中包含 `index.html`、静态资源、`manifest.webmanifest`、`sw.js` 和 PWA 图标。Service Worker 依赖 HTTPS（localhost 除外），正式环境建议配置证书。

## 4. Nginx

```bash
sudo cp /opt/standard-lens/deploy/nginx/standard-lens.conf /etc/nginx/conf.d/
sudo nginx -t
sudo systemctl reload nginx
```

配置要点：

- `/api/` 反向代理到 `127.0.0.1:8000`
- `/assets/` 长期缓存（文件名带 hash）
- `sw.js`、`registerSW.js` 禁止缓存
- 其余路径回退到 `index.html`，支持前端路由
- `client_max_body_size 20m`，为后续图片上传预留

## 5. 首次标准数据同步

`ADMIN_SYNC_TOKEN` 必须改成随机强令牌。systemd 示例固定 `--workers 1`，因为每日定时任务和同步互斥锁都在进程内。

服务启动后手动触发首次全量初始化：

```bash
curl -X POST "http://127.0.0.1:8000/api/admin/sync/standards?mode=auto" \
  -H "X-Admin-Token: <ADMIN_SYNC_TOKEN>"
```

- 首次 `auto` 会执行全量；之后每日定时任务只做增量
- 全量目录约 8 万条，默认 1 秒/请求，可能持续很久；建议非高峰执行
- 可先设置 `SYNC_MAX_ITEMS_PER_RUN=50` 做小规模验证，再改为 `0` 执行完整初始化
- 未完成首次初始化时，每日任务会跳过并记录警告

查看同步日志：

```sql
SELECT id, source, status, total_count, success_count, failed_count,
       started_at, finished_at, error_message
FROM sync_task
ORDER BY id DESC
LIMIT 5;
```

或：

```bash
sudo journalctl -u standard-lens-api -f
```

## 6. 升级流程

```bash
# 后端
sudo rsync -a --delete backend/ /opt/standard-lens/backend/
sudo /opt/standard-lens/backend/.venv/bin/pip install -r /opt/standard-lens/backend/requirements.txt
sudo /opt/standard-lens/backend/.venv/bin/python -m alembic upgrade head
sudo systemctl restart standard-lens-api

# 前端
cd frontend && npm ci && npm run build
sudo rsync -a --delete dist/ /var/www/standard-lens/
```

## 7. 上线检查

```bash
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS "http://127.0.0.1:8000/api/v1/standards/search?q=GB%204806.11-2023"
curl -I http://127.0.0.1/
curl -I http://127.0.0.1/sw.js
```

`/api/health` 的 `status` 应为 `ok`。若不是，先检查 MySQL 与 `.env`。

## 8. AI Key 与接口安全

- **必须启用 HTTPS**：AI Key 由浏览器随请求发送到后端；HTTP 会暴露 Key。
- 用户 Key 不写数据库、不写日志；前端默认 sessionStorage，localStorage 由用户主动选择。
- `/api/v1/ai/test-connection` 不需要管理员令牌，任何能访问站点的人都可以使用自己的 Key 发起请求。
- `/api/v1/vision/analyze` 同样不需要登录；图片最大 10MB，后端只在内存中处理，不保存原图，不记录图片内容或 Key。
- Nginx 的 `client_max_body_size` 当前为 `20m`，足够 10MB 图片和 multipart 开销；如果调低该值，要同步调整图片限制。
- 上述接口允许自定义 Base URL，后端会向用户填写的 http(s) 地址发起请求（SSRF 面）。公网部署时应：
  - 在 Nginx/网关层限制访问或增加认证/限流
  - 通过出口网络策略限制后端可访问的地址范围
  - 不要把内部管理网络暴露给这些接口
- AI 请求超时由 `AI_REQUEST_TIMEOUT_SECONDS` 控制，默认 20 秒。

> 注意：健康检查接口对公网暴露了数据库失败的第一行错误信息，生产环境建议在 Nginx 层限制该路径的访问，或在后续阶段改为仅返回通用错误。
