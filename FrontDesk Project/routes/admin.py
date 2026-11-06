"""Admin pages. Every handler requires role=admin; forms also require CSRF."""
from __future__ import annotations

from datetime import datetime, date, time, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.ai_service import get_setting, get_business_hours, set_ai_api_key, set_setting
from app.auth import hash_password, is_weak_password, verify_password
from app.config import settings
from app.database import get_db
from app.models import Appointment, Conversation, KnowledgeItem, Message
from app.security import (
    block_demo_sensitive_action, csrf_token as make_csrf, ensure_password_hash,
    require_admin, verify_csrf,
)
from app.templating import templates

router = APIRouter(tags=["admin"], dependencies=[Depends(require_admin)])
APPOINTMENT_STATUSES = {"confirmed", "cancelled", "completed"}



ALLOWED_DEMO_CHANGES_KEY = "_demo_allowed_changes"


def demo_writes(request: Request) -> dict:
    return request.session.get(ALLOWED_DEMO_CHANGES_KEY) or {}


def demo_created(request: Request, kind: str, item_id: int, description: str) -> None:
    """Record only rows created through this specific sandbox session.

    Generic delete/edit endpoints use this server-side allowlist; a visitor
    cannot delete or edit the seeded fixtures or another reviewer's rows.
    No production credential, API key, or account setting is ever covered.
    """
    if not (settings.demo_mode and request.session.get("demo_session")):
        return
    changes = demo_writes(request)
    entries = list(changes.get(kind, []))
    entries.append({"id": item_id, "description": description[:140]})
    # Keep Starlette's signed client-side session bounded.
    changes[kind] = entries[-25:]
    request.session[ALLOWED_DEMO_CHANGES_KEY] = changes


def demo_can_mutate(request: Request, kind: str, item_id: int) -> bool:
    return any(entry.get("id") == item_id for entry in demo_writes(request).get(kind, []))


def _tpl(request: Request, name: str, context: dict | None = None):
    ctx = {
        "request": request, "csrf_token": make_csrf(request),
        "demo_mode": settings.demo_mode,
        "demo_session": bool(settings.demo_mode and request.session.get("demo_session")),
        "upcoming_count": 0, "business_name": "FrontDesk AI",
        "demo_writes": demo_writes(request),
        "demo_can_mutate": demo_can_mutate,
    }
    if context:
        ctx.update(context)
    return templates.TemplateResponse(request, name, ctx)


def _page_params(request: Request) -> tuple[int, int]:
    try:
        page = max(1, min(100000, int(request.query_params.get("page", "1"))))
    except ValueError:
        page = 1
    return page, (page - 1) * settings.page_size


