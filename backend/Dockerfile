# Backend image: Python 3.12 slim keeps the image small while staying on a
# well-supported interpreter for all pinned dependencies.
FROM python:3.12-slim

# Never write .pyc files; flush logs straight to the container output.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Run as a non-root user: basic container hygiene.
RUN useradd --create-home appuser

WORKDIR /code

# Install dependencies first so Docker caches this layer between code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

USER appuser
EXPOSE 8000

# Apply pending migrations, then start the API.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
