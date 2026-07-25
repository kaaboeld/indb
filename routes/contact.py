"""
Contact Form Route

Receives form submissions from the presentation site and
forwards them via Resend API to the configured recipient.
Email address and API key are stored as Fly.io secrets — never in code.
"""
import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/v2", tags=["contact"])

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
CONTACT_TO    = os.getenv("CONTACT_EMAIL", "")    # Set as Fly secret


class ContactRequest(BaseModel):
    name: str
    email: str
    message: str
    consent: bool = False


@router.post("/contact")
async def send_contact(payload: ContactRequest):
    """
    Forward a contact form submission via Resend.
    RESEND_API_KEY and CONTACT_EMAIL must be set as Fly.io secrets.
    """
    if not RESEND_API_KEY or not CONTACT_TO:
        raise HTTPException(status_code=503, detail="Email service not configured")

    if not payload.email or not payload.message:
        raise HTTPException(status_code=422, detail="Email and message are required")

    consent_label = (
        "Yes — data processing, newsletters, privacy policy"
        if payload.consent
        else "Not provided"
    )
    consent_color = "#4ade80" if payload.consent else "#666"

    html_body = f"""
    <div style="font-family: monospace; background:#0a0a0a; color:#fff; padding:32px; max-width:600px;">
      <div style="color:#E53E3E; font-size:11px; letter-spacing:0.5em; text-transform:uppercase; margin-bottom:24px;">
        INDB CONTACT FORM
      </div>
      <table style="width:100%; border-collapse:collapse;">
        <tr>
          <td style="color:#666; font-size:11px; padding:8px 0; width:80px;">NAME</td>
          <td style="color:#fff; font-size:14px; padding:8px 0;">{payload.name}</td>
        </tr>
        <tr>
          <td style="color:#666; font-size:11px; padding:8px 0;">EMAIL</td>
          <td style="color:#E53E3E; font-size:14px; padding:8px 0;">
            <a href="mailto:{payload.email}" style="color:#E53E3E;">{payload.email}</a>
          </td>
        </tr>
        <tr>
          <td style="color:#666; font-size:11px; padding:8px 0;">CONSENT</td>
          <td style="color:{consent_color}; font-size:14px; padding:8px 0;">{consent_label}</td>
        </tr>
      </table>
      <div style="margin-top:24px; padding:16px; border:1px solid #222; background:#111;">
        <div style="color:#666; font-size:11px; letter-spacing:0.3em; margin-bottom:12px;">MESSAGE</div>
        <div style="color:#ccc; font-size:14px; line-height:1.6; white-space:pre-wrap;">{payload.message}</div>
      </div>
      <div style="margin-top:32px; color:#333; font-size:10px; letter-spacing:0.3em;">
        SENT VIA INDB PRESENTATION · indb-presentation.fly.dev
      </div>
    </div>
    """

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from":    "INDB Contact <mail@indb.tech>",
                "to":      [CONTACT_TO],
                "reply_to": payload.email,
                "subject": f"INDB Inquiry from {payload.name}",
                "html":    html_body,
            },
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"Email service error: {resp.text}")

    return {"status": "sent"}
