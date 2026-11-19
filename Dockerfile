FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data
COPY evals ./evals
COPY scripts ./scripts
COPY tests ./tests
COPY results ./results

RUN pip install --no-cache-dir -e ".[rag,baseline]"

CMD ["sh", "-c", "python scripts/validate_cases.py && pytest"]
