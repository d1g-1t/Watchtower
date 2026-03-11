from __future__ import annotations

import asyncio
import os
import random

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

SERVICE_NAME = os.getenv("SERVICE_NAME", "mock")
HEALTH_MODE = os.getenv("HEALTH_MODE", "healthy")
FAIL_RATE = float(os.getenv("FAIL_RATE", "0.3"))


@app.get("/health")
async def health():
    if HEALTH_MODE == "healthy":
        return {"status": "healthy", "service": SERVICE_NAME}

    if HEALTH_MODE == "unhealthy":
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "service": SERVICE_NAME},
        )

    if HEALTH_MODE == "flaky":
        if random.random() < FAIL_RATE:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "service": SERVICE_NAME},
            )
        return {"status": "healthy", "service": SERVICE_NAME}

    if HEALTH_MODE == "slow":
        await asyncio.sleep(random.uniform(2, 8))
        return {"status": "healthy", "service": SERVICE_NAME}

    return {"status": "healthy", "service": SERVICE_NAME}
