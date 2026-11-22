FROM ghcr.io/astral-sh/uv:0.13.9 AS uv
FROM python:3.13-slim

COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY app/ app/
COPY sql/ sql/
COPY seeds/ seeds/
COPY specs/ specs/
COPY prompts/ prompts/
COPY evals/ evals/
COPY data/BUSINESS_CONTEXT.md data/BUSINESS_CONTEXT.md
RUN uv sync --locked --no-dev \
    && useradd --create-home --uid 10001 cloudnova \
    && mkdir -p /app/build \
    && chown -R cloudnova:cloudnova /app/build
ENV PATH="/app/.venv/bin:$PATH" CLOUDNOVA_DATA_PATH=/input/invoices.csv
USER cloudnova
ENTRYPOINT ["python", "-m", "app"]
CMD ["build"]
