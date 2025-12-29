import requests
from datetime import datetime
from celery import Celery
from sqlalchemy.orm import Session
from .config import settings
from .db import SessionLocal
from .models import Delivery, Event, Destination

celery_app = Celery("relay", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

@celery_app.task(bind=True, max_retries=5, default_retry_delay=10)
def deliver_event(self, delivery_id: str):
    db: Session = SessionLocal()
    try:
        delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
        if not delivery:
            return

        event = db.query(Event).filter(Event.id == delivery.event_id).first()
        dest = db.query(Destination).filter(Destination.id == delivery.destination_id).first()
        if not event or not dest:
            delivery.status = "failed"
            delivery.last_error = "Missing event/destination"
            delivery.updated_at = datetime.utcnow()
            db.commit()
            return

        delivery.attempt += 1
        delivery.updated_at = datetime.utcnow()
        db.commit()

        headers = {dest.secret_header_name: dest.secret_value, "Content-Type": "application/json"}
        resp = requests.request(dest.method.upper(), dest.url, data=event.body_text.encode("utf-8"), headers=headers, timeout=15)

        delivery.last_http_status = resp.status_code
        if 200 <= resp.status_code < 300:
            delivery.status = "success"
            delivery.last_error = None
        else:
            delivery.status = "failed"
            delivery.last_error = f"Non-2xx response: {resp.status_code}"
            db.commit()
            raise self.retry(exc=Exception(delivery.last_error))

        delivery.updated_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        # اگر به retry رفت، اینجا هم می‌تونه ثبت کنه
        delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
        if delivery:
            delivery.status = "failed"
            delivery.last_error = str(e)
            delivery.updated_at = datetime.utcnow()
            db.commit()
        raise
    finally:
        db.close()
