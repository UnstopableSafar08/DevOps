#!/usr/bin/env python3
"""
Author      : Sagar Malla
Email       : sagarmalla08@gmail.com
Description : Sends an email with attached HTML security reports and pipeline
              status via SMTP. SMTP credentials are read from environment
              variables. Supports both authenticated and unauthenticated
              (no-auth) SMTP relays.

Environment variables:
  SMTP_SERVER   (default: localhost)
  SMTP_PORT     (default: 25)
  SMTP_USERNAME (optional — skipped if empty)
  SMTP_PASSWORD (optional — skipped if empty)
  EMAIL_FROM    (defaults to SMTP_USERNAME, or SMTP_USER@SMTP_SERVER)

Flags:
  --tls         Enable STARTTLS (required for Gmail / port 587)

Usage:
  python3 send-report.py \\
      --recipients "sagar.malla@esewa.com.np" \\
      --status "SUCCESS" \\
      --reports "depcheck-report.html,sbom-vuln-report.html" \\
      --subject "[CI/CD] Security Report - SUCCESS" \\
      --pipeline-url "https://jenkins.example.com/job/my-job/42"
"""

import os
import sys
import argparse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime


STATUS_COLORS = {
    "SUCCESS": "#059669",
    "FAILURE": "#dc2626",
    "UNSTABLE": "#d97706",
    "ABORTED": "#6b7280",
}


def parse_args():
    p = argparse.ArgumentParser(description="Send security reports via email.")
    p.add_argument("-r", "--recipients", required=True,
                   help="Comma-separated recipient email addresses")
    p.add_argument("-s", "--status", required=True,
                   help="Pipeline status (SUCCESS, FAILURE, UNSTABLE, ABORTED)")
    p.add_argument("-f", "--reports", required=True,
                   help="Comma-separated paths to HTML report files")
    p.add_argument("-S", "--subject",
                   help="Email subject line (auto-generated if omitted)")
    p.add_argument("-u", "--pipeline-url",
                   help="Link to the pipeline run")
    p.add_argument("--tls", action="store_true",
                   help="Enable STARTTLS (required for Gmail / port 587)")
    return p.parse_args()


def build_html_body(status, pipeline_url, report_names):
    color = STATUS_COLORS.get(status.upper(), "#0b9cbd")
    status_upper = status.upper()

    status_icons = {
        "SUCCESS": "\u2713",
        "FAILURE": "\u2718",
        "UNSTABLE": "\u26a0",
        "ABORTED": "\u25a0",
    }
    icon = status_icons.get(status_upper, "\u2139")

    status_labels = {
        "SUCCESS": "Passed",
        "FAILURE": "Failed",
        "UNSTABLE": "Unstable",
        "ABORTED": "Aborted",
    }
    status_label = status_labels.get(status_upper, status_upper)

    header_lines = {
        "SUCCESS": "green",
        "FAILURE": "red",
        "UNSTABLE": "amber",
        "ABORTED": "gray",
    }
    header_color_name = header_lines.get(status_upper, "indigo")
    shield_color = {"red": "#fca5a5", "green": "#86efac", "amber": "#fcd34d", "gray": "#cbd5e1"}.get(header_color_name, "#a5b4fc")

    report_type_icons = {
        ".html": "\U0001f5ce",
        ".json": "\U0001f4cb",
        ".xml": "\U0001f4c3",
        ".pdf": "\U0001f5cb",
    }
    default_icon = "\U0001f4e6"

    reports_list = "".join(
        f"""
        <tr>
          <td style="padding:12px 14px;border-bottom:1px solid #edf2f7;vertical-align:middle;width:30px;">
            <span style="font-size:1.1rem;">{next((v for k, v in report_type_icons.items() if r.lower().endswith(k)), default_icon)}</span>
          </td>
          <td style="padding:12px 14px;border-bottom:1px solid #edf2f7;vertical-align:middle;">
            <span style="font-weight:500;color:#2d3748;font-size:0.85rem;">{r}</span>
          </td>
        </tr>"""
        for r in report_names
    )

    url_html = ""
    if pipeline_url:
        url_html = f"""
        <table cellpadding="0" cellspacing="0" border="0" style="margin:12px 0 0;">
          <tr>
            <td align="center" style="border-radius:6px;" bgcolor="#4a5568">
              <a href="{pipeline_url}" target="_blank"
                 style="display:inline-block;padding:10px 20px;font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;font-size:0.82rem;font-weight:600;color:#ffffff;text-decoration:none;border-radius:6px;">
                View Pipeline Run &rang;
              </a>
            </td>
          </tr>
        </table>"""

    status_text = {
        "SUCCESS": "All security scans completed successfully with no critical findings.",
        "FAILURE": "One or more security scans failed. Please review the attached reports.",
        "UNSTABLE": "Security scans completed with warnings. Review the attached reports for details.",
        "ABORTED": "The security pipeline was aborted before completion.",
    }
    status_msg = status_text.get(status_upper, "The security pipeline has completed.")

    now = datetime.now()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>[Security] Pipeline {status_upper}</title>
<style>
  body {{ margin:0; padding:0; background-color:#f4f7fa; font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif; }}
  table {{ border-spacing:0; }}
  img {{ border:0; outline:none; }}
</style>
</head>
<body style="margin:0;padding:0;background-color:#f4f7fa;font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;">

<div style="display:none;font-size:1px;color:#f4f7fa;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
  Pipeline {status_label} &mdash; {status_msg[:80]}
</div>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color:#f4f7fa;padding:30px 0;">
<tr>
<td align="center">

<table cellpadding="0" cellspacing="0" border="0" width="600" style="max-width:600px;width:100%;">

<tr>
  <td style="background-color:{color};border-radius:10px 10px 0 0;padding:28px 30px 22px;text-align:center;">
    <table cellpadding="0" cellspacing="0" border="0" align="center" style="margin-bottom:10px;">
      <tr>
        <td align="center" style="background:rgba(255,255,255,0.15);border-radius:50%;width:48px;height:48px;line-height:48px;font-size:22px;">
          &#128737;
        </td>
      </tr>
    </table>
    <h1 style="margin:0 0 2px;font-size:1.25rem;font-weight:700;color:#ffffff;letter-spacing:-0.01em;">
      Security Pipeline Report
    </h1>
    <p style="margin:0 0 12px;font-size:0.82rem;color:rgba(255,255,255,0.85);">
      Build Status: <strong style="color:#ffffff;">{status_label}</strong>
    </p>
    <table cellpadding="0" cellspacing="0" border="0" align="center" style="border-radius:20px;" bgcolor="rgba(255,255,255,0.2)">
      <tr>
        <td align="center" style="padding:4px 16px;border-radius:20px;font-size:0.78rem;font-weight:700;color:#ffffff;letter-spacing:0.02em;text-transform:uppercase;">
          {icon} &nbsp;{status_label}
        </td>
      </tr>
    </table>
  </td>
</tr>

<tr>
  <td style="background:#ffffff;padding:28px 30px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">

    <p style="margin:0 0 18px;font-size:0.88rem;color:#475569;line-height:1.6;">
      {status_msg}
    </p>

    {url_html}

    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:22px 0;">
      <tr>
        <td style="height:1px;background:#e2e8f0;font-size:0;line-height:0;">&nbsp;</td>
      </tr>
    </table>

    <h2 style="margin:0 0 2px;font-size:0.92rem;font-weight:600;color:#1e293b;">
      &#128196; Attached Reports
    </h2>
    <p style="margin:0 0 14px;font-size:0.78rem;color:#718096;">
      The following files are attached to this email.
    </p>

    {f'<table cellpadding="0" cellspacing="0" border="0" width="100%" style="border:1px solid #e2e8f0;border-radius:6px;">{reports_list}</table>' if report_names else '<p style="color:#a0aec0;font-style:italic;margin:12px 0;">No reports attached.</p>'}

    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top:22px;">
      <tr>
        <td align="center" style="font-size:0.74rem;color:#a0aec0;">
          Generated on {now.strftime('%B %d, %Y at %H:%M')}
        </td>
      </tr>
    </table>

  </td>
</tr>

<tr>
  <td style="background:#f8fafc;border-radius:0 0 10px 10px;border:1px solid #e2e8f0;border-top:none;padding:18px 30px;text-align:center;">
    <table cellpadding="0" cellspacing="0" border="0" align="center">
      <tr>
        <td style="font-size:0.74rem;color:#718096;line-height:1.8;">
          <strong style="color:#4a5568;">Security Pipelines Team</strong><br>
          Sagar Malla &bull; sagar.malla@esewa.com.np<br>
          Aditya Tuladhar &bull; aditya.tuladhar@esewa.com.np
        </td>
      </tr>
    </table>
    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top:12px;">
      <tr>
        <td align="center" style="font-size:0.68rem;color:#a0aec0;">
          This is an automated message from the CI/CD security pipeline.
        </td>
      </tr>
    </table>
  </td>
</tr>

</table>
</td>
</tr>
</table>

</body>
</html>"""


def send_email(recipients, subject, html_body, attachments, smtp_cfg):
    msg = MIMEMultipart("alternative")
    msg["From"] = smtp_cfg["from"]
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html"))

    for filepath in attachments:
        if not os.path.isfile(filepath):
            print(f"  ⚠ Attachment not found, skipping: {filepath}", file=sys.stderr)
            continue
        with open(filepath, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            filename = os.path.basename(filepath)
            part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
            msg.attach(part)

    with smtplib.SMTP(smtp_cfg["server"], smtp_cfg["port"]) as server:
        server.ehlo()
        if smtp_cfg.get("tls"):
            server.starttls()
            server.ehlo()
        if smtp_cfg.get("username") and smtp_cfg.get("password"):
            server.login(smtp_cfg["username"], smtp_cfg["password"])
        server.sendmail(smtp_cfg["from"], recipients, msg.as_string())


def main():
    args = parse_args()

    smtp_server = os.environ.get("SMTP_SERVER", "localhost")
    smtp_port = int(os.environ.get("SMTP_PORT", "25"))
    smtp_username = os.environ.get("SMTP_USERNAME") or ""
    smtp_password = os.environ.get("SMTP_PASSWORD") or ""
    email_from = os.environ.get("EMAIL_FROM") or smtp_username or f"noreply@{smtp_server}"

    if smtp_username and smtp_password:
        print(f"SMTP auth: {smtp_username}")
    else:
        print("SMTP: no auth, sending without login")

    recipients = [r.strip() for r in args.recipients.split(",") if r.strip()]
    report_files = [r.strip() for r in args.reports.split(",") if r.strip()]

    if not recipients:
        print("Error: No valid recipients provided.", file=sys.stderr)
        sys.exit(1)

    status = args.status.upper()
    subject = args.subject or f"[Security Pipeline] Report - {status}"

    report_basenames = [os.path.basename(f) for f in report_files]
    html_body = build_html_body(status, args.pipeline_url, report_basenames)

    smtp_cfg = {
        "server": smtp_server,
        "port": smtp_port,
        "username": smtp_username or None,
        "password": smtp_password or None,
        "from": email_from,
        "tls": args.tls,
    }

    print(f"Sending email to: {', '.join(recipients)}")
    print(f"Subject: {subject}")
    print(f"Attachments: {', '.join(report_files)}")
    send_email(recipients, subject, html_body, report_files, smtp_cfg)
    print("Email sent successfully.")


if __name__ == "__main__":
    main()
