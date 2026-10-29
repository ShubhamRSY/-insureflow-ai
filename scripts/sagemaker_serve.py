"""SageMaker inference server: GET /ping and POST /invocations on port 8080.

Model files arrive at /opt/ml/model (from model.tar.gz in S3); the image links
/app/ml_models there, so the normal model loader finds them.
"""

from __future__ import annotations

from typing import Any

import uvicorn
from fastapi import FastAPI, Request

from insureflow.ml.sagemaker import handle_invocation

app = FastAPI()


@app.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/invocations")
async def invocations(request: Request) -> dict[str, Any]:
    return handle_invocation(await request.json())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, workers=1)
