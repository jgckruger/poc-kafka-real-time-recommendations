import os
import valkey
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

VALKEY_HOST = os.getenv('VALKEY_HOST', 'valkey')
VALKEY_PORT = int(os.getenv('VALKEY_PORT', 6379))

app = FastAPI(title="Recommendation Gateway")

client = valkey.Valkey(host=VALKEY_HOST, port=VALKEY_PORT, socket_timeout=3)

@app.get("/recommendations/popularity")
def get_popularity(topn: int = 10):
    try:
        result = client.zrevrange("popularity", 0, topn-1, withscores=True)
        return JSONResponse({"top": [{"content_id": k.decode(), "score": int(v)} for k, v in result]})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recommendations/content/{content_id}")
def get_similar(content_id: str, topn: int = 10):
    try:
        key = f"sim:{content_id}"
        result = client.zrevrange(key, 0, topn-1, withscores=True)
        return JSONResponse({"content_id": content_id, "similar": [{"content_id": k.decode(), "score": int(v)} for k, v in result]})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recommendations/user/{user_id}")
def get_user_recs(user_id: str, topn: int = 10):
    try:
        # Get last N items from profile
        items = client.lrange(f"profile:{user_id}", 0, 9)
        sim_scores = {}
        for item in items:
            sim_key = f"sim:{item.decode()}"
            similars = client.zrevrange(sim_key, 0, 4, withscores=True)
            for k, v in similars:
                k_dec = k.decode()
                if k_dec not in items:
                    sim_scores[k_dec] = sim_scores.get(k_dec, 0) + v
        # Sort and return top N
        top = sorted(sim_scores.items(), key=lambda x: -x[1])[:topn]
        return JSONResponse({"user_id": user_id, "recommendations": [{"content_id": k, "score": int(v)} for k, v in top]})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
