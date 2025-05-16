FROM python:3.11-slim

WORKDIR /app
COPY app /app

RUN pip install fastapi uvicorn pymongo

ENV PORT=8000

EXPOSE ${PORT}

CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT}"