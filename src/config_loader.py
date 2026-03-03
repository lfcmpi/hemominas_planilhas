"""Config Loader: sincroniza banco app_config <-> variaveis de modulos em runtime."""

import sys

from src.history_store import obter_app_config, salvar_app_config

# Mapeamento: chave do banco -> (atributo em src.config, tipo)
_CONFIG_KEYS = {
    "google_sheets_id": ("GOOGLE_SHEETS_ID", str),
    "sheet_tab_name": ("SHEET_TAB_NAME", str),
    "sheet_header_row": ("SHEET_HEADER_ROW", int),
    "base_tab_name": ("BASE_TAB_NAME", str),
    "base_gs_rh_range": ("BASE_GS_RH_RANGE", str),
    "base_tipos_range": ("BASE_TIPOS_RANGE", str),
    "base_responsaveis_range": ("BASE_RESPONSAVEIS_RANGE", str),
    "base_destinos_range": ("BASE_DESTINOS_RANGE", str),
    "base_reacao_range": ("BASE_REACAO_RANGE", str),
    "smtp_enabled": ("SMTP_ENABLED", bool),
    "smtp_host": ("SMTP_HOST", str),
    "smtp_port": ("SMTP_PORT", int),
    "smtp_user": ("SMTP_USER", str),
    "smtp_password": ("SMTP_PASSWORD", str),
    "smtp_from": ("SMTP_FROM", str),
    "alert_email_to": ("ALERT_EMAIL_TO", str),
    "scheduler_enabled": ("SCHEDULER_ENABLED", bool),
    "scheduler_alert_hour": ("SCHEDULER_ALERT_HOUR", int),
    "scheduler_alert_minute": ("SCHEDULER_ALERT_MINUTE", int),
    "sync_interval_minutes": ("SYNC_INTERVAL_MINUTES", int),
    "cache_ttl_seconds": ("CACHE_TTL_SECONDS", int),
    "session_lifetime_minutes": ("SESSION_LIFETIME_MINUTES", int),
    "max_batch_files": ("MAX_BATCH_FILES", int),
    "max_upload_size_mb": ("MAX_UPLOAD_SIZE_MB", int),
}

# Modulos que importaram constantes localmente e precisam ser atualizados
_MODULE_ATTRS = {
    "src.sheets_reader": [
        "GOOGLE_CREDENTIALS_PATH", "GOOGLE_SHEETS_ID", "SHEET_TAB_NAME",
        "BASE_TAB_NAME", "BASE_GS_RH_RANGE", "BASE_TIPOS_RANGE",
        "BASE_RESPONSAVEIS_RANGE", "BASE_DESTINOS_RANGE",
        "BASE_REACAO_RANGE", "BASE_CACHE_TTL_MINUTES",
    ],
    "src.sheets_writer": [
        "GOOGLE_CREDENTIALS_PATH", "GOOGLE_SHEETS_ID", "SHEET_TAB_NAME",
    ],
    "src.email_sender": [
        "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM",
    ],
    "src.sync_service": [
        "GOOGLE_SHEETS_ID",
    ],
    "src.dashboard_service": [
        "CACHE_TTL_SECONDS",
    ],
    "src.app": [
        "SQLITE_DB_PATH", "GOOGLE_SHEETS_ID", "MAX_BATCH_FILES",
        "MAX_UPLOAD_SIZE_MB",
    ],
    "src.scheduler": [
        "GOOGLE_SHEETS_ID", "SCHEDULER_ENABLED", "SCHEDULER_ALERT_HOUR",
        "SCHEDULER_ALERT_MINUTE", "SYNC_INTERVAL_MINUTES",
    ],
}


def _converter(valor_str, tipo):
    """Converte string do banco para o tipo Python correto."""
    if tipo == bool:
        return valor_str.lower() in ("true", "1", "yes", "sim")
    if tipo == int:
        try:
            return int(valor_str)
        except (ValueError, TypeError):
            return 0
    return valor_str


def _propagar_para_modulos():
    """Propaga atributos de src.config para modulos que fizeram import local."""
    config_mod = sys.modules.get("src.config")
    if not config_mod:
        return

    for mod_name, attrs in _MODULE_ATTRS.items():
        mod = sys.modules.get(mod_name)
        if not mod:
            continue
        for attr in attrs:
            if hasattr(config_mod, attr):
                setattr(mod, attr, getattr(config_mod, attr))


def carregar_config_do_banco(db_path):
    """Chamada no startup (apos init_db). Le app_config e sobrescreve src.config."""
    import src.config as config_mod

    db_config = obter_app_config(db_path)
    if not db_config:
        return  # Banco vazio, manter defaults do .env

    for db_key, (attr_name, tipo) in _CONFIG_KEYS.items():
        if db_key in db_config and db_config[db_key] != "":
            valor = _converter(db_config[db_key], tipo)
            setattr(config_mod, attr_name, valor)

    _propagar_para_modulos()


def aplicar_config_runtime(db_path, config: dict):
    """Chamada ao salvar via UI. Atualiza banco + propaga para todos os modulos."""
    import src.config as config_mod

    # Salvar no banco
    db_data = {}
    for db_key, (attr_name, tipo) in _CONFIG_KEYS.items():
        if db_key in config:
            valor = config[db_key]
            db_data[db_key] = str(valor) if valor is not None else ""
    salvar_app_config(db_path, db_data)

    # Atualizar src.config
    for db_key, (attr_name, tipo) in _CONFIG_KEYS.items():
        if db_key in config:
            valor_str = str(config[db_key]) if config[db_key] is not None else ""
            if valor_str != "":
                valor = _converter(valor_str, tipo)
                setattr(config_mod, attr_name, valor)

    _propagar_para_modulos()
