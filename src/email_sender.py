"""Envio de emails de alerta via SMTP."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER


def enviar_alerta_email(config, bolsas_urgente, bolsas_atencao, vencidas=None):
    """Compoe e envia email HTML com alertas de vencimento."""
    email_to = config.get("email_to", "")
    if not email_to:
        return

    html = _compor_email_html(bolsas_urgente, bolsas_atencao, vencidas=vencidas)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Alerta de Vencimento - Banco de Sangue HMOB"
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["To"] = email_to
    msg.attach(MIMEText(html, "html"))

    _enviar_smtp(msg, email_to)


def testar_smtp():
    """Envia email de teste. Retorna True se sucesso."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Teste - Alerta Banco de Sangue HMOB"
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["To"] = SMTP_USER
    msg.attach(MIMEText("<p>Email de teste do sistema de alertas.</p>", "html"))

    _enviar_smtp(msg, SMTP_USER)
    return True


def _enviar_smtp(msg, to):
    """Envia mensagem via SMTP."""
    if SMTP_PORT == 465:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
    else:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()

    try:
        if SMTP_USER and SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(msg["From"], [to], msg.as_string())
    finally:
        server.quit()


def _compor_email_html(bolsas_urgente, bolsas_atencao, vencidas=None):
    """Compoe HTML do email de alerta."""
    html = """
    <html>
    <body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
    <h2 style="color:#333">Alerta de Vencimento - Banco de Sangue HMOB</h2>
    """

    if vencidas:
        html += """
        <div style="background:#fecaca;border:1px solid #f87171;border-radius:8px;padding:12px;margin-bottom:16px">
        <h3 style="color:#7f1d1d;margin:0 0 8px">VENCIDAS ({count} bolsas)</h3>
        <table style="width:100%;border-collapse:collapse;font-size:13px">
        <tr style="background:#fca5a5">
            <th style="padding:4px 8px;text-align:left">Bolsa</th>
            <th style="padding:4px 8px;text-align:left">Tipo</th>
            <th style="padding:4px 8px;text-align:left">GS/RH</th>
            <th style="padding:4px 8px;text-align:left">Vencida ha</th>
        </tr>
        """.format(count=len(vencidas))

        for b in vencidas:
            dias_abs = abs(b.get("dias_restantes", 0))
            html += """
            <tr>
                <td style="padding:4px 8px">{num}</td>
                <td style="padding:4px 8px">{tipo}</td>
                <td style="padding:4px 8px">{gs}</td>
                <td style="padding:4px 8px;color:#b91c1c;font-weight:bold">{dias}d</td>
            </tr>
            """.format(
                num=b.get("num_bolsa", ""),
                tipo=b.get("tipo", ""),
                gs=b.get("gs_rh", ""),
                dias=dias_abs,
            )

        html += "</table></div>"

    if bolsas_urgente:
        html += """
        <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px;margin-bottom:16px">
        <h3 style="color:#991b1b;margin:0 0 8px">URGENTE ({count} bolsas)</h3>
        <table style="width:100%;border-collapse:collapse;font-size:13px">
        <tr style="background:#fee2e2">
            <th style="padding:4px 8px;text-align:left">Bolsa</th>
            <th style="padding:4px 8px;text-align:left">Tipo</th>
            <th style="padding:4px 8px;text-align:left">GS/RH</th>
            <th style="padding:4px 8px;text-align:left">Dias</th>
        </tr>
        """.format(count=len(bolsas_urgente))

        for b in bolsas_urgente:
            html += """
            <tr>
                <td style="padding:4px 8px">{num}</td>
                <td style="padding:4px 8px">{tipo}</td>
                <td style="padding:4px 8px">{gs}</td>
                <td style="padding:4px 8px;color:#dc2626;font-weight:bold">{dias}d</td>
            </tr>
            """.format(
                num=b.get("num_bolsa", ""),
                tipo=b.get("tipo", ""),
                gs=b.get("gs_rh", ""),
                dias=b.get("dias_restantes", ""),
            )

        html += "</table></div>"

    if bolsas_atencao:
        html += """
        <div style="background:#fffbeb;border:1px solid #fef3c7;border-radius:8px;padding:12px;margin-bottom:16px">
        <h3 style="color:#92400e;margin:0 0 8px">ATENCAO ({count} bolsas)</h3>
        <table style="width:100%;border-collapse:collapse;font-size:13px">
        <tr style="background:#fef3c7">
            <th style="padding:4px 8px;text-align:left">Bolsa</th>
            <th style="padding:4px 8px;text-align:left">Tipo</th>
            <th style="padding:4px 8px;text-align:left">GS/RH</th>
            <th style="padding:4px 8px;text-align:left">Dias</th>
        </tr>
        """.format(count=len(bolsas_atencao))

        for b in bolsas_atencao:
            html += """
            <tr>
                <td style="padding:4px 8px">{num}</td>
                <td style="padding:4px 8px">{tipo}</td>
                <td style="padding:4px 8px">{gs}</td>
                <td style="padding:4px 8px;color:#d97706;font-weight:bold">{dias}d</td>
            </tr>
            """.format(
                num=b.get("num_bolsa", ""),
                tipo=b.get("tipo", ""),
                gs=b.get("gs_rh", ""),
                dias=b.get("dias_restantes", ""),
            )

        html += "</table></div>"

    if not vencidas and not bolsas_urgente and not bolsas_atencao:
        html += '<p style="color:#166534">Nenhuma bolsa proxima do vencimento.</p>'

    html += """
    <p style="color:#999;font-size:12px;margin-top:16px">
    Gerado automaticamente pelo sistema de Banco de Sangue HMOB.
    </p>
    </body></html>
    """

    return html
