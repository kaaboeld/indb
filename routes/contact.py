"""
Contact Form Route

Receives form submissions from the presentation site and
forwards them via Resend API to the configured recipient.
Email address and API key are stored as Fly.io secrets — never in code.
"""
import html
import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.routing import ContentNegotiationRoute

router = APIRouter(prefix="/api/v2", tags=["contact"], route_class=ContentNegotiationRoute)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
CONTACT_TO    = os.getenv("CONTACT_EMAIL", "")    # Set as Fly secret


class CampaignInfo(BaseModel):
    utm_source: str = Field(default="", max_length=200)
    utm_medium: str = Field(default="", max_length=200)
    utm_campaign: str = Field(default="", max_length=200)
    utm_content: str = Field(default="", max_length=200)
    utm_term: str = Field(default="", max_length=200)
    landing_page: str = Field(default="", max_length=500)
    referrer: str = Field(default="", max_length=500)


class ContactRequest(BaseModel):
    name: str
    email: str
    message: str
    consent: bool = False
    campaign: CampaignInfo = Field(default_factory=CampaignInfo)


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
    campaign = payload.campaign

    def cell(value: str) -> str:
        return html.escape(value or "—")

    html_body = f"""
    <div style="font-family: monospace; background:#0a0a0a; color:#fff; padding:32px; max-width:600px;">
      <div style="color:#E53E3E; font-size:11px; letter-spacing:0.5em; text-transform:uppercase; margin-bottom:24px;">
        INDB CONTACT FORM
      </div>
      <table style="width:100%; border-collapse:collapse;">
        <tr>
          <td style="color:#666; font-size:11px; padding:8px 0; width:80px;">NAME</td>
          <td style="color:#fff; font-size:14px; padding:8px 0;">{cell(payload.name)}</td>
        </tr>
        <tr>
          <td style="color:#666; font-size:11px; padding:8px 0;">EMAIL</td>
          <td style="color:#E53E3E; font-size:14px; padding:8px 0;">
            <a href="mailto:{cell(payload.email)}" style="color:#E53E3E;">{cell(payload.email)}</a>
          </td>
        </tr>
        <tr>
          <td style="color:#666; font-size:11px; padding:8px 0;">CONSENT</td>
          <td style="color:{consent_color}; font-size:14px; padding:8px 0;">{consent_label}</td>
        </tr>
      </table>
      <div style="margin-top:24px; padding:16px; border:1px solid #222; background:#111;">
        <div style="color:#666; font-size:11px; letter-spacing:0.3em; margin-bottom:12px;">MESSAGE</div>
        <div style="color:#ccc; font-size:14px; line-height:1.6; white-space:pre-wrap;">{cell(payload.message)}</div>
      </div>
      <table style="width:100%; border-collapse:collapse; margin-top:24px;">
        <tr><td style="color:#666; font-size:11px; padding:6px 0; width:120px;">SOURCE</td><td style="color:#ccc; font-size:13px; padding:6px 0;">{cell(campaign.utm_source)}</td></tr>
        <tr><td style="color:#666; font-size:11px; padding:6px 0;">MEDIUM</td><td style="color:#ccc; font-size:13px; padding:6px 0;">{cell(campaign.utm_medium)}</td></tr>
        <tr><td style="color:#666; font-size:11px; padding:6px 0;">CAMPAIGN</td><td style="color:#ccc; font-size:13px; padding:6px 0;">{cell(campaign.utm_campaign)}</td></tr>
        <tr><td style="color:#666; font-size:11px; padding:6px 0;">CONTENT</td><td style="color:#ccc; font-size:13px; padding:6px 0;">{cell(campaign.utm_content)}</td></tr>
        <tr><td style="color:#666; font-size:11px; padding:6px 0;">TERM</td><td style="color:#ccc; font-size:13px; padding:6px 0;">{cell(campaign.utm_term)}</td></tr>
        <tr><td style="color:#666; font-size:11px; padding:6px 0;">LANDING</td><td style="color:#ccc; font-size:13px; padding:6px 0;">{cell(campaign.landing_page)}</td></tr>
        <tr><td style="color:#666; font-size:11px; padding:6px 0;">REFERRER</td><td style="color:#ccc; font-size:13px; padding:6px 0;">{cell(campaign.referrer)}</td></tr>
      </table>
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
