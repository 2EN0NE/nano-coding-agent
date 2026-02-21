#!/bin/bash
set -e

IMAGE="ai-coding-sandbox:latest"
CONTAINER_NAME="ai-coding-sandbox"
PROJECT_DIR="$(pwd)"

build() {
    echo "Building Docker image..."
    docker build -t "$IMAGE" -f - . <<EOF
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    git \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir copier semgrep deepeval

RUN useradd -m -u 1000 sandbox
USER sandbox
WORKDIR /workspace

ENV CI=true
ENV DEBIAN_FRONTEND=noninteractive
ENV GIT_TERMINAL_PROMPT=0

CMD ["/bin/bash"]
EOF
}

start() {
    echo "Starting container..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        -v "$PROJECT_DIR:/workspace" \
        -w /workspace \
        -e CI=true \
        -e DEBIAN_FRONTEND=noninteractive \
        -e GIT_TERMINAL_PROMPT=0 \
        "$IMAGE"
}

stop() {
    echo "Stopping container..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
}

exec_cmd() {
    docker exec -it "$CONTAINER_NAME" "$@"
}

case "${1:-}" in
    build)
        build
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        start
        ;;
    exec)
        shift
        exec_cmd "$@"
        ;;
    *)
        echo "Usage: $0 {build|start|stop|restart|exec}"
        exit 1
        ;;
esac
