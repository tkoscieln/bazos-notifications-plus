# Stage 1: Build dependencies using Astral uv
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Bind application dependency files and sync them
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Stage 2: Runtime image using AWS Lambda's official base image
FROM public.ecr.aws/lambda/python:3.14

WORKDIR /var/task

# Copy compiled virtual environment dependencies from builder stage
COPY --from=builder /app/.venv/lib/python3.14/site-packages/ ./

# Copy the actual script code
COPY main.py .

# AWS Lambda invokes the specific handler function inside main.py
CMD ["main.lambda_handler"]
