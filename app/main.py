import json
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .db import get_db
from .models import User, Endpoint, Destination, Event, Delivery
from .schemas import (
    CreateUser,
    CreateEndpoint,
    CreateDestination,
    EndpointOut,
    DestinationOut,
    DeliveryOut,
)
from .auth import generate_api_key, require_api_key, get_user_by_api_key
from .tasks import deliver_event

app = FastAPI(title="Webhook Relay MVP")


@app.get("/health")
def health():
    return {"ok": True, "ts": datetime.utcnow().isoformat()}


# ---- Admin-ish APIs (با API Key) ----
@app.post("/users")
def create_user(payload: CreateUser, db: Session = Depends(get_db)):
    api_key = generate_api_key()
    user = User(name=payload.name, api_key=api_key)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"user_id": user.id, "api_key": user.api_key}


@app.post("/endpoints", response_model=EndpointOut)
def create_endpoint(
    payload: CreateEndpoint,
    x_api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db),
):
    user = get_user_by_api_key(db, x_api_key)
    if not user:
        raise HTTPException(401, "Invalid API key")

    ep = Endpoint(user_id=user.id, name=payload.name, is_enabled=True)
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return EndpointOut(id=ep.id, name=ep.name, is_enabled=ep.is_enabled)


@app.post("/endpoints/{endpoint_id}/destinations", response_model=DestinationOut)
def add_destination(
    endpoint_id: str,
    payload: CreateDestination,
    x_api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db),
):
    user = get_user_by_api_key(db, x_api_key)
    if not user:
        raise HTTPException(401, "Invalid API key")

    ep = (
        db.query(Endpoint)
        .filter(Endpoint.id == endpoint_id, Endpoint.user_id == user.id)
        .first()
    )
    if not ep:
        raise HTTPException(404, "Endpoint not found")

    dest = Destination(
        endpoint_id=ep.id,
        url=str(payload.url),
        method=payload.method.upper(),
        secret_header_name=payload.secret_header_name,
        secret_value=payload.secret_value,
    )
    db.add(dest)
    db.commit()
    db.refresh(dest)
    return DestinationOut(id=dest.id, url=dest.url, method=dest.method)


@app.get("/endpoints/{endpoint_id}/deliveries", response_model=list[DeliveryOut])
def list_deliveries(
    endpoint_id: str,
    x_api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db),
):
    user = get_user_by_api_key(db, x_api_key)
    if not user:
        raise HTTPException(401, "Invalid API key")

    ep = (
        db.query(Endpoint)
        .filter(Endpoint.id == endpoint_id, Endpoint.user_id == user.id)
        .first()
    )
    if not ep:
        raise HTTPException(404, "Endpoint not found")

    deliveries = (
        db.query(Delivery)
        .join(Event, Delivery.event_id == Event.id)
        .filter(Event.endpoint_id == ep.id)
        .order_by(Delivery.created_at.desc())
        .limit(200)
        .all()
    )

    return [
        DeliveryOut(
            id=d.id,
            status=d.status,
            attempt=d.attempt,
            last_http_status=d.last_http_status,
            last_error=d.last_error,
        )
        for d in deliveries
    ]


# ---- Ingest endpoint (بدون API Key) ----
@app.post("/ingest/{endpoint_id}")
async def ingest(endpoint_id: str, request: Request, db: Session = Depends(get_db)):
    ep = (
        db.query(Endpoint)
        .filter(Endpoint.id == endpoint_id, Endpoint.is_enabled == True)  # noqa: E712
        .first()
    )
    if not ep:
        raise HTTPException(404, "Endpoint not found or disabled")

    raw_body = await request.body()
    body_text = raw_body.decode("utf-8", errors="replace")

    headers = dict(request.headers)
    event = Event(
        endpoint_id=ep.id,
        headers_json=json.dumps(headers, ensure_ascii=False),
        body_text=body_text,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    dests = db.query(Destination).filter(Destination.endpoint_id == ep.id).all()
    if not dests:
        return {"event_id": event.id, "queued": 0, "note": "No destinations configured"}

    count = 0
    for dest in dests:
        delivery = Delivery(event_id=event.id, destination_id=dest.id, status="pending", attempt=0)
        db.add(delivery)
        db.commit()
        db.refresh(delivery)

        deliver_event.delay(delivery.id)
        count += 1

    return {"event_id": event.id, "queued": count}
