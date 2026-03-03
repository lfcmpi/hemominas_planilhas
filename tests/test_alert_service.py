"""Tests para alert_service.py — verificacao de vencimento."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.alert_service import executar_alerta, verificar_vencimentos
from src.dashboard_service import DashboardService, EstoqueResumo


HEADER = [
    "DIAS ANTES VENCIMENTO", "STATUS", "DATA ENTRADA", "DATA VALIDADE",
    "DATA TRANSFUSAO/DESTINO", "DESTINO", "NOME COMPLETO PACIENTE",
    "TIPO HEMOCOMPONENTE", "GS/RH", "VOLUME", "RESPONSAVEL RECEPCAO",
    "SETOR TRANSFUSAO", "Num DA BOLSA",
]


def _make_row(dias_ate_vencer, num="25051087"):
    hoje = date.today()
    validade = (hoje + timedelta(days=dias_ate_vencer)).strftime("%d/%m/%Y")
    return [
        str(dias_ate_vencer), f"VENCE EM {dias_ate_vencer} DIAS",
        "14/12/2025", validade, "", "", "",
        "CHD - Concentrado de Hemacias", "O/POS", "292", "NILMARA", "", num,
    ]


class TestVerificarVencimentos:
    def test_detecta_urgente(self):
        service = DashboardService()
        rows = [_make_row(3, "1"), _make_row(5, "2")]
        result = verificar_vencimentos(service, HEADER, rows)
        assert len(result["urgente"]) == 2

    def test_detecta_atencao(self):
        service = DashboardService()
        rows = [_make_row(10, "1")]
        result = verificar_vencimentos(service, HEADER, rows)
        assert len(result["atencao"]) == 1

    def test_nenhum_alerta(self):
        service = DashboardService()
        rows = [_make_row(60, "1")]
        result = verificar_vencimentos(service, HEADER, rows)
        assert len(result["urgente"]) == 0
        assert len(result["atencao"]) == 0


class TestExecutarAlerta:
    @patch("src.alert_service.obter_alert_config")
    def test_sem_email(self, mock_config):
        mock_config.return_value = {
            "threshold_urgente": 7,
            "threshold_atencao": 14,
            "email_enabled": False,
            "email_to": None,
            "inapp_enabled": True,
        }
        service = DashboardService()
        rows = [_make_row(3)]
        result = executar_alerta(service, HEADER, rows)
        assert result["email_enviado"] is False
        assert len(result["urgente"]) > 0

    @patch("src.alert_service.obter_alert_config")
    def test_com_email_sucesso(self, mock_config):
        mock_config.return_value = {
            "threshold_urgente": 7,
            "threshold_atencao": 14,
            "email_enabled": True,
            "email_to": "test@example.com",
            "inapp_enabled": True,
        }
        mock_sender = MagicMock()
        service = DashboardService()
        rows = [_make_row(3)]
        result = executar_alerta(service, HEADER, rows, email_sender=mock_sender)
        assert result["email_enviado"] is True
        mock_sender.enviar_alerta_email.assert_called_once()

    @patch("src.alert_service.obter_alert_config")
    def test_email_falha_nao_interrompe(self, mock_config):
        mock_config.return_value = {
            "threshold_urgente": 7,
            "threshold_atencao": 14,
            "email_enabled": True,
            "email_to": "test@example.com",
            "inapp_enabled": True,
        }
        mock_sender = MagicMock()
        mock_sender.enviar_alerta_email.side_effect = Exception("SMTP error")
        service = DashboardService()
        rows = [_make_row(3)]
        result = executar_alerta(service, HEADER, rows, email_sender=mock_sender)
        assert result["email_enviado"] is False
        assert len(result["urgente"]) > 0

    @patch("src.alert_service.obter_alert_config")
    def test_sem_bolsas_nao_envia_email(self, mock_config):
        mock_config.return_value = {
            "threshold_urgente": 7,
            "threshold_atencao": 14,
            "email_enabled": True,
            "email_to": "test@example.com",
            "inapp_enabled": True,
        }
        mock_sender = MagicMock()
        service = DashboardService()
        rows = [_make_row(60)]  # Longe do vencimento
        result = executar_alerta(service, HEADER, rows, email_sender=mock_sender)
        assert result["email_enviado"] is False
        mock_sender.enviar_alerta_email.assert_not_called()
