FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml poetry.lock* requirements.txt* /app/
# Install dependencies.  Try poetry first; fallback to pip requirements.
RUN set -e; \
    if [ -f poetry.lock ]; then \
      pip install poetry && poetry export --without-hashes --format=requirements.txt > /tmp/req.txt && pip install -r /tmp/req.txt; \
    elif [ -f requirements.txt ]; then \
      pip install -r requirements.txt; \
    else \
      pip install fastapi uvicorn[standard] requests pydantic sqlalchemy; \
    fi

COPY . /app

CMD ["uvicorn", "golf_flip_app.app:app", "--host", "0.0.0.0", "--port", "8000"]
