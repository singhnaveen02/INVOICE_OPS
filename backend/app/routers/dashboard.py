from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, Any, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..database import get_db
from ..models.invoice import Invoice, ProcessingStage
from ..models.purchase_order import PurchaseOrder
from ..models.vendor import Vendor
from ..models.decision import Decision, AuditLog

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    total_invoices = db.query(Invoice).count()
    approved = db.query(Invoice).filter(Invoice.status == "APPROVED").count()
    review = db.query(Invoice).filter(Invoice.status == "REVIEW").count()
    rejected = db.query(Invoice).filter(Invoice.status == "REJECTED").count()
    pending = db.query(Invoice).filter(Invoice.status.in_(["PENDING", "PROCESSING"])).count()

    total_value = db.query(func.coalesce(func.sum(Invoice.grand_total), 0.0)).scalar() or 0.0
    approved_value = (
        db.query(func.coalesce(func.sum(Invoice.grand_total), 0.0))
        .filter(Invoice.status == "APPROVED")
        .scalar()
        or 0.0
    )
    duplicate_count = db.query(Invoice).filter(Invoice.is_duplicate == True).count()

    # Average processing time from completed ProcessingStages
    avg_duration = (
        db.query(func.avg(ProcessingStage.duration_ms))
        .filter(ProcessingStage.status == "COMPLETED", ProcessingStage.duration_ms.isnot(None))
        .scalar()
    )

    return {
        "total_invoices": total_invoices,
        "approved_invoices": approved,
        "pending_review": review,
        "rejected_invoices": rejected,
        "pending_processing": pending,
        "total_value": round(float(total_value), 2),
        "approved_value": round(float(approved_value), 2),
        "duplicate_count": duplicate_count,
        "avg_processing_time_ms": round(float(avg_duration or 450.0), 1),
    }


@router.get("/trends")
def get_invoice_trends(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    # 30 day trends
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=29)

    invoices = (
        db.query(Invoice.created_at, Invoice.status, Invoice.grand_total)
        .filter(Invoice.created_at >= start_date)
        .all()
    )

    # Bucket by day
    days_map: Dict[str, Dict[str, Any]] = {}
    for i in range(30):
        d = (start_date + timedelta(days=i)).isoformat()
        days_map[d] = {
            "date": d,
            "total": 0,
            "approved": 0,
            "review": 0,
            "rejected": 0,
            "value": 0.0,
        }

    for inv in invoices:
        if not inv.created_at:
            continue
        day_str = inv.created_at.date().isoformat()
        if day_str in days_map:
            days_map[day_str]["total"] += 1
            if inv.status == "APPROVED":
                days_map[day_str]["approved"] += 1
            elif inv.status == "REVIEW":
                days_map[day_str]["review"] += 1
            elif inv.status == "REJECTED":
                days_map[day_str]["rejected"] += 1
            days_map[day_str]["value"] += inv.grand_total or 0.0

    result = list(days_map.values())
    for item in result:
        item["value"] = round(item["value"], 2)
    return result


@router.get("/status-distribution")
def get_status_distribution(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    rows = (
        db.query(Invoice.status, func.count(Invoice.id))
        .group_by(Invoice.status)
        .all()
    )
    status_colors = {
        "APPROVED": "#16a34a",
        "REVIEW": "#ca8a04",
        "REJECTED": "#dc2626",
        "PENDING": "#9333ea",
        "PROCESSING": "#2563eb",
    }
    return [
        {
            "status": status,
            "count": count,
            "color": status_colors.get(status, "#64748b"),
        }
        for status, count in rows
    ]


@router.get("/po-utilization")
def get_po_utilization(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    pos = db.query(PurchaseOrder).order_by(desc(PurchaseOrder.utilized_amount)).limit(8).all()
    out = []
    for po in pos:
        total = po.total_amount or 0.01
        utilized = po.utilized_amount or 0.0
        pct = min(100.0, round((utilized / total) * 100, 1))
        out.append({
            "po_id": po.id,
            "po_number": po.po_number,
            "vendor_name": po.vendor.name if po.vendor else "Unknown",
            "total_amount": round(total, 2),
            "utilized_amount": round(utilized, 2),
            "remaining_amount": round(po.remaining_amount or (total - utilized), 2),
            "utilization_pct": pct,
            "status": po.status,
        })
    return out


@router.get("/recent-activity")
def get_recent_activity(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    # Fetch from AuditLog if available, else recent invoices
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10).all()
    if logs:
        return [
            {
                "id": log.id,
                "invoice_id": log.invoice_id,
                "action": log.action,
                "actor": log.actor,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "notes": log.notes,
            }
            for log in logs
        ]

    # Fallback to recent invoices
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).limit(10).all()
    return [
        {
            "id": inv.id,
            "invoice_id": inv.id,
            "action": f"Invoice {inv.invoice_number or inv.original_filename} - {inv.status}",
            "actor": "System",
            "timestamp": inv.created_at.isoformat() if inv.created_at else None,
            "notes": f"Amount: ${inv.grand_total:.2f}" if inv.grand_total else "Pending processing",
        }
        for inv in invoices
    ]
