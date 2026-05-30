"""PTG Procurement Pilot — FastAPI application."""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

# Load .env if present
load_dotenv()

from database import (
    add_note,
    create_rfq,
    get_all_open,
    get_rfq,
    get_next_rfq_number,
    get_rfq_by_id,
    increment_followup,
    init_db,
    update_rfq_status,
    STATUS_CHOICES,
)
from claude_service import classify_email, generate_draft
from templates import analyze_page, dashboard_page, new_rfq_page


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="PTG Procurement Pilot", lifespan=lifespan)


# ── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    rfqs = await get_all_open()
    return dashboard_page(rfqs)


# ── New RFQ ──────────────────────────────────────────────────────────────────

@app.get("/new", response_class=HTMLResponse)
async def new_rfq_form():
    suggested = await get_next_rfq_number()
    return new_rfq_page(suggested_id=suggested)


@app.post("/new", response_class=HTMLResponse)
async def new_rfq_submit(
    rfq_id: str = Form(...),
    supplier_name: str = Form(...),
    supplier_email: str = Form(...),
    subject: str = Form(...),
    sent_at: str = Form(...),
):
    rfq_id = rfq_id.strip()
    supplier_name = supplier_name.strip()
    supplier_email = supplier_email.strip()
    subject = subject.strip()
    sent_at = sent_at.strip()

    existing = await get_rfq(rfq_id)
    if existing:
        suggested = await get_next_rfq_number()
        return new_rfq_page(
            suggested_id=suggested,
            error=f"RFQ ID '{rfq_id}' already exists. Please use a different ID.",
        )

    await create_rfq(
        rfq_id=rfq_id,
        supplier_name=supplier_name,
        supplier_email=supplier_email,
        subject=subject,
        sent_at=sent_at,
    )
    return RedirectResponse(url="/", status_code=303)


# ── Analyze Email ─────────────────────────────────────────────────────────────

@app.get("/analyze", response_class=HTMLResponse)
async def analyze_form():
    rfqs = await get_all_open()
    return analyze_page(rfqs=rfqs)


@app.post("/analyze", response_class=HTMLResponse)
async def analyze_submit(
    supplier_name: str = Form(default=""),
    supplier_email: str = Form(default=""),
    subject: str = Form(...),
    body: str = Form(...),
    rfq_id: str = Form(default=""),
):
    supplier_name = supplier_name.strip()
    supplier_email = supplier_email.strip()
    subject = subject.strip()
    body = body.strip()
    rfq_id = rfq_id.strip()

    form_values = {
        "supplier_name": supplier_name,
        "supplier_email": supplier_email,
        "subject": subject,
        "body": body,
        "rfq_id": rfq_id,
    }

    rfqs = await get_all_open()

    try:
        sender = supplier_email or supplier_name or "unknown"
        result = await classify_email(subject=subject, body=body, sender=sender)
    except Exception as exc:
        return analyze_page(
            rfqs=rfqs,
            form_values=form_values,
            error=f"Claude API error during classification: {exc}",
        )

    rfq_dict = None
    if rfq_id:
        rfq_dict = await get_rfq(rfq_id)

    try:
        draft = await generate_draft(
            rfq_dict=rfq_dict,
            email_subject=subject,
            email_body=body,
            classification=result.get("classification", "other"),
            requires_engineer=result.get("requires_engineer", False),
            supplier_name=supplier_name or result.get("supplier_name") or "",
        )
    except Exception as exc:
        return analyze_page(
            rfqs=rfqs,
            result=result,
            form_values=form_values,
            error=f"Claude API error during draft generation: {exc}",
        )

    # Auto-update linked RFQ if classification gives us useful info
    if rfq_dict:
        if result.get("classification") in (
            "supplier_quote_received",
            "supplier_replied",
            "supplier_delivery_confirmed",
            "supplier_acknowledgment",
        ):
            try:
                await update_rfq_status(rfq_dict["id"], "supplier_replied")
            except Exception:
                pass
        if result.get("delivery_date"):
            from datetime import datetime
            import aiosqlite
            from database import DB_PATH
            now = datetime.utcnow().isoformat()
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE rfqs SET delivery_date=?, updated_at=? WHERE id=?",
                    (result["delivery_date"], now, rfq_dict["id"]),
                )
                await db.commit()

    return analyze_page(
        rfqs=rfqs,
        result=result,
        draft=draft,
        form_values=form_values,
    )


# ── RFQ actions ───────────────────────────────────────────────────────────────

@app.post("/rfq/{rfq_db_id}/update-status", response_class=HTMLResponse)
async def rfq_update_status(rfq_db_id: int, status: str = Form(...)):
    status = status.strip()
    if status not in STATUS_CHOICES:
        rfqs = await get_all_open()
        return dashboard_page(rfqs)
    await update_rfq_status(rfq_db_id, status)
    return RedirectResponse(url="/", status_code=303)


@app.post("/rfq/{rfq_db_id}/note", response_class=HTMLResponse)
async def rfq_add_note(rfq_db_id: int, note: str = Form(...)):
    note = note.strip()
    if note:
        await add_note(rfq_db_id, note)
    return RedirectResponse(url="/", status_code=303)
