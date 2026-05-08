"""
alerts.py — Email alerts for price changes and description updates.

Set email_enabled=True in config.py and fill in SMTP details.
Uses environment variable SMTP_PASSWORD for security.
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from config import SETTINGS
from database import get_recent_changes, get_conn

log = logging.getLogger(__name__)


def _build_email_html(changes: list[dict]) -> str:
    rows = ""
    for c in changes:
        ts = c["detected_at"][:16].replace("T", " ")
        if c["change_type"] == "price":
            pct = c["pct_change"] or 0
            colour = "#a32d2d" if pct > 0 else "#2d7a0f"
            badge = f'<span style="color:{colour};font-weight:bold">{"▲" if pct > 0 else "▼"} {abs(pct):.1f}%</span>'
        elif c["change_type"] == "description":
            badge = '<span style="color:#854F0B">📝 Description changed</span>'
        else:
            badge = '<span style="color:#a32d2d">⚠ Price unavailable</span>'

        rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0ee">{ts}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0ee"><b>{c['brand']}</b></td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0ee">{c['size']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0ee">{badge}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0ee">
            {('£' + str(c['old_value'])) if c['old_value'] and c['change_type'] == 'price' else (c.get('old_value') or '')[:40]}
          </td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0ee">
            {('£' + str(c['new_value'])) if c['new_value'] and c['change_type'] == 'price' else (c.get('new_value') or '')[:40]}
          </td>
        </tr>"""

    return f"""
    <html><body style="font-family:system-ui,sans-serif;background:#f5f5f3;padding:24px">
    <div style="max-width:700px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden;border:1px solid #e5e5e5">
      <div style="background:#185FA5;color:#fff;padding:20px 24px">
        <h1 style="font-size:18px;margin:0">⚠ Big Whey Price Alert</h1>
        <p style="margin:4px 0 0;opacity:.85;font-size:13px">{len(changes)} change(s) detected — {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}</p>
      </div>
      <div style="padding:20px 24px">
        <table style="width:100%;border-collapse:collapse">
          <thead>
            <tr style="background:#f8f8f6">
              <th style="padding:8px 12px;text-align:left;font-size:12px;color:#666">Time</th>
              <th style="padding:8px 12px;text-align:left;font-size:12px;color:#666">Brand</th>
              <th style="padding:8px 12px;text-align:left;font-size:12px;color:#666">Size</th>
              <th style="padding:8px 12px;text-align:left;font-size:12px;color:#666">Change</th>
              <th style="padding:8px 12px;text-align:left;font-size:12px;color:#666">Before</th>
              <th style="padding:8px 12px;text-align:left;font-size:12px;color:#666">After</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
        <p style="font-size:12px;color:#aaa;margin-top:16px">
          Open reports/latest.html for the full dashboard · Nutrition X Big Whey Tracker
        </p>
      </div>
    </div>
    </body></html>"""


def send_alert_email(changes: list[dict]):
    """Send email alert for a list of changes."""
    if not SETTINGS.get("email_enabled"):
        return
    if not changes:
        return

    password = os.environ.get("SMTP_PASSWORD") or SETTINGS.get("smtp_password", "")
    if not password:
        log.warning("SMTP_PASSWORD not set — skipping email alert.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"⚠ Big Whey: {len(changes)} price change(s) detected"
    msg["From"] = SETTINGS["email_from"]
    msg["To"] = SETTINGS["email_to"]

    html_body = _build_email_html(changes)
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SETTINGS["smtp_host"], SETTINGS["smtp_port"]) as server:
            server.starttls()
            server.login(SETTINGS["smtp_user"], password)
            server.sendmail(SETTINGS["email_from"], SETTINGS["email_to"], msg.as_string())
        log.info(f"Alert email sent to {SETTINGS['email_to']}")

        # Mark as alerted in DB
        ids = tuple(c["id"] for c in changes if c.get("id"))
        if ids:
            with get_conn() as conn:
                conn.execute(
                    f"UPDATE changes SET alerted=1 WHERE id IN ({','.join('?'*len(ids))})",
                    ids,
                )
    except Exception as exc:
        log.error(f"Failed to send alert email: {exc}")


def send_daily_alerts():
    """Send alerts for any unalerted changes from the last 24 hours."""
    changes = get_recent_changes(days=1)
    unalerted = [c for c in changes if not c.get("alerted")]
    if unalerted:
        send_alert_email(unalerted)
    else:
        log.info("No new alerts to send.")
