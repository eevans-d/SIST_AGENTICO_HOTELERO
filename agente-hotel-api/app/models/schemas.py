# [PROMPT GA-02] app/models/schemas.py

from pydantic import BaseModel


class HealthCheck(BaseModel):
    status: str
    timestamp: str


class ReadinessCheck(BaseModel):
    ready: bool
    checks: dict
    timestamp: str


class LivenessCheck(BaseModel):
    alive: bool
    timestamp: str