def _pagination(request: Request, total: int) -> dict:
    page = max(1, int(request.query_params.get("page", "1")) if request.query_params.get("page", "1").isdigit() else 1)
    pages = max(1, (total + settings.page_size - 1) // settings.page_size)
    return {"page": min(page, pages), "pages": pages, "total": total}


def _business_context(db: Session) -> dict:
    today = datetime.combine(date.today(), time.min)
    upcoming = db.query(func.count(Appointment.id)).filter(Appointment.appointment_time >= today, Appointment.status == "confirmed").scalar() or 0
    return {"business_name": get_setting(db, "business_name", settings.business_name), "upcoming_count": upcoming}


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    today = datetime.combine(date.today(), time.min)
    tomorrow = today + timedelta(days=1)
    month_start = today.replace(day=1)
    conv_count = db.query(func.count(Conversation.id)).scalar() or 0
    msg_count = db.query(func.count(Message.id)).scalar() or 0
    appt_count = db.query(func.count(Appointment.id)).scalar() or 0
    upcoming_count = db.query(func.count(Appointment.id)).filter(Appointment.appointment_time >= today, Appointment.status == "confirmed").scalar() or 0
    today_count = db.query(func.count(Appointment.id)).filter(Appointment.appointment_time >= today, Appointment.appointment_time < tomorrow, Appointment.status != "cancelled").scalar() or 0
    completed_count = db.query(func.count(Appointment.id)).filter(Appointment.status == "completed").scalar() or 0
    attended_conv = db.query(func.count(func.distinct(Appointment.conversation_id))).filter(Appointment.status != "cancelled").scalar() or 0
    conversion = round(attended_conv * 100 / conv_count) if conv_count else 0
    this_month = db.query(func.count(Appointment.id)).filter(Appointment.appointment_time >= month_start).scalar() or 0
    kb_count = db.query(func.count(KnowledgeItem.id)).scalar() or 0
    recent = db.query(Conversation).options(selectinload(Conversation.messages)).order_by(Conversation.updated_at.desc()).limit(5).all()
    upcoming = db.query(Appointment).filter(Appointment.appointment_time >= today, Appointment.status == "confirmed").order_by(Appointment.appointment_time.asc()).limit(5).all()
    # Real daily conversation counts for the last seven days, normalized in Python.
    activity_start = today - timedelta(days=6)
    counts = dict(db.query(func.date(Conversation.created_at), func.count(Conversation.id)).filter(Conversation.created_at >= activity_start).group_by(func.date(Conversation.created_at)).all())
    activity = [{"label": (activity_start + timedelta(days=i)).strftime("%a"), "count": counts.get((activity_start + timedelta(days=i)).date().isoformat(), 0)} for i in range(7)]
    max_activity = max([1] + [entry["count"] for entry in activity])
    return _tpl(request, "admin.html", _business_context(db) | {
        "active_page": "dashboard", "conv_count": conv_count, "msg_count": msg_count,
        "appt_count": appt_count, "upcoming_count": upcoming_count, "today_count": today_count,
        "completed_count": completed_count, "this_month": this_month, "kb_count": kb_count,
        "conversion": conversion, "recent": recent, "upcoming": upcoming,
        "activity": activity, "max_activity": max_activity,
    })


@router.get("/admin/knowledge", response_class=HTMLResponse)
async def knowledge_list(request: Request, db: Session = Depends(get_db), q: str = ""):
    query = db.query(KnowledgeItem)
    if q.strip():
        term = f"%{q.strip()[:100]}%"
        query = query.filter(KnowledgeItem.question.ilike(term) | KnowledgeItem.answer.ilike(term))
    items = query.order_by(KnowledgeItem.id.desc()).all()
    return _tpl(request, "knowledge.html", _business_context(db) | {"active_page": "knowledge", "items": items, "q": q.strip()[:100]})


@router.get("/admin/knowledge/{item_id}/edit", response_class=HTMLResponse)
async def knowledge_edit(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.query(KnowledgeItem).filter(KnowledgeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    return _tpl(request, "knowledge_edit.html", _business_context(db) | {"active_page": "knowledge", "item": item})


@router.post("/admin/knowledge/{item_id}/edit")
async def knowledge_update(item_id: int, request: Request, question: str = Form(...), answer: str = Form(...), category: str = Form("general"), is_active: bool = Form(False), csrf_token: str = Form(""), db: Session = Depends(get_db), _: None = Depends(require_admin)):
    verify_csrf(request, csrf_token)
    if settings.demo_mode and not demo_can_mutate(request, "knowledge", item_id):
        raise HTTPException(status_code=403, detail="You can only edit answers you added in this demo session")
    item = db.query(KnowledgeItem).filter(KnowledgeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    item.question, item.answer = question.strip()[:500], answer.strip()
    item.category, item.is_active = category.strip()[:100] or "general", is_active
    if settings.demo_mode:
        item.question = question.strip()[:500]
        item.answer = answer.strip()
    db.commit()
    return RedirectResponse("/admin/knowledge?updated=1", status_code=303)


@router.post("/admin/knowledge")
async def knowledge_add(request: Request, question: str = Form(...), answer: str = Form(...), category: str = Form("general"), csrf_token: str = Form(""), db: Session = Depends(get_db), _: None = Depends(require_admin)):
    verify_csrf(request, csrf_token)
    if not question.strip() or not answer.strip():
        return RedirectResponse("/admin/knowledge?error=empty", status_code=303)
    item = KnowledgeItem(question=question.strip()[:500], answer=answer.strip(), category=category.strip()[:100] or "general")
    db.add(item)
    db.commit()
    db.refresh(item)
    demo_created(request, "knowledge", item.id, item.question)
    return RedirectResponse("/admin/knowledge?added=1", status_code=303)


@router.post("/admin/knowledge/{item_id}/delete")
async def knowledge_delete(item_id: int, request: Request, csrf_token: str = Form(""), db: Session = Depends(get_db), _: None = Depends(require_admin)):
    verify_csrf(request, csrf_token)
    if settings.demo_mode and not demo_can_mutate(request, "knowledge", item_id):
        raise HTTPException(status_code=403, detail="You can only delete answers you added in this demo session")
    item = db.query(KnowledgeItem).filter(KnowledgeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    db.delete(item)
    db.commit()
    return RedirectResponse("/admin/knowledge?deleted=1", status_code=303)


@router.get("/admin/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    demo = bool(settings.demo_mode and request.session.get("demo_session"))
    current = {"ai_base_url": "Not available in demo" if demo else get_setting(db, "ai_base_url", settings.ai_base_url), "ai_api_key_set": bool(get_setting(db, "ai_api_key", "")) and not demo, "ai_api_key": "", "ai_model": "Local guided demo" if demo else get_setting(db, "ai_model", settings.ai_model), "business_name": get_setting(db, "business_name", settings.business_name), "opening_hour": get_setting(db, "opening_hour", "9"), "closing_hour": get_setting(db, "closing_hour", "18"), "closed_days": get_setting(db, "closed_days", "sunday"), "holiday_dates": get_setting(db, "holiday_dates", "")}
    return _tpl(request, "settings.html", _business_context(db) | {"active_page": "settings", "current": current, "admin_name": get_setting(db, "admin_username", "admin")})


@router.post("/admin/settings")
async def save_settings(request: Request, ai_base_url: str = Form(""), ai_api_key: str = Form(""), ai_model: str = Form(""), business_name: str = Form(...), opening_hour: str = Form("9"), closing_hour: str = Form("18"), closed_days: str = Form("sunday"), holiday_dates: str = Form(""), csrf_token: str = Form(""), db: Session = Depends(get_db), _: None = Depends(require_admin)):
    block_demo_sensitive_action(request)
    verify_csrf(request, csrf_token)
    try:
        opening, closing = int(opening_hour), int(closing_hour)
        if not 0 <= opening < closing <= 24:
            raise ValueError
        holidays = [d.strip() for d in holiday_dates.split(",") if d.strip()]
        for value in holidays:
            date.fromisoformat(value)
    except ValueError:
        return RedirectResponse("/admin/settings?error=schedule", status_code=303)
    set_setting(db, "ai_base_url", ai_base_url.strip())
    if ai_api_key.strip():
        set_ai_api_key(db, ai_api_key.strip())
    set_setting(db, "ai_model", ai_model.strip())
    set_setting(db, "business_name", business_name.strip()[:200])
    set_setting(db, "opening_hour", str(opening))
    set_setting(db, "closing_hour", str(closing))
    set_setting(db, "closed_days", closed_days.strip().lower() or "sunday")
    set_setting(db, "holiday_dates", ",".join(holidays))
    return RedirectResponse("/admin/settings?saved=1", status_code=303)


@router.post("/admin/change-password")
async def change_password(request: Request, current_password: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...), csrf_token: str = Form(""), db: Session = Depends(get_db), _: None = Depends(require_admin)):
    block_demo_sensitive_action(request)
    verify_csrf(request, csrf_token)
    stored = ensure_password_hash(db)
    if not stored or not verify_password(current_password, stored):
        return RedirectResponse("/admin/settings?error=wrong_password", status_code=303)
    if new_password != confirm_password:
        return RedirectResponse("/admin/settings?error=mismatch", status_code=303)
    if len(new_password) < 8 or is_weak_password(new_password):
        return RedirectResponse("/admin/settings?error=too_short", status_code=303)
    set_setting(db, "admin_password", hash_password(new_password))
    return RedirectResponse("/admin/settings?password_changed=1", status_code=303)


@router.get("/admin/appointments", response_class=HTMLResponse)
async def appointments_list(request: Request, db: Session = Depends(get_db), status: str = "", q: str = ""):
    page, offset = _page_params(request)
    query = db.query(Appointment)
    if status in APPOINTMENT_STATUSES:
        query = query.filter(Appointment.status == status)
    if q.strip():
        term = f"%{q.strip()[:100]}%"
        query = query.filter(Appointment.customer_name.ilike(term) | Appointment.customer_phone.ilike(term) | Appointment.service.ilike(term))
    total = query.count()
    items = query.order_by(Appointment.appointment_time.asc()).offset(offset).limit(settings.page_size).all()
    today = datetime.combine(date.today(), time.min)
    confirmed_count = db.query(func.count(Appointment.id)).filter(Appointment.status == "confirmed").scalar() or 0
    today_count = db.query(func.count(Appointment.id)).filter(Appointment.appointment_time >= today, Appointment.appointment_time < today + timedelta(days=1), Appointment.status != "cancelled").scalar() or 0
    return _tpl(request, "appointments.html", _business_context(db) | {"active_page": "appointments", "items": items, "status": status, "q": q.strip()[:100], "confirmed_count": confirmed_count, "today_count": today_count, **_pagination(request, total)})


@router.post("/admin/appointments/{appt_id}/status")
async def update_appointment_status(appt_id: int, request: Request, status: str = Form(...), csrf_token: str = Form(""), db: Session = Depends(get_db), _: None = Depends(require_admin)):
    verify_csrf(request, csrf_token)
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if status not in APPOINTMENT_STATUSES:
        raise HTTPException(status_code=422, detail="Unsupported appointment status")
    appt.status = status
    db.commit()
    return RedirectResponse("/admin/appointments?updated=1", status_code=303)


@router.get("/admin/conversations", response_class=HTMLResponse)
async def conversations_list(request: Request, db: Session = Depends(get_db), q: str = ""):
    page, offset = _page_params(request)
    query = db.query(Conversation)
    if q.strip():
        term = f"%{q.strip()[:100]}%"
        query = query.filter(Conversation.customer_name.ilike(term) | Conversation.customer_phone.ilike(term))
    total = query.count()
    items = query.options(selectinload(Conversation.messages)).order_by(Conversation.updated_at.desc()).offset(offset).limit(settings.page_size).all()
    return _tpl(request, "conversations.html", _business_context(db) | {"active_page": "conversations", "items": items, "q": q.strip()[:100], **_pagination(request, total)})


@router.get("/admin/conversations/{conv_id}", response_class=HTMLResponse)
async def conversation_detail(conv_id: int, request: Request, db: Session = Depends(get_db)):
    conv = db.query(Conversation).options(selectinload(Conversation.messages)).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _tpl(request, "conversation_detail.html", _business_context(db) | {"active_page": "conversations", "conv": conv})


@router.post("/admin/conversations/{conv_id}/delete")
async def conversation_delete(conv_id: int, request: Request, csrf_token: str = Form(""), db: Session = Depends(get_db), _: None = Depends(require_admin)):
    verify_csrf(request, csrf_token)
    if settings.demo_mode and not demo_can_mutate(request, "conversation", conv_id):
        raise HTTPException(status_code=403, detail="You can only delete conversations you started in this demo session")
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return RedirectResponse("/admin/conversations?deleted=1", status_code=303)
