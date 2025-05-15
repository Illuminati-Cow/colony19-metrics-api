from fastapi import FastAPI, Request
import sqlite3
import os

DB_PATH = "/data/metrics.db"

app = FastAPI()

# Ensure DB exists
os.makedirs("/data", exist_ok=True)
conn = sqlite3.connect(DB_PATH)
conn.execute("CREATE TABLE IF NOT EXISTS metrics (payload TEXT)")
conn.close()

@app.post("/metrics")
async def collect_metrics(request: Request):
    data = await request.json()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO metrics (payload) VALUES (?)", (str(data),))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/health")
async def healthcheck():
    return {"status": "ok"}