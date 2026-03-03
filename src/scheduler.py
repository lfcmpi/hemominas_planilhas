"""Agendamento de tarefas (alertas diarios)."""

from src.config import (
    GOOGLE_SHEETS_ID,
    SCHEDULER_ALERT_HOUR,
    SCHEDULER_ALERT_MINUTE,
    SCHEDULER_ENABLED,
    SQLITE_DB_PATH,
    SYNC_INTERVAL_MINUTES,
)

_scheduler_started = False


def iniciar_scheduler(app, dashboard_service):
    """Inicia scheduler de alertas diarios se SCHEDULER_ENABLED=true."""
    global _scheduler_started

    if not SCHEDULER_ENABLED:
        return

    if _scheduler_started:
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")

        def job_alerta():
            with app.app_context():
                try:
                    from src.alert_service import executar_alerta
                    from src.email_sender import enviar_alerta_email
                    from src.sheets_reader import ler_planilha_completa

                    header, data_rows = ler_planilha_completa(GOOGLE_SHEETS_ID)
                    if header:
                        import src.email_sender as email_mod
                        executar_alerta(dashboard_service, header, data_rows, email_mod)
                except Exception as e:
                    app.logger.error(f"Erro no alerta agendado: {e}")

        scheduler.add_job(
            job_alerta,
            "cron",
            hour=SCHEDULER_ALERT_HOUR,
            minute=SCHEDULER_ALERT_MINUTE,
            id="alerta_vencimento",
        )

        def job_sync():
            with app.app_context():
                try:
                    from src.sync_service import executar_sync, sincronizar_pendentes
                    executar_sync(SQLITE_DB_PATH)
                    # Also try to push any locally-saved data to Sheets
                    sincronizar_pendentes(SQLITE_DB_PATH)
                except Exception as e:
                    app.logger.error(f"Erro no sync agendado: {e}")

        from datetime import datetime
        scheduler.add_job(
            job_sync,
            "interval",
            minutes=SYNC_INTERVAL_MINUTES,
            id="sync_planilha",
            next_run_time=datetime.now(),
        )

        scheduler.start()
        _scheduler_started = True
        app.logger.info(
            f"Scheduler iniciado: alertas diarios as {SCHEDULER_ALERT_HOUR}:{SCHEDULER_ALERT_MINUTE:02d}, "
            f"sync a cada {SYNC_INTERVAL_MINUTES}min"
        )

    except Exception as e:
        app.logger.error(f"Erro ao iniciar scheduler: {e}")
