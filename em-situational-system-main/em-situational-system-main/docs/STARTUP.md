# 启动方式

本文档说明如何启动当前项目，包括本地启动、Docker 启动，以及 Docker 无法联网时的内网/离线启动方式。

## 1. 本地启动

这是最推荐的启动方式，最直接，也最适合日常开发和调试。

### 1.1 进入后端目录

```powershell
cd backend
```

### 1.2 安装依赖

```powershell
pip install -r requirements.txt
```

### 1.3 启动后端服务

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 1.4 访问地址

- 前端页面: [http://127.0.0.1:8000/static/index.html](http://127.0.0.1:8000/static/index.html)
- API 文档: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 健康检查: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 1.5 常见说明

- Default startup loads online real orbit data from `data/scenarios/tle_online_v0.json` (CelesTrak TLE; cached fallback when network is unavailable).
- 如果端口 `8000` 被占用，可以改成别的端口，例如 `--port 8001`
- 如果改了端口，页面访问地址也要同步改成对应端口

## 2. Docker 启动

如果本机 Docker 能正常访问镜像源，可以直接使用 Docker Compose 启动整套服务。

### 2.1 在项目根目录启动

```powershell
docker compose up -d --build
```

### 2.2 访问地址

- 前端页面: [http://127.0.0.1:8000/static/index.html](http://127.0.0.1:8000/static/index.html)
- API 文档: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 健康检查: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2.3 查看容器状态

```powershell
docker compose ps
```

### 2.4 查看后端日志

```powershell
docker compose logs -f api
```

### 2.5 停止服务

```powershell
docker compose down
```

## 3. Docker 内网/离线启动

如果 Docker 无法访问 Docker Hub，或者运行环境在内网/离线机器上，不要直接反复重试公网启动。

请改用下面这套文档：

- DOCKER_OFFLINE.md
- .env.docker.example

这套模式支持：

- 内网镜像源
- 私有 registry
- 完全离线加载镜像和 wheel 包

## 4. 启动后如何验证

无论是本地还是 Docker，都建议启动后先做这几个检查。

### 4.1 检查健康状态

访问：

- [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

正常时会看到类似字段：

- `status`
- `scenario_loaded`
- `database_url`
- `redis_connected`

### 4.2 检查页面是否打开

访问：

- [http://127.0.0.1:8000/static/index.html](http://127.0.0.1:8000/static/index.html)

### 4.3 检查 API 文档

访问：

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## 5. 推荐使用顺序

建议按这个顺序使用：

1. 先本地启动，确认后端和页面都正常
2. 再尝试 Docker 启动
3. 如果 Docker 拉镜像失败，再切换到内网/离线方案

这样定位问题会更快。
