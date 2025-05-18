FROM python:3.11-slim

WORKDIR /app

# Copy pyproject.toml and install dependencies first
COPY pyproject.toml .
RUN pip install --no-cache-dir 'fastapi' 'uvicorn' 'pymongo'

# Now copy your app code
COPY app /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]