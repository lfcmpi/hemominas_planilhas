"""Servico de dashboard: agregacao de estoque e vencimentos."""

from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.config import CACHE_TTL_SECONDS, SQLITE_DB_PATH
from src.history_store import obter_alert_config


@dataclass
class EstoqueResumo:
    por_gs_rh: dict = field(default_factory=dict)
    por_hemocomponente: dict = field(default_factory=dict)
    total_em_estoque: int = 0
    vencendo_7d: list = field(default_factory=list)
    vencendo_14d: list = field(default_factory=list)
    vencendo_30d: list = field(default_factory=list)
    ultima_atualizacao: datetime = None


class DashboardService:
    def __init__(self):
        self._cache: EstoqueResumo | None = None
        self._cache_time: datetime | None = None

    def invalidar_cache(self):
        """Invalida cache — chamado apos importacao."""
        self._cache = None
        self._cache_time = None

    def obter_estoque(self, header, data_rows, force_refresh=False) -> EstoqueResumo:
        """Retorna dados agregados de estoque. Usa cache se disponivel."""
        now = datetime.now()

        if (
            not force_refresh
            and self._cache is not None
            and self._cache_time is not None
            and (now - self._cache_time).total_seconds() < CACHE_TTL_SECONDS
        ):
            return self._cache

        resumo = self._agregar_dados(data_rows, header)
        self._cache = resumo
        self._cache_time = now
        return resumo

    def _agregar_dados(self, data_rows, header) -> EstoqueResumo:
        """Agrega dados das rows da planilha."""
        # Map column indices by header
        col_idx = {}
        for i, h in enumerate(header):
            h_upper = h.strip().upper()
            if "DATA" in h_upper and "TRANSFUS" in h_upper:
                col_idx["data_transfusao"] = i  # E
            elif "DESTINO" in h_upper:
                col_idx["destino"] = i  # F
            elif "DATA" in h_upper and "VALIDADE" in h_upper:
                col_idx["data_validade"] = i  # D
            elif "DATA" in h_upper and "ENTRADA" in h_upper:
                col_idx["data_entrada"] = i  # C
            elif "TIPO" in h_upper and "HEMO" in h_upper:
                col_idx["tipo_hemo"] = i  # H
            elif "GS" in h_upper or "RH" in h_upper:
                col_idx["gs_rh"] = i  # I
            elif "VOLUME" in h_upper:
                col_idx["volume"] = i  # J
            elif "BOLSA" in h_upper or (h_upper.startswith("N") and "BOLSA" in h_upper):
                col_idx["num_bolsa"] = i  # M

        # Fallback to known positions if header mapping fails
        col_idx.setdefault("data_entrada", 2)      # C
        col_idx.setdefault("data_validade", 3)      # D
        col_idx.setdefault("data_transfusao", 4)    # E
        col_idx.setdefault("destino", 5)            # F
        col_idx.setdefault("tipo_hemo", 7)          # H
        col_idx.setdefault("gs_rh", 8)              # I
        col_idx.setdefault("volume", 9)             # J
        col_idx.setdefault("num_bolsa", 12)         # M

        hoje = _hoje()

        por_gs_rh = {}
        por_hemocomponente = {}
        total_em_estoque = 0
        vencendo = {7: [], 14: [], 30: []}

        # Get alert thresholds
        try:
            alert_config = obter_alert_config(SQLITE_DB_PATH)
            thresh_urgente = alert_config["threshold_urgente"]
            thresh_atencao = alert_config["threshold_atencao"]
        except Exception:
            thresh_urgente = 7
            thresh_atencao = 14

        for row in data_rows:
            if not row or len(row) <= col_idx["destino"]:
                continue

            # Em estoque = coluna E (data_transfusao) vazia AND coluna F (destino) vazia
            col_e = _safe_get(row, col_idx["data_transfusao"]).strip()
            col_f = _safe_get(row, col_idx["destino"]).strip()

            if col_e or col_f:
                continue  # Bolsa ja transfundida/com destino

            # Parse data validade
            data_val_str = _safe_get(row, col_idx["data_validade"]).strip()
            data_val = _parse_date_br(data_val_str)

            tipo = _safe_get(row, col_idx["tipo_hemo"]).strip()
            gs_rh = _safe_get(row, col_idx["gs_rh"]).strip()
            num_bolsa = _safe_get(row, col_idx["num_bolsa"]).strip()
            volume_str = _safe_get(row, col_idx["volume"]).strip()

            if not num_bolsa and not tipo:
                continue  # Row vazia

            total_em_estoque += 1

            # Contagem por GS/RH
            if gs_rh:
                por_gs_rh[gs_rh] = por_gs_rh.get(gs_rh, 0) + 1

            # Contagem por hemocomponente (usar sigla antes do " - ")
            if tipo:
                sigla = tipo.split(" - ")[0].split(" – ")[0].strip() if (" - " in tipo or " – " in tipo) else tipo
                por_hemocomponente[sigla] = por_hemocomponente.get(sigla, 0) + 1

            # Verificar vencimento
            if data_val:
                dias = (data_val - hoje).days
                volume = 0
                try:
                    volume = int(volume_str) if volume_str else 0
                except ValueError:
                    pass

                bolsa_info = {
                    "num_bolsa": num_bolsa,
                    "tipo": tipo,
                    "gs_rh": gs_rh,
                    "volume": volume,
                    "data_validade": data_val_str,
                    "dias_restantes": dias,
                }

                if dias <= thresh_urgente:
                    vencendo[7].append(bolsa_info)
                elif dias <= thresh_atencao:
                    vencendo[14].append(bolsa_info)
                elif dias <= 30:
                    vencendo[30].append(bolsa_info)

        # Sort vencendo by dias_restantes
        for key in vencendo:
            vencendo[key].sort(key=lambda b: b["dias_restantes"])

        return EstoqueResumo(
            por_gs_rh=dict(sorted(por_gs_rh.items(), key=lambda x: x[1], reverse=True)),
            por_hemocomponente=dict(sorted(por_hemocomponente.items(), key=lambda x: x[1], reverse=True)),
            total_em_estoque=total_em_estoque,
            vencendo_7d=vencendo[7],
            vencendo_14d=vencendo[14],
            vencendo_30d=vencendo[30],
            ultima_atualizacao=datetime.now(),
        )


def _hoje() -> date:
    """Data de hoje em fuso de Brasilia."""
    try:
        return datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    except Exception:
        return date.today()


def _safe_get(row, idx) -> str:
    """Acessa indice da lista sem IndexError."""
    if idx < len(row):
        return str(row[idx])
    return ""


def _parse_date_br(text: str) -> date | None:
    """Parse DD/MM/YYYY para date."""
    if not text:
        return None
    try:
        parts = text.split("/")
        if len(parts) == 3:
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
    except (ValueError, IndexError):
        pass
    return None
