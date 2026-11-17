# Docker Offline / Intranet Runbook

This project can now run in three Docker modes:

1. Public internet mode
2. Intranet mirror mode
3. Air-gapped offline mode

## 1. Public Internet Mode

Use the default images and PyPI:

```bash
docker compose up -d --build
```

## 2. Intranet Mirror Mode

Create a local env file from `.env.docker.example` and point images or Python packages to your mirror:

```bash
copy .env.docker.example .env.docker
```

Example values:

```env
PYTHON_BASE_IMAGE=registry.local/python:3.11-slim
POSTGRES_IMAGE=registry.local/postgres:16-alpine
REDIS_IMAGE=registry.local/redis:7-alpine
PIP_INDEX_URL=https://pypi.mirror.local/simple
PIP_EXTRA_INDEX_URL=
```

Then run:

```bash
docker compose --env-file .env.docker up -d --build
```

## 3. Air-Gapped Offline Mode

Offline mode needs two things prepared on a machine that has internet access:

- Docker base images saved to a tar archive
- Python dependency wheels downloaded into `backend/wheels/`

### Step A. Prepare images on an online machine

Pull the images:

```bash
docker pull python:3.11-slim
docker pull postgres:16-alpine
docker pull redis:7-alpine
```

Save them:

```bash
docker save -o ems-docker-images.tar python:3.11-slim postgres:16-alpine redis:7-alpine
```

### Step B. Prepare Python wheels on an online machine

From the project root:

```bash
cd backend
pip download -r requirements.txt -d wheels
cd ..
```

Transfer these to the offline machine:

- `ems-docker-images.tar`
- the whole project directory including `backend/wheels/`

### Step C. Load images on the offline machine

```bash
docker load -i ems-docker-images.tar
```

### Step D. Build and start offline

Use default image names if you loaded the same tags:

```bash
docker compose up -d --build
```

If the offline machine uses renamed local images, create `.env.docker` and point to them:

```env
PYTHON_BASE_IMAGE=local/python:3.11-slim
POSTGRES_IMAGE=local/postgres:16-alpine
REDIS_IMAGE=local/redis:7-alpine
PIP_INDEX_URL=
PIP_EXTRA_INDEX_URL=
```

Then run:

```bash
docker compose --env-file .env.docker up -d --build
```

## Why this works now

- `docker-compose.yml` accepts image overrides through environment variables.
- `backend/Dockerfile` accepts a custom Python base image.
- `backend/Dockerfile` installs from `backend/wheels/` when wheel files are present.
- The backend no longer depends on PostGIS-specific features, so `postgres:16-alpine` is enough.
- The Dockerfile no longer runs `apt-get`, which avoids another external network dependency.

## Health Checks

After the stack starts:

```bash
docker compose ps
curl http://127.0.0.1:8000/health
```

Expected health response includes:

- `status`
- `scenario_loaded`
- `database_url`
- `redis_connected`

## Notes

- `backend/wheels/.gitkeep` is tracked; real wheel files are ignored by git.
- Experiment metadata is persisted in PostgreSQL.
- Experiment progress is written to Redis.
- The API exposes progress at `/api/v1/experiments/{experiment_id}/progress`.
