from __future__ import annotations
import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from ..database import get_db, SessionLocal
from ..models.invoice import Invoice, ProcessingStage

router = APIRouter()


@router.get("/invoice/{invoice_id}")
async def stream_invoice_stages(invoice_id: str, request: Request):
    """
    Streams processing stage events for an invoice via Server-Sent Events (SSE).
    Watches database updates and yields each stage completion.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        seen_stages = set()
        retries = 0
        max_retries = 1200  # max 60 seconds (50ms intervals)

        while retries < max_retries:
            if await request.is_disconnected():
                break

            db: Session = SessionLocal()
            try:
                invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
                if not invoice:
                    yield json.dumps({"event": "error", "message": "Invoice not found"})
                    break

                stages = (
                    db.query(ProcessingStage)
                    .filter(ProcessingStage.invoice_id == invoice_id)
                    .order_by(ProcessingStage.started_at.asc())
                    .all()
                )

                for stage in stages:
                    stage_key = f"{stage.stage_name}_{stage.status}"
                    if stage_key not in seen_stages:
                        seen_stages.add(stage_key)
                        data = {
                            "invoice_id": invoice_id,
                            "stage_name": stage.stage_name,
                            "status": stage.status,
                            "started_at": stage.started_at.isoformat() if stage.started_at else None,
                            "completed_at": stage.completed_at.isoformat() if stage.completed_at else None,
                            "duration_ms": stage.duration_ms,
                            "findings": stage.findings,
                            "error_message": stage.error_message,
                            "invoice_status": invoice.status,
                        }
                        yield json.dumps(data)

                # Check if final decision is reached
                if invoice.status in ["APPROVED", "REVIEW", "REJECTED"]:
                    # Yield complete event
                    yield json.dumps({
                        "event": "done",
                        "status": invoice.status,
                        "invoice_id": invoice_id,
                    })
                    break

            finally:
                db.close()

            await asyncio.sleep(0.05)
            retries += 1

    return EventSourceResponse(event_generator())
