"""FastAPI backend. Вся ML-логика находится в src/."""
import logging
from contextlib import asynccontextmanager
from typing import List, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from src.detector import check, check_batch
from src.model import load_model

log = logging.getLogger("sms_fraud_api")
MAX_LEN = 5000


def _clean(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Текст SMS не должен быть пустым")
    if len(value) > MAX_LEN:
        raise ValueError(f"Текст SMS длиннее {MAX_LEN} символов")
    return value


class CheckRequest(BaseModel):
    text: str = Field(..., examples=["Ваш аккаунт заблокирован. Отправьте код."])

    @field_validator("text")
    @classmethod
    def _text(cls, value):
        return _clean(value)


class BatchRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1, max_length=1000)

    @field_validator("texts")
    @classmethod
    def _each(cls, items):
        return [_clean(t) for t in items]


class DomainInfo(BaseModel):
    domain: str
    official: bool
    impersonation: bool


class CheckResponse(BaseModel):
    risk: Literal["low", "medium", "high"]
    score: int
    reasons: List[str]
    recommendation: str
    domains: List[DomainInfo] = []


class BatchResponse(BaseModel):
    count: int
    results: List[CheckResponse]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model_error = None
    try:
        app.state.model = load_model()
    except Exception as exc:  # модель недоступна: API стартует, /health покажет 503
        log.exception("Не удалось загрузить модель")
        app.state.model, app.state.model_error = None, str(exc)
    yield


app = FastAPI(title="SMS Fraud Detector API", version="1.0.0", lifespan=lifespan)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("Необработанная ошибка")
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


def _require_model(request: Request):
    if request.app.state.model is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")


@app.get("/health")
def health(request: Request):
    model = request.app.state.model
    if model is None:
        raise HTTPException(status_code=503, detail=f"Модель не загружена: {request.app.state.model_error}")
    return {"status": "ok", "model_loaded": True, "classes": [str(c) for c in model.classes_]}


@app.post("/check", response_model=CheckResponse)
def check_one(body: CheckRequest, request: Request):
    _require_model(request)
    try:
        return check(body.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/check/batch", response_model=BatchResponse)
def check_many(body: BatchRequest, request: Request):
    _require_model(request)
    try:
        results = check_batch(body.texts)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"count": len(results), "results": results}
