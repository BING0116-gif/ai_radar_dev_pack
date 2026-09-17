"""AI Radar backend entrypoint.

FastAPI application exposing a minimal health check endpoint.
The rest of the API surface is built incrementally in later cards.
"""

from fastapi import FastAPI

app = FastAPI(title="AI Radar API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Return service liveness status."""
    return {"status": "ok"}