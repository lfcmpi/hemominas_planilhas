"""Tests para batch_processor.py — processamento em lote."""

import io
from dataclasses import dataclass, field
from datetime import date, datetime
from unittest.mock import patch

import pytest

from src.batch_processor import BatchFileStatus, processar_lote
from src.pdf_extractor import BolsaExtraida, Comprovante


class FakeFileStorage:
    """Mock de werkzeug FileStorage."""
    def __init__(self, filename, data=b"fake pdf"):
        self.filename = filename
        self._data = data

    def save(self, path):
        with open(path, "wb") as f:
            f.write(self._data)


def _make_comprovante(numero="1292305", n_bolsas=3):
    bolsas = [
        BolsaExtraida(
            inst_coleta="B0001", num_doacao=f"2505{i:04d}",
            componente_pdf="Concentrado Hemacias Desleucocitado",
            cod_isbt="E0001V01", seq=i, volume=292,
            abo="O", rh="P", validade=date(2026, 3, 8),
        )
        for i in range(n_bolsas)
    ]
    return Comprovante(
        numero=numero, data_emissao=datetime(2025, 12, 15, 10, 0),
        instituicao="HMOB", expedido_por="Nilmara",
        data_expedicao=date(2025, 12, 15), bolsas=bolsas,
        total_bolsas_declarado=n_bolsas,
    )


class TestProcessarLote:
    @patch("src.batch_processor.extrair_pdf")
    def test_processa_multiplos_sucesso(self, mock_extrair):
        mock_extrair.return_value = [_make_comprovante()]
        files = [FakeFileStorage("a.pdf"), FakeFileStorage("b.pdf")]
        result = processar_lote(files)

        assert result["summary"]["total_files"] == 2
        assert result["summary"]["success_files"] == 2
        assert result["summary"]["error_files"] == 0
        assert result["summary"]["total_bolsas"] == 6  # 3 per file
        assert len(result["files"]) == 2
        assert all(f.status == "done" for f in result["files"])

    @patch("src.batch_processor.extrair_pdf")
    def test_erro_em_um_nao_bloqueia_outros(self, mock_extrair):
        mock_extrair.side_effect = [
            Exception("Erro OCR"),
            [_make_comprovante()],
        ]
        files = [FakeFileStorage("bad.pdf"), FakeFileStorage("good.pdf")]
        result = processar_lote(files)

        assert result["summary"]["success_files"] == 1
        assert result["summary"]["error_files"] == 1
        assert result["files"][0].status == "error"
        assert "Erro OCR" in result["files"][0].error_message
        assert result["files"][1].status == "done"

    @patch("src.batch_processor.extrair_pdf")
    def test_pdf_sem_comprovantes(self, mock_extrair):
        mock_extrair.return_value = []
        files = [FakeFileStorage("empty.pdf")]
        result = processar_lote(files)

        assert result["summary"]["error_files"] == 1
        assert result["files"][0].status == "error"
        assert "Nenhum comprovante" in result["files"][0].error_message

    @patch("src.batch_processor.extrair_pdf")
    def test_lista_vazia(self, mock_extrair):
        result = processar_lote([])
        assert result["summary"]["total_files"] == 0
        assert result["summary"]["total_bolsas"] == 0

    @patch("src.batch_processor.extrair_pdf")
    def test_linhas_consolidadas(self, mock_extrair):
        mock_extrair.side_effect = [
            [_make_comprovante("100", 2)],
            [_make_comprovante("200", 4)],
        ]
        files = [FakeFileStorage("a.pdf"), FakeFileStorage("b.pdf")]
        result = processar_lote(files)

        assert len(result["all_linhas"]) == 6  # 2 + 4
        assert result["files"][0].bolsa_count == 2
        assert result["files"][1].bolsa_count == 4

    @patch("src.batch_processor.extrair_pdf")
    def test_comprovante_nums(self, mock_extrair):
        mock_extrair.return_value = [_make_comprovante("1292305")]
        files = [FakeFileStorage("a.pdf")]
        result = processar_lote(files)

        assert result["files"][0].comprovante_nums == "1292305"

    @patch("src.batch_processor.extrair_pdf")
    def test_cleanup_temp_files(self, mock_extrair):
        """Temp files should be cleaned up even on error."""
        mock_extrair.side_effect = Exception("boom")
        files = [FakeFileStorage("fail.pdf")]
        result = processar_lote(files)
        # Should not raise, temp file should be cleaned
        assert result["files"][0].status == "error"
