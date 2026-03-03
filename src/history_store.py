"""Armazenamento de historico de importacoes e configuracao de alertas (SQLite)."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta


@contextmanager
def get_db(db_path: str):
    """Context manager para conexao SQLite com WAL mode."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str):
    """Cria tabelas se nao existem."""
    with get_db(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS import_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                filename TEXT NOT NULL,
                comprovante_nums TEXT,
                bolsa_count INTEGER NOT NULL,
                status TEXT NOT NULL,
                error_message TEXT
            );

            CREATE TABLE IF NOT EXISTS import_bolsas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_id INTEGER NOT NULL,
                num_bolsa TEXT NOT NULL,
                inst_coleta TEXT DEFAULT '',
                tipo_hemocomponente TEXT NOT NULL,
                gs_rh TEXT NOT NULL,
                volume INTEGER NOT NULL,
                data_validade TEXT NOT NULL,
                FOREIGN KEY (import_id) REFERENCES import_records(id)
            );

            CREATE TABLE IF NOT EXISTS alert_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                threshold_urgente INTEGER NOT NULL DEFAULT 7,
                threshold_atencao INTEGER NOT NULL DEFAULT 14,
                email_enabled INTEGER NOT NULL DEFAULT 0,
                email_to TEXT,
                inapp_enabled INTEGER NOT NULL DEFAULT 1
            );

            CREATE INDEX IF NOT EXISTS idx_import_records_timestamp
                ON import_records(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_import_bolsas_import_id
                ON import_bolsas(import_id);

            CREATE TABLE IF NOT EXISTS planilha_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                num_bolsa TEXT UNIQUE NOT NULL,
                inst_coleta TEXT DEFAULT '',
                dias_antes_vencimento TEXT,
                status_vencimento TEXT,
                data_entrada TEXT,
                data_validade TEXT,
                data_transfusao TEXT,
                destino TEXT,
                nome_paciente TEXT DEFAULT '',
                tipo_hemocomponente TEXT,
                gs_rh TEXT,
                volume INTEGER,
                responsavel_recepcao TEXT,
                setor_transfusao TEXT DEFAULT '',
                prontuario_salus TEXT DEFAULT '',
                prontuario_mv TEXT DEFAULT '',
                sus_laudo TEXT DEFAULT '',
                reacao_transfusional TEXT DEFAULT '',
                bolsa_sbs TEXT DEFAULT '',
                sheet_row INTEGER,
                pending_sync INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_planilha_num_bolsa
                ON planilha_data(num_bolsa);
            CREATE INDEX IF NOT EXISTS idx_planilha_gs_rh
                ON planilha_data(gs_rh);
            CREATE INDEX IF NOT EXISTS idx_planilha_tipo
                ON planilha_data(tipo_hemocomponente);

            CREATE TABLE IF NOT EXISTS sync_metadata (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_sync_at TEXT,
                last_sync_status TEXT,
                last_sync_rows INTEGER DEFAULT 0,
                last_sync_error TEXT
            );

            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)

        # Migration: add pending_sync column if missing (existing databases)
        cols = [row[1] for row in conn.execute("PRAGMA table_info(planilha_data)").fetchall()]
        if "pending_sync" not in cols:
            conn.execute("ALTER TABLE planilha_data ADD COLUMN pending_sync INTEGER DEFAULT 0")

        # Migration: add inst_coleta column if missing (existing databases)
        if "inst_coleta" not in cols:
            conn.execute("ALTER TABLE planilha_data ADD COLUMN inst_coleta TEXT DEFAULT ''")

        # Migration: rename campo_g -> nome_paciente, campo_l -> setor_transfusao
        if "campo_g" in cols and "nome_paciente" not in cols:
            conn.execute("ALTER TABLE planilha_data RENAME COLUMN campo_g TO nome_paciente")
        if "campo_l" in cols and "setor_transfusao" not in cols:
            conn.execute("ALTER TABLE planilha_data RENAME COLUMN campo_l TO setor_transfusao")

        # Migration: add columns N-S (spreadsheet columns beyond M)
        # Re-read cols after possible renames
        cols = [row[1] for row in conn.execute("PRAGMA table_info(planilha_data)").fetchall()]
        for col_name in ["nome_paciente", "setor_transfusao", "prontuario_salus",
                         "prontuario_mv", "sus_laudo", "reacao_transfusional", "bolsa_sbs"]:
            if col_name not in cols:
                conn.execute(f"ALTER TABLE planilha_data ADD COLUMN {col_name} TEXT DEFAULT ''")

        bolsa_cols = [row[1] for row in conn.execute("PRAGMA table_info(import_bolsas)").fetchall()]
        if "inst_coleta" not in bolsa_cols:
            conn.execute("ALTER TABLE import_bolsas ADD COLUMN inst_coleta TEXT DEFAULT ''")

        # Migration: add edited_by and edited_at columns (RBAC inline editing audit)
        cols = [row[1] for row in conn.execute("PRAGMA table_info(planilha_data)").fetchall()]
        if "edited_by" not in cols:
            conn.execute("ALTER TABLE planilha_data ADD COLUMN edited_by TEXT DEFAULT ''")
        if "edited_at" not in cols:
            conn.execute("ALTER TABLE planilha_data ADD COLUMN edited_at TEXT DEFAULT ''")

        # Create index after ensuring column exists
        conn.execute("CREATE INDEX IF NOT EXISTS idx_planilha_pending_sync ON planilha_data(pending_sync)")


