# ---------- build stage ----------
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /build

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project --frozen

# Copy application source and install the project itself
COPY . .
RUN uv sync --no-dev --frozen

# ---------- runtime stage ----------
FROM public.ecr.aws/lambda/python:3.13

# Copy the virtual-env and application code from the builder
COPY --from=builder /build/.venv ${LAMBDA_TASK_ROOT}/.venv
COPY --from=builder /build/app ${LAMBDA_TASK_ROOT}/app
COPY --from=builder /build/lambda_handler.py ${LAMBDA_TASK_ROOT}/

# Add virtual-env site-packages to the Python path
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}/.venv/lib/python3.13/site-packages:${LAMBDA_TASK_ROOT}"

CMD ["lambda_handler.handler"]
