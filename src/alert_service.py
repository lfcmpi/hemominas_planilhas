"""Servico de alertas de vencimento de bolsas."""

from src.config import SQLITE_DB_PATH
from src.history_store import obter_alert_config


def verificar_vencimentos(dashboard_service, header, data_rows):
    """Verifica bolsas proximas do vencimento usando dados do dashboard.

    Retorna dict com listas 'urgente' e 'atencao'.
    """
    resumo = dashboard_service.obter_estoque(header, data_rows)

    return {
        "vencidas": resumo.vencidas,
        "urgente": resumo.vencendo_7d,
        "atencao": resumo.vencendo_14d,
    }


def executar_alerta(dashboard_service, header, data_rows, email_sender=None):
    """Executa verificacao completa + envia notificacoes se configurado.

    Returns dict com resumo do alerta.
    """
    config = obter_alert_config(SQLITE_DB_PATH)
    vencimentos = verificar_vencimentos(dashboard_service, header, data_rows)

    email_enviado = False

    if (
        config["email_enabled"]
        and config.get("email_to")
        and email_sender is not None
        and (vencimentos["vencidas"] or vencimentos["urgente"] or vencimentos["atencao"])
    ):
        try:
            email_sender.enviar_alerta_email(
                config, vencimentos["urgente"], vencimentos["atencao"],
                vencidas=vencimentos["vencidas"],
            )
            email_enviado = True
        except Exception:
            email_enviado = False

    return {
        "vencidas": vencimentos["vencidas"],
        "urgente": vencimentos["urgente"],
        "atencao": vencimentos["atencao"],
        "email_enviado": email_enviado,
    }
