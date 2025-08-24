from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import os
import json

app = FastAPI()
PRECOMPUTED_DIR = os.path.join(os.path.dirname(__file__), "..", "precomputed_maps")

@app.get("/api/v1/maps/{topic_name}", response_model=dict)
def get_map(topic_name: str):
    file_path = os.path.join(PRECOMPUTED_DIR, f"{topic_name}_map.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Topic not found")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(content=data)
