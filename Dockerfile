FROM node:20-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM debian:bookworm-slim AS litestream
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ARG TARGETARCH=amd64
ARG LITESTREAM_VERSION=0.5.17
ARG LITESTREAM_SHA256_AMD64=cfb371176d164437ae869f8351cfde49bd1804ae71c61923f75c9cba9c9c006d
ARG LITESTREAM_SHA256_ARM64=f8ca4a050095c1efbda2c4365172e61bf9d955ea0d9ac42f448b52e51819baa5
RUN set -eu; \
    case "${TARGETARCH}" in \
        amd64) asset="litestream-${LITESTREAM_VERSION}-linux-x86_64.tar.gz"; sha="${LITESTREAM_SHA256_AMD64}" ;; \
        arm64) asset="litestream-${LITESTREAM_VERSION}-linux-arm64.tar.gz"; sha="${LITESTREAM_SHA256_ARM64}" ;; \
        *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/litestream.tar.gz \
        "https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/${asset}"; \
    echo "${sha}  /tmp/litestream.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/litestream.tar.gz -C /usr/local/bin litestream; \
    chmod +x /usr/local/bin/litestream

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY --from=litestream /usr/local/bin/litestream /usr/local/bin/litestream
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend ./backend
COPY --from=frontend /frontend/dist ./frontend/dist
COPY litestream.yml /app/litestream.yml
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh
ENV PYTHONUNBUFFERED=1
CMD ["/app/start.sh"]
