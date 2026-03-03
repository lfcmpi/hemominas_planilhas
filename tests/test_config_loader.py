"""Tests para config_loader.py — sincronizacao banco <-> runtime."""

import os
import tempfile

import pytest

from src.history_store import init_db, obter_app_config, salvar_app_config


@pytest.fixture
def db_path():
    """Cria banco temporario para cada teste."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    os.unlink(path)


class TestCarregarConfigDoBanco:
    def test_banco_vazio_mantem_defaults(self, db_path, monkeypatch):
        """Com banco vazio, carregar_config_do_banco nao altera src.config."""
        import src.config as config_mod

        original_id = config_mod.GOOGLE_SHEETS_ID
        original_tab = config_mod.SHEET_TAB_NAME

        from src.config_loader import carregar_config_do_banco
        carregar_config_do_banco(db_path)

        assert config_mod.GOOGLE_SHEETS_ID == original_id
        assert config_mod.SHEET_TAB_NAME == original_tab

    def test_sobrescreve_config_com_valor_do_banco(self, db_path, monkeypatch):
        """Valor no banco sobrescreve src.config."""
        import src.config as config_mod

        salvar_app_config(db_path, {"google_sheets_id": "NOVO_ID_123"})

        from src.config_loader import carregar_config_do_banco
        carregar_config_do_banco(db_path)

        assert config_mod.GOOGLE_SHEETS_ID == "NOVO_ID_123"

        # Cleanup
        monkeypatch.setattr(config_mod, "GOOGLE_SHEETS_ID", "")

    def test_nao_sobrescreve_com_valor_vazio(self, db_path, monkeypatch):
        """Valor vazio no banco nao sobrescreve o default."""
        import src.config as config_mod

        monkeypatch.setattr(config_mod, "SHEET_TAB_NAME", "ORIGINAL")
        salvar_app_config(db_path, {"sheet_tab_name": ""})

        from src.config_loader import carregar_config_do_banco
        carregar_config_do_banco(db_path)

        assert config_mod.SHEET_TAB_NAME == "ORIGINAL"


class TestAplicarConfigRuntime:
    def test_salva_no_banco(self, db_path):
        """aplicar_config_runtime salva valores no banco."""
        from src.config_loader import aplicar_config_runtime

        aplicar_config_runtime(db_path, {
            "google_sheets_id": "TEST_ID",
            "smtp_host": "smtp.test.com",
        })

        stored = obter_app_config(db_path)
        assert stored["google_sheets_id"] == "TEST_ID"
        assert stored["smtp_host"] == "smtp.test.com"

    def test_propaga_para_config(self, db_path, monkeypatch):
        """aplicar_config_runtime atualiza atributos em src.config."""
        import src.config as config_mod
        from src.config_loader import aplicar_config_runtime

        aplicar_config_runtime(db_path, {"smtp_port": "465"})

        assert config_mod.SMTP_PORT == 465

        # Cleanup
        monkeypatch.setattr(config_mod, "SMTP_PORT", 587)


class TestConversaoTipos:
    def test_str_para_bool_true(self, db_path, monkeypatch):
        """Converte 'true' para True."""
        import src.config as config_mod
        from src.config_loader import aplicar_config_runtime

        aplicar_config_runtime(db_path, {"smtp_enabled": "true"})
        assert config_mod.SMTP_ENABLED is True

        monkeypatch.setattr(config_mod, "SMTP_ENABLED", False)

    def test_str_para_bool_false(self, db_path, monkeypatch):
        """Converte 'false' para False."""
        import src.config as config_mod
        from src.config_loader import aplicar_config_runtime

        aplicar_config_runtime(db_path, {"smtp_enabled": "false"})
        assert config_mod.SMTP_ENABLED is False

    def test_str_para_int(self, db_path, monkeypatch):
        """Converte string numerica para int."""
        import src.config as config_mod
        from src.config_loader import aplicar_config_runtime

        aplicar_config_runtime(db_path, {"cache_ttl_seconds": "600"})
        assert config_mod.CACHE_TTL_SECONDS == 600

        monkeypatch.setattr(config_mod, "CACHE_TTL_SECONDS", 300)


class TestSenhaMascarada:
    def test_senha_vazia_nao_perde_valor(self, db_path, monkeypatch):
        """Senha mascarada (vazia) nao deve apagar valor existente no banco."""
        from src.config_loader import aplicar_config_runtime

        # Salvar senha real
        aplicar_config_runtime(db_path, {"smtp_password": "minha_senha"})

        stored = obter_app_config(db_path)
        assert stored["smtp_password"] == "minha_senha"

        # Atualizar sem incluir smtp_password — nao deve alterar
        aplicar_config_runtime(db_path, {"smtp_host": "novo.host.com"})

        stored = obter_app_config(db_path)
        assert stored["smtp_password"] == "minha_senha"
