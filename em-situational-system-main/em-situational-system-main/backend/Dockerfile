ARG PYTHON_BASE_IMAGE=python:3.11-slim
FROM ${PYTHON_BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

ARG PIP_INDEX_URL=
ARG PIP_EXTRA_INDEX_URL=

COPY requirements.txt ./
COPY wheels/ /tmp/wheels/

RUN python -m pip install --upgrade pip && \
    if [ -n "$PIP_INDEX_URL" ]; then pip config set global.index-url "$PIP_INDEX_URL"; fi && \
    if [ -n "$PIP_EXTRA_INDEX_URL" ]; then pip config set global.extra-index-url "$PIP_EXTRA_INDEX_URL"; fi && \
    if find /tmp/wheels -maxdepth 1 -type f | grep -q .; then \
      pip install --no-index --find-links=/tmp/wheels -r requirements.txt; \
    else \
      pip install --no-cache-dir -r requirements.txt; \
    fi && \
    rm -rf /root/.cache/pip /tmp/wheels

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