def registrar_importacao(db_path, filename, comprovante_nums, bolsa_count,
                         status, error_message, bolsas_detail) -> int:
    """Insere registro de importacao + detalhes de bolsas. Retorna import_id."""
    with get_db(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO import_records (timestamp, filename, comprovante_nums, "
            "bolsa_count, status, error_message) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), filename, comprovante_nums,
             bolsa_count, status, error_message)
        )
        import_id = cursor.lastrowid
        for bolsa in bolsas_detail:
            validade = bolsa.data_validade
            if hasattr(validade, 'isoformat'):
                validade = validade.isoformat()
            inst_coleta = getattr(bolsa, 'inst_coleta', '')
            conn.execute(
                "INSERT INTO import_bolsas (import_id, num_bolsa, inst_coleta, "
                "tipo_hemocomponente, gs_rh, volume, data_validade) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (import_id, bolsa.num_bolsa, inst_coleta,
                 bolsa.tipo_hemocomponente, bolsa.gs_rh, bolsa.volume, validade)
            )
        return import_id


def listar_importacoes(db_path, data_inicio=None, data_fim=None,
                       page=1, per_page=20):
    """Retorna (lista_importacoes, total). Filtro por periodo opcional."""
    with get_db(db_path) as conn:
        where_clauses = []
        params = []

        if data_inicio:
            where_clauses.append("timestamp >= ?")
            params.append(data_inicio + "T00:00:00")
        if data_fim:
            where_clauses.append("timestamp <= ?")
            params.append(data_fim + "T23:59:59")

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        count_row = conn.execute(
            f"SELECT COUNT(*) as total FROM import_records {where_sql}",
            params
        ).fetchone()
        total = count_row["total"]

        offset = (page - 1) * per_page
        rows = conn.execute(
            f"SELECT id, timestamp, filename, comprovante_nums, bolsa_count, status "
            f"FROM import_records {where_sql} "
            f"ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()

        importacoes = [dict(row) for row in rows]
        return importacoes, total


def obter_importacao(db_path, import_id):
    """Retorna registro + bolsas detalhadas, ou None se nao existe."""
    with get_db(db_path) as conn:
        record = conn.execute(
            "SELECT * FROM import_records WHERE id = ?", (import_id,)
        ).fetchone()

        if not record:
            return None

        bolsas = conn.execute(
            "SELECT num_bolsa, tipo_hemocomponente, gs_rh, volume, data_validade "
            "FROM import_bolsas WHERE import_id = ? ORDER BY id",
            (import_id,)
        ).fetchall()

        return {
            "importacao": dict(record),
            "bolsas": [dict(b) for b in bolsas],
        }


def obter_alert_config(db_path):
    """Retorna config de alertas. Cria padrao se nao existe."""
    with get_db(db_path) as conn:
        row = conn.execute("SELECT * FROM alert_config WHERE id = 1").fetchone()
        if not row:
            conn.execute(
                "INSERT INTO alert_config (id, threshold_urgente, threshold_atencao, "
                "email_enabled, email_to, inapp_enabled) VALUES (1, 7, 14, 0, NULL, 1)"
            )
            row = conn.execute("SELECT * FROM alert_config WHERE id = 1").fetchone()
        return {
            "threshold_urgente": row["threshold_urgente"],
            "threshold_atencao": row["threshold_atencao"],
            "email_enabled": bool(row["email_enabled"]),
            "email_to": row["email_to"],
            "inapp_enabled": bool(row["inapp_enabled"]),
        }


def salvar_alert_config(db_path, config):
    """Upsert da config de alertas."""
    with get_db(db_path) as conn:
        conn.execute(
            "INSERT INTO alert_config (id, threshold_urgente, threshold_atencao, "
            "email_enabled, email_to, inapp_enabled) VALUES (1, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "threshold_urgente=excluded.threshold_urgente, "
            "threshold_atencao=excluded.threshold_atencao, "
            "email_enabled=excluded.email_enabled, "
            "email_to=excluded.email_to, "
            "inapp_enabled=excluded.inapp_enabled",
            (config["threshold_urgente"], config["threshold_atencao"],
             int(config["email_enabled"]), config.get("email_to"),
             int(config["inapp_enabled"]))
        )


# ==========================================
# Phase 4: Dashboard Analytics
# ==========================================


def obter_estatisticas_importacoes(db_path):
    """Estatisticas gerais de importacoes historicas."""
    with get_db(db_path) as conn:
        # Total imports
        total = conn.execute(
            "SELECT COUNT(*) as c FROM import_records WHERE status = 'sucesso'"
        ).fetchone()["c"]

        # Total bolsas imported
        total_bolsas = conn.execute(
            "SELECT COALESCE(SUM(bolsa_count), 0) as c FROM import_records WHERE status = 'sucesso'"
        ).fetchone()["c"]

        # Imports last 7 days
        d7 = (datetime.now() - timedelta(days=7)).isoformat()
        imports_7d = conn.execute(
            "SELECT COUNT(*) as c FROM import_records WHERE status = 'sucesso' AND timestamp >= ?",
            (d7,)
        ).fetchone()["c"]
        bolsas_7d = conn.execute(
            "SELECT COALESCE(SUM(bolsa_count), 0) as c FROM import_records WHERE status = 'sucesso' AND timestamp >= ?",
            (d7,)
        ).fetchone()["c"]

        # Imports last 30 days
        d30 = (datetime.now() - timedelta(days=30)).isoformat()
        imports_30d = conn.execute(
            "SELECT COUNT(*) as c FROM import_records WHERE status = 'sucesso' AND timestamp >= ?",
            (d30,)
        ).fetchone()["c"]
        bolsas_30d = conn.execute(
            "SELECT COALESCE(SUM(bolsa_count), 0) as c FROM import_records WHERE status = 'sucesso' AND timestamp >= ?",
            (d30,)
        ).fetchone()["c"]

        # Average bolsas per import
        media_bolsas = round(total_bolsas / total, 1) if total > 0 else 0

        # Average volume
        vol = conn.execute(
            "SELECT COALESCE(AVG(volume), 0) as m FROM import_bolsas"
        ).fetchone()["m"]
        media_volume = round(vol, 1)

        # Last import timestamp
        last = conn.execute(
            "SELECT timestamp FROM import_records WHERE status = 'sucesso' ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        ultima_importacao = last["timestamp"] if last else None

        return {
            "total_importacoes": total,
            "total_bolsas": total_bolsas,
            "importacoes_7d": imports_7d,
            "bolsas_7d": bolsas_7d,
            "importacoes_30d": imports_30d,
            "bolsas_30d": bolsas_30d,
            "media_bolsas_por_importacao": media_bolsas,
            "media_volume_ml": media_volume,
            "ultima_importacao": ultima_importacao,
        }


def obter_evolucao_diaria(db_path, dias=30):
    """Bolsas importadas por dia nos ultimos N dias."""
    inicio = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT DATE(timestamp) as dia, SUM(bolsa_count) as total "
            "FROM import_records WHERE status = 'sucesso' AND DATE(timestamp) >= ? "
            "GROUP BY DATE(timestamp) ORDER BY dia",
            (inicio,)
        ).fetchall()
        return [{"dia": r["dia"], "total": r["total"]} for r in rows]


def obter_distribuicao_bolsas(db_path):
    """Distribuicao de bolsas importadas por tipo sanguineo e hemocomponente."""
    with get_db(db_path) as conn:
        # Por GS/RH
        gs_rows = conn.execute(
            "SELECT gs_rh, COUNT(*) as count FROM import_bolsas "
            "WHERE gs_rh != '' GROUP BY gs_rh ORDER BY count DESC"
        ).fetchall()

        # Por hemocomponente
        hemo_rows = conn.execute(
            "SELECT tipo_hemocomponente, COUNT(*) as count FROM import_bolsas "
            "WHERE tipo_hemocomponente != '' GROUP BY tipo_hemocomponente ORDER BY count DESC"
        ).fetchall()

        # Por volume faixas
        vol_rows = conn.execute(
            "SELECT "
            "  CASE "
            "    WHEN volume < 200 THEN '<200mL' "
            "    WHEN volume < 300 THEN '200-299mL' "
            "    WHEN volume < 400 THEN '300-399mL' "
            "    ELSE '400mL+' "
            "  END as faixa, "
            "  COUNT(*) as count "
            "FROM import_bolsas GROUP BY faixa ORDER BY MIN(volume)"
        ).fetchall()

        return {
            "por_gs_rh": [{"tipo": r["gs_rh"], "count": r["count"]} for r in gs_rows],
            "por_hemocomponente": [{"tipo": r["tipo_hemocomponente"], "count": r["count"]} for r in hemo_rows],
            "por_volume": [{"faixa": r["faixa"], "count": r["count"]} for r in vol_rows],
        }


def obter_evolucao_por_tipo(db_path, dias=30):
    """Evolucao de bolsas importadas por tipo sanguineo (agrupado por semana)."""
    inicio = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT b.gs_rh, "
            "  CASE WHEN CAST(strftime('%W', r.timestamp) AS INTEGER) = CAST(strftime('%W', 'now') AS INTEGER) "
            "    THEN 'esta_semana' "
            "    ELSE 'semanas_anteriores' END as periodo, "
            "  COUNT(*) as count "
            "FROM import_bolsas b "
            "JOIN import_records r ON b.import_id = r.id "
            "WHERE r.status = 'sucesso' AND DATE(r.timestamp) >= ? AND b.gs_rh != '' "
            "GROUP BY b.gs_rh, periodo "
            "ORDER BY count DESC",
            (inicio,)
        ).fetchall()
        return [{"gs_rh": r["gs_rh"], "periodo": r["periodo"], "count": r["count"]} for r in rows]


def obter_top_bolsas_recentes(db_path, limit=10):
    """Ultimas bolsas importadas com detalhes."""
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT b.num_bolsa, b.tipo_hemocomponente, b.gs_rh, b.volume, "
            "  b.data_validade, r.timestamp, r.filename "
            "FROM import_bolsas b "
            "JOIN import_records r ON b.import_id = r.id "
            "WHERE r.status = 'sucesso' "
            "ORDER BY r.timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ==========================================
# Phase 6: App Config (UI-managed settings)
# ==========================================


def obter_app_config(db_path):
    """Le todas as chaves da tabela app_config. Retorna dict."""
    with get_db(db_path) as conn:
        rows = conn.execute("SELECT key, value FROM app_config").fetchall()
        return {row["key"]: row["value"] for row in rows}


def salvar_app_config(db_path, config: dict):
    """Upsert cada chave/valor na tabela app_config."""
    with get_db(db_path) as conn:
        for key, value in config.items():
            conn.execute(
                "INSERT INTO app_config (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value) if value is not None else ""),
            )
