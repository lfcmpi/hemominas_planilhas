import os
import tempfile
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user

from src.auth import (
    authenticate,
    atualizar_usuario,
    criar_usuario,
    excluir_usuario,
    get_user_by_id,
    init_users_table,
    listar_usuarios,
    role_required,
    seed_default_user,
)
from src.batch_processor import processar_lote
from src.config import (
    GOOGLE_SHEETS_ID,
    MAX_BATCH_FILES,
    MAX_UPLOAD_SIZE_MB,
    SECRET_KEY,
    SESSION_LIFETIME_MINUTES,
    SQLITE_DB_PATH,
)
from src.dashboard_service import DashboardService
from src.field_mapper import LinhaPlanilha, mapear_comprovantes
from src.history_store import (
    init_db,
    listar_auditoria,
    listar_importacoes,
    obter_alert_config,
    obter_app_config,
    obter_distribuicao_bolsas,
    obter_estatisticas_importacoes,
    obter_evolucao_diaria,
    obter_evolucao_por_tipo,
    obter_filtros_auditoria,
    obter_importacao,
    obter_top_bolsas_recentes,
    registrar_importacao,
    registrar_operacao,
    salvar_alert_config,
)
from src.pdf_extractor import extrair_pdf
from src.sheets_reader import (
    ler_bolsas_existentes,
    ler_bolsas_existentes_local,
    ler_planilha_completa,
    ler_valores_base,
    ler_valores_base_local,
)
from src.sheets_writer import escrever_linhas
from src.sync_service import (
    atualizar_campo_planilha,
    contar_pendentes,
    consultar_planilha,
    executar_sync,
    obter_sync_status,
    salvar_linhas_local,
    sincronizar_pendentes,
)
from src.validators import montar_preview, validar_campo, validar_linha

_src_dir = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(_src_dir / "templates"),
    static_folder=str(_src_dir / "static"),
)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE_MB * 1024 * 1024
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = timedelta(minutes=SESSION_LIFETIME_MINUTES)

# Phase 4: Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login_page"


@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(SQLITE_DB_PATH, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return jsonify({"error": "Nao autenticado."}), 401
    return redirect(url_for("login_page"))


# Phase 3: Initialize SQLite on startup
init_db(SQLITE_DB_PATH)
init_users_table(SQLITE_DB_PATH)
seed_default_user(SQLITE_DB_PATH)
dashboard_service = DashboardService()

# Phase 6: Load UI-managed configs from database
from src.config_loader import aplicar_config_runtime, carregar_config_do_banco
carregar_config_do_banco(SQLITE_DB_PATH)


def _client_ip():
    """Return the client IP address (supports proxied requests)."""
    return request.headers.get("X-Forwarded-For", request.remote_addr or "")


def _audit(operacao, descricao, detalhes=None, entidade_tipo="", entidade_id=""):
    """Shorthand to log an audit entry for the current user."""
    registrar_operacao(
        SQLITE_DB_PATH,
        current_user.email,
        current_user.name,
        operacao,
        descricao,
        detalhes=detalhes,
        ip_address=_client_ip(),
        entidade_tipo=entidade_tipo,
        entidade_id=entidade_id,
    )


@app.route("/login", methods=["GET"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_submit():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    user = authenticate(SQLITE_DB_PATH, email, password)
    if user is None:
        registrar_operacao(
            SQLITE_DB_PATH, email, "", "LOGIN_FALHA",
            f"Tentativa de login falhou para {email}",
            ip_address=_client_ip(), entidade_tipo="usuario",
        )
        return render_template("login.html", error="Email ou senha incorretos.")
    login_user(user, remember=True)
    registrar_operacao(
        SQLITE_DB_PATH, user.email, user.name, "LOGIN",
        f"{user.name} realizou login",
        ip_address=_client_ip(), entidade_tipo="usuario",
    )
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    if current_user.is_authenticated:
        _audit("LOGOUT", f"{current_user.name} realizou logout")
    logout_user()
    return redirect(url_for("login_page"))


# === UPLOAD (admin, manager, uploader) ===

@app.route("/")
@login_required
@role_required("admin", "manager", "uploader")
def index():
    return render_template("index.html", active_page="upload")


def _serialize_preview(p):
    """Serialize a LinhaPreview to JSON-safe dict."""
    return {
        "num_comprovante": p.num_comprovante,
        "data_entrada": p.linha.data_entrada.strftime("%d/%m/%Y") if p.linha.data_entrada else "",
        "data_validade": p.linha.data_validade.strftime("%d/%m/%Y") if p.linha.data_validade else "",
        "tipo_hemocomponente": p.linha.tipo_hemocomponente,
        "gs_rh": p.linha.gs_rh,
        "volume": p.linha.volume,
        "responsavel": p.linha.responsavel_recepcao,
        "num_bolsa": p.linha.num_bolsa,
        "inst_coleta": p.linha.inst_coleta,
        "selecionada": p.selecionada,
        "erros": [
            {
                "campo": e.campo,
                "valor_atual": e.valor_atual,
                "mensagem": e.mensagem,
                "nivel": e.nivel,
                "valores_validos": e.valores_validos,
            }
            for e in p.erros
        ],
        "duplicata": {
            "num_bolsa": p.duplicata.num_bolsa,
            "linha_planilha": p.duplicata.linha_planilha,
            "data_cadastro": p.duplicata.data_cadastro,
        } if p.duplicata else None,
    }


@app.route("/api/upload", methods=["POST"])
@login_required
@role_required("admin", "manager", "uploader")
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nenhum arquivo selecionado."}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Arquivo nao e PDF valido."}), 400

    # Save to temp file for processing
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        # Phase 1: Extract and map
        comprovantes = extrair_pdf(tmp_path)

        if not comprovantes:
            return jsonify({"error": "Nenhum comprovante encontrado no PDF."}), 400

        linhas = mapear_comprovantes(comprovantes, tolerante=True)

        # Phase 2: Validate against BASE + detect duplicates (with offline fallback)
        sheets_online = True
        try:
            base = ler_valores_base(GOOGLE_SHEETS_ID)
            bolsas_existentes = ler_bolsas_existentes(GOOGLE_SHEETS_ID)
        except Exception:
            base = ler_valores_base_local(SQLITE_DB_PATH)
            bolsas_existentes = ler_bolsas_existentes_local(SQLITE_DB_PATH)
            sheets_online = False

        preview = montar_preview(linhas, comprovantes, base, bolsas_existentes)

        # Build summary
        total_duplicatas = sum(1 for p in preview if p.duplicata)
        total_erros = sum(
            1 for p in preview if any(e.nivel == "error" for e in p.erros)
        )
        total_warnings = sum(
            1 for p in preview if any(e.nivel == "warning" for e in p.erros)
        )

        _audit("UPLOAD_PDF", f"Upload PDF: {file.filename} ({len(linhas)} bolsas)",
               detalhes={"filename": file.filename, "bolsas": len(linhas)},
               entidade_tipo="bolsa")

        return jsonify({
            "comprovantes": len(comprovantes),
            "total_bolsas": sum(len(c.bolsas) for c in comprovantes),
            "linhas": [_serialize_preview(p) for p in preview],
            "resumo": {
                "total_bolsas": len(linhas),
                "total_comprovantes": len(comprovantes),
                "total_duplicatas": total_duplicatas,
                "total_erros_criticos": total_erros,
                "total_warnings": total_warnings,
            },
            "base_values": {
                "tipos_hemocomponente": base.tipos_hemocomponente,
                "gs_rh": base.gs_rh,
            },
            "sheets_online": sheets_online,
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao processar PDF: {str(e)}"}), 500
    finally:
        os.unlink(tmp_path)


@app.route("/api/enviar", methods=["POST"])
@login_required
@role_required("admin", "manager", "uploader")
def enviar_planilha():
    data = request.get_json()
    if not data or "linhas" not in data:
        return jsonify({"error": "Dados invalidos."}), 400

    linhas_json = data["linhas"]
    if not linhas_json:
        return jsonify({"error": "Nenhuma linha para enviar."}), 400

    try:
        # Revalidate before writing (with offline fallback)
        try:
            base = ler_valores_base(GOOGLE_SHEETS_ID)
        except Exception:
            base = ler_valores_base_local(SQLITE_DB_PATH)

        linhas = []
        for item in linhas_json:
            dt_entrada = (
                datetime.strptime(item["data_entrada"], "%d/%m/%Y").date()
                if item.get("data_entrada")
                else date.today()
            )
            dt_validade = (
                datetime.strptime(item["data_validade"], "%d/%m/%Y").date()
                if item.get("data_validade")
                else date.today()
            )

            linha = LinhaPlanilha(
                dias_antes_vencimento="",
                status="",
                data_entrada=dt_entrada,
                data_validade=dt_validade,
                tipo_hemocomponente=item.get("tipo_hemocomponente", ""),
                gs_rh=item.get("gs_rh", ""),
                volume=int(item.get("volume", 0)),
                responsavel_recepcao=item.get("responsavel", ""),
                num_bolsa=item.get("num_bolsa", ""),
                inst_coleta=item.get("inst_coleta", ""),
            )

            # Revalidate: reject if critical errors remain
            erros = validar_linha(linha, base)
            erros_criticos = [e for e in erros if e.nivel == "error"]
            if erros_criticos:
                campos = ", ".join(e.campo for e in erros_criticos)
                return jsonify({
                    "error": f"Dados com erros criticos nao resolvidos: {campos}"
                }), 400

            linhas.append(linha)

        # Try writing to Google Sheets; fallback to local DB
        destino = "planilha"
        try:
            resultado = escrever_linhas(linhas)
            threading.Thread(target=executar_sync, args=(SQLITE_DB_PATH,), daemon=True).start()
        except Exception:
            salvar_linhas_local(SQLITE_DB_PATH, linhas)
            resultado = {
                "linhas_inseridas": len(linhas),
                "mensagem": f"{len(linhas)} linha(s) salva(s) localmente. "
                            "Serao sincronizadas com a planilha quando a conexao for restabelecida.",
            }
            destino = "banco_local"

        _audit("ENVIAR_PLANILHA", f"Enviou {len(linhas)} bolsa(s) para {destino}",
               detalhes={"destino": destino, "bolsas": len(linhas)},
               entidade_tipo="bolsa")

        resultado["destino"] = destino
        return jsonify(resultado)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao processar envio: {str(e)}"}), 500


@app.route("/api/validate-field", methods=["POST"])
@login_required
def validate_field():
    """Validate a single field value against BASE (for inline edit revalidation)."""
    data = request.get_json()
    if not data or "campo" not in data or "valor" not in data:
        return jsonify({"error": "Campos 'campo' e 'valor' obrigatorios."}), 400

    try:
        try:
            base = ler_valores_base(GOOGLE_SHEETS_ID)
        except Exception:
            base = ler_valores_base_local(SQLITE_DB_PATH)
        valido, mensagem = validar_campo(data["campo"], data["valor"], base)
        return jsonify({"valido": valido, "mensagem": mensagem})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/batch/upload", methods=["POST"])
@login_required
@role_required("admin", "manager", "uploader")
def batch_upload():
    """Upload e processamento de multiplos PDFs em lote."""
    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "Nenhum arquivo enviado."}), 400

    files = [f for f in files if f.filename != ""]

    if len(files) > MAX_BATCH_FILES:
        return jsonify({"error": f"Maximo {MAX_BATCH_FILES} arquivos por lote."}), 400

    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            return jsonify({"error": f"Arquivo '{f.filename}' nao e PDF valido."}), 400

    try:
        result = processar_lote(files)

        # Validate against BASE + detect duplicates (with offline fallback)
        sheets_online = True
        try:
            base = ler_valores_base(GOOGLE_SHEETS_ID)
            bolsas_existentes = ler_bolsas_existentes(GOOGLE_SHEETS_ID)
        except Exception:
            base = ler_valores_base_local(SQLITE_DB_PATH)
            bolsas_existentes = ler_bolsas_existentes_local(SQLITE_DB_PATH)
            sheets_online = False

        files_json = []
        all_preview = []
        for fs in result["files"]:
            if fs.status == "done":
                preview = montar_preview(fs.linhas, fs.comprovantes, base, bolsas_existentes)
                all_preview.extend(preview)
                files_json.append({
                    "filename": fs.filename,
                    "status": "done",
                    "comprovantes": fs.comprovante_count,
                    "bolsas": fs.bolsa_count,
                    "comprovante_nums": fs.comprovante_nums,
                    "error": None,
                })
            else:
                files_json.append({
                    "filename": fs.filename,
                    "status": "error",
                    "comprovantes": None,
                    "bolsas": None,
                    "comprovante_nums": "",
                    "error": fs.error_message,
                })

        total_duplicatas = sum(1 for p in all_preview if p.duplicata)
        total_erros = sum(
            1 for p in all_preview if any(e.nivel == "error" for e in p.erros)
        )
        total_warnings = sum(
            1 for p in all_preview if any(e.nivel == "warning" for e in p.erros)
        )

        filenames = [f.filename for f in files]
        _audit("UPLOAD_BATCH",
               f"Upload em lote: {len(files)} arquivo(s), {len(all_preview)} bolsa(s)",
               detalhes={"filenames": filenames, "total_bolsas": len(all_preview)},
               entidade_tipo="bolsa")

        return jsonify({
            "files": files_json,
            "linhas": [_serialize_preview(p) for p in all_preview],
            "summary": {
                **result["summary"],
                "total_duplicatas": total_duplicatas,
                "total_erros_criticos": total_erros,
                "total_warnings": total_warnings,
            },
            "base_values": {
                "tipos_hemocomponente": base.tipos_hemocomponente,
                "gs_rh": base.gs_rh,
            },
            "sheets_online": sheets_online,
        })

    except Exception as e:
        return jsonify({"error": f"Erro no processamento em lote: {str(e)}"}), 500


@app.route("/api/batch/enviar", methods=["POST"])
@login_required
@role_required("admin", "manager", "uploader")
def batch_enviar():
    """Envia dados consolidados do lote para Google Sheets + registra no historico."""
    data = request.get_json()
    if not data or "linhas" not in data:
        return jsonify({"error": "Dados invalidos."}), 400

    linhas_json = data["linhas"]
    if not linhas_json:
        return jsonify({"error": "Nenhuma linha para enviar."}), 400

    try:
        # Revalidate (with offline fallback)
        try:
            base = ler_valores_base(GOOGLE_SHEETS_ID)
        except Exception:
            base = ler_valores_base_local(SQLITE_DB_PATH)

        linhas = []
        for item in linhas_json:
            dt_entrada = (
                datetime.strptime(item["data_entrada"], "%d/%m/%Y").date()
                if item.get("data_entrada")
                else date.today()
            )
            dt_validade = (
                datetime.strptime(item["data_validade"], "%d/%m/%Y").date()
                if item.get("data_validade")
                else date.today()
            )

            linha = LinhaPlanilha(
                dias_antes_vencimento="",
                status="",
                data_entrada=dt_entrada,
                data_validade=dt_validade,
                tipo_hemocomponente=item.get("tipo_hemocomponente", ""),
                gs_rh=item.get("gs_rh", ""),
                volume=int(item.get("volume", 0)),
                responsavel_recepcao=item.get("responsavel", ""),
                num_bolsa=item.get("num_bolsa", ""),
                inst_coleta=item.get("inst_coleta", ""),
            )

            erros = validar_linha(linha, base)
            erros_criticos = [e for e in erros if e.nivel == "error"]
            if erros_criticos:
                campos = ", ".join(e.campo for e in erros_criticos)
                return jsonify({
                    "error": f"Dados com erros criticos nao resolvidos: {campos}"
                }), 400

            linhas.append(linha)

        # Always register in history first (independent of Sheets)
        files_info = data.get("files_info", [{"filename": "lote", "comprovante_nums": ""}])
        import_ids = []
        for finfo in files_info:
            class BolsaDetail:
                pass
            bolsas_detail = []
            for item in linhas_json:
                b = BolsaDetail()
                b.num_bolsa = item.get("num_bolsa", "")
                b.tipo_hemocomponente = item.get("tipo_hemocomponente", "")
                b.gs_rh = item.get("gs_rh", "")
                b.volume = int(item.get("volume", 0))
                b.data_validade = item.get("data_validade", "")
                bolsas_detail.append(b)

            import_id = registrar_importacao(
                SQLITE_DB_PATH,
                finfo.get("filename", "lote"),
                finfo.get("comprovante_nums", ""),
                len(bolsas_detail),
                "sucesso",
                None,
                bolsas_detail,
            )
            import_ids.append(import_id)

        # Try writing to Google Sheets; fallback to local DB
        destino = "planilha"
        try:
            resultado = escrever_linhas(linhas)
            threading.Thread(target=executar_sync, args=(SQLITE_DB_PATH,), daemon=True).start()
        except Exception:
            salvar_linhas_local(SQLITE_DB_PATH, linhas)
            resultado = {
                "linhas_inseridas": len(linhas),
                "mensagem": f"{len(linhas)} linha(s) salva(s) localmente. "
                            "Serao sincronizadas com a planilha quando a conexao for restabelecida.",
            }
            destino = "banco_local"

        _audit("ENVIAR_BATCH",
               f"Enviou lote: {len(linhas)} bolsa(s) para {destino}",
               detalhes={"destino": destino, "import_ids": import_ids, "bolsas": len(linhas)},
               entidade_tipo="bolsa")

        resultado["import_ids"] = import_ids
        resultado["destino"] = destino
        return jsonify(resultado)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao processar envio em lote: {str(e)}"}), 500


# === HISTORICO (Phase 3) — all roles ===

@app.route("/historico")
@login_required
def historico_page():
    return render_template("history.html", active_page="historico")


@app.route("/historico/<int:import_id>")
@login_required
def historico_detail_page(import_id):
    return render_template("history_detail.html", active_page="historico")


@app.route("/api/historico")
@login_required
def api_historico():
    """Lista importacoes com filtro opcional por periodo."""
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    importacoes, total = listar_importacoes(
        SQLITE_DB_PATH, data_inicio=data_inicio, data_fim=data_fim,
        page=page, per_page=per_page
    )

    return jsonify({
        "importacoes": importacoes,
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@app.route("/api/historico/<int:import_id>")
@login_required
def api_historico_detail(import_id):
    """Detalhe de uma importacao especifica."""
    result = obter_importacao(SQLITE_DB_PATH, import_id)
    if result is None:
        return jsonify({"error": "Importacao nao encontrada."}), 404
    return jsonify(result)


# === DASHBOARD (Phase 3 + Phase 4 BI) — admin, manager, consulta ===

@app.route("/dashboard")
@login_required
@role_required("admin", "manager", "consulta")
def dashboard_page():
    return render_template("dashboard.html", active_page="dashboard")


@app.route("/api/dashboard")
@login_required
@role_required("admin", "manager", "consulta")
def api_dashboard():
    """Dados agregados de estoque atual + historico. Resiliente a falhas do Google Sheets."""
    force_refresh = request.args.get("force_refresh", "false").lower() == "true"

    # Historical data (always available from SQLite)
    stats = obter_estatisticas_importacoes(SQLITE_DB_PATH)
    evolucao = obter_evolucao_diaria(SQLITE_DB_PATH, dias=30)
    distribuicao = obter_distribuicao_bolsas(SQLITE_DB_PATH)
    evolucao_tipo = obter_evolucao_por_tipo(SQLITE_DB_PATH, dias=30)
    recentes = obter_top_bolsas_recentes(SQLITE_DB_PATH, limit=10)
    alert_config = obter_alert_config(SQLITE_DB_PATH)

    result = {
        "historico": {
            "stats": stats,
            "evolucao_diaria": evolucao,
            "distribuicao": distribuicao,
            "evolucao_tipo": evolucao_tipo,
            "recentes": recentes,
        },
        "threshold_urgente": alert_config["threshold_urgente"],
        "threshold_atencao": alert_config["threshold_atencao"],
        "estoque_disponivel": False,
    }

    # Live stock data (may fail if Google Sheets is unavailable)
    try:
        header, data_rows = ler_planilha_completa(GOOGLE_SHEETS_ID)

        if header:
            resumo = dashboard_service.obter_estoque(header, data_rows, force_refresh=force_refresh)
            result["estoque_disponivel"] = True
            result["estoque"] = {
                "por_gs_rh": [{"tipo": k, "count": v} for k, v in resumo.por_gs_rh.items()],
                "por_hemocomponente": [{"tipo": k, "count": v} for k, v in resumo.por_hemocomponente.items()],
                "total_em_estoque": resumo.total_em_estoque,
                "vencendo": {
                    "vencidas": {
                        "count": len(resumo.vencidas),
                        "bolsas": resumo.vencidas,
                    },
                    "urgente": {
                        "count": len(resumo.vencendo_7d),
                        "bolsas": resumo.vencendo_7d,
                    },
                    "atencao": {
                        "count": len(resumo.vencendo_14d),
                        "bolsas": resumo.vencendo_14d,
                    },
                },
                "ultima_atualizacao": resumo.ultima_atualizacao.strftime("%d/%m/%Y %H:%M:%S")
                    if resumo.ultima_atualizacao else "-",
            }
    except Exception:
        result["estoque_erro"] = "Google Sheets indisponivel. Mostrando dados historicos."

    return jsonify(result)


# === ALERTAS (Phase 3) — admin, manager ===

@app.route("/alertas/config")
@login_required
@role_required("admin", "manager")
def alertas_config_page():
    return render_template("alert_settings.html", active_page="alertas")


@app.route("/api/alertas/config", methods=["GET"])
@login_required
@role_required("admin", "manager")
def api_alertas_config_get():
    """Retorna configuracao atual de alertas."""
    config = obter_alert_config(SQLITE_DB_PATH)
    return jsonify(config)


@app.route("/api/alertas/config", methods=["PUT"])
@login_required
@role_required("admin", "manager")
def api_alertas_config_put():
    """Atualiza configuracao de alertas."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados invalidos."}), 400

    # Validar thresholds
    urgente = data.get("threshold_urgente", 7)
    atencao = data.get("threshold_atencao", 14)
    if urgente >= atencao:
        return jsonify({"error": "Threshold urgente deve ser menor que atencao."}), 400

    salvar_alert_config(SQLITE_DB_PATH, {
        "threshold_urgente": urgente,
        "threshold_atencao": atencao,
        "email_enabled": data.get("email_enabled", False),
        "email_to": data.get("email_to"),
        "inapp_enabled": data.get("inapp_enabled", True),
    })

    _audit("ALTERAR_ALERTAS", "Alterou configuracao de alertas",
           detalhes={"threshold_urgente": urgente, "threshold_atencao": atencao},
           entidade_tipo="config")

    return jsonify({"mensagem": "Configuracao salva com sucesso."})


@app.route("/api/alertas/verificar")
@login_required
@role_required("admin", "manager")
def api_alertas_verificar():
    """Executa verificacao manual de vencimentos."""
    try:
        from src.alert_service import executar_alerta

        header, data_rows = ler_planilha_completa(GOOGLE_SHEETS_ID)
        if not header:
            return jsonify({"urgente": [], "atencao": [], "email_enviado": False})

        import src.email_sender as email_mod
        result = executar_alerta(dashboard_service, header, data_rows, email_mod)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"Erro ao verificar alertas: {str(e)}"}), 500


@app.route("/api/alertas/testar-email", methods=["POST"])
@login_required
@role_required("admin", "manager")
def api_alertas_testar_email():
    """Envia email de teste."""
    try:
        from src.email_sender import testar_smtp
        testar_smtp()
        return jsonify({"mensagem": "Email de teste enviado."})
    except Exception as e:
        return jsonify({"error": f"Erro ao enviar email: {str(e)}"}), 500


@app.route("/api/alertas/pendentes")
@login_required
def api_alertas_pendentes():
    """Retorna contagem de bolsas em alerta (para badge de navegacao)."""
    try:
        header, data_rows = ler_planilha_completa(GOOGLE_SHEETS_ID)
        if not header:
            return jsonify({"vencidas": 0, "urgente": 0, "atencao": 0})

        resumo = dashboard_service.obter_estoque(header, data_rows)
        return jsonify({
            "vencidas": len(resumo.vencidas),
            "urgente": len(resumo.vencendo_7d),
            "atencao": len(resumo.vencendo_14d),
        })
    except Exception:
        return jsonify({"vencidas": 0, "urgente": 0, "atencao": 0})


# === CONSULTA & SYNC (Phase 5) — admin, manager, consulta ===

@app.route("/consulta")
@login_required
@role_required("admin", "manager", "consulta")
def consulta_page():
    return render_template("consulta.html", active_page="consulta",
                           can_edit=current_user.can_edit)


@app.route("/api/sync", methods=["POST"])
@login_required
@role_required("admin", "manager", "consulta")
def api_sync():
    """Trigger manual sync from Google Sheets."""
    result = executar_sync(SQLITE_DB_PATH)
    _audit("SYNC_MANUAL", f"Sincronizacao manual: {result.get('status')}",
           detalhes={"status": result.get("status"), "rows_synced": result.get("rows_synced", 0)},
           entidade_tipo="sync")
    return jsonify(result)


@app.route("/api/pendentes")
@login_required
def api_pendentes():
    """Retorna contagem de registros com pending_sync=1."""
    count = contar_pendentes(SQLITE_DB_PATH)
    return jsonify({"pendentes": count})


@app.route("/api/pendentes/sync", methods=["POST"])
@login_required
def api_pendentes_sync():
    """Tenta sincronizar registros pendentes com Google Sheets."""
    result = sincronizar_pendentes(SQLITE_DB_PATH)
    _audit("SYNC_PENDENTES", f"Sincronizacao pendentes: {result.get('status')}",
           detalhes={"status": result.get("status"), "total": result.get("total", 0)},
           entidade_tipo="sync")
    return jsonify(result)


@app.route("/api/sync/status")
@login_required
def api_sync_status():
    """Return last sync info."""
    status = obter_sync_status(SQLITE_DB_PATH)
    return jsonify(status)


@app.route("/api/consulta")
@login_required
@role_required("admin", "manager", "consulta")
def api_consulta():
    """Query planilha data with pagination, search, sort, filters."""
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))
    search = request.args.get("search", "").strip()
    sort_by = request.args.get("sort_by", "data_entrada")
    sort_dir = request.args.get("sort_dir", "desc")

    filters = {}
    for f in ["gs_rh", "tipo_hemocomponente", "status_vencimento"]:
        val = request.args.get(f)
        if val:
            filters[f] = val

    # Vencimento range filter (from dashboard links)
    dias_max = request.args.get("dias_vencimento_max")
    if dias_max is not None:
        filters["dias_vencimento_max"] = dias_max

    # Vencidas filter (expired bags, dias < 0)
    vencidas = request.args.get("vencidas")
    if vencidas:
        filters["vencidas"] = vencidas

    result = consultar_planilha(SQLITE_DB_PATH, page, per_page, search, sort_by, sort_dir, filters)
    return jsonify(result)


# === INLINE EDIT (admin, manager) ===

@app.route("/api/planilha_data/<num_bolsa>", methods=["PUT"])
@login_required
@role_required("admin", "manager")
def api_planilha_edit(num_bolsa):
    """Update fields of a planilha_data row (inline editing)."""
    data = request.get_json()
    if not data or "campo" not in data or "valor" not in data:
        return jsonify({"error": "Campos 'campo' e 'valor' obrigatorios."}), 400

    try:
        result = atualizar_campo_planilha(
            SQLITE_DB_PATH, num_bolsa, data["campo"],
            data["valor"], current_user.email,
        )
        _audit("EDITAR_CAMPO",
               f"Editou {data['campo']} da bolsa {num_bolsa}",
               detalhes={
                   "campo": data["campo"],
                   "num_bolsa": num_bolsa,
                   "valor_anterior": result.get("valor_anterior", ""),
                   "valor_novo": data["valor"],
               },
               entidade_tipo="bolsa", entidade_id=num_bolsa)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao atualizar: {str(e)}"}), 500


# === API ME (role info for frontend) ===

@app.route("/api/me")
@login_required
def api_me():
    """Return current user info including role."""
    return jsonify({
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "can_edit": current_user.can_edit,
    })


# === CONFIGURACOES (Phase 6) — admin only ===

@app.route("/configuracoes")
@login_required
@role_required("admin")
def configuracoes_page():
    return render_template("configuracoes.html", active_page="configuracoes")


@app.route("/api/configuracoes", methods=["GET"])
@login_required
@role_required("admin")
def api_configuracoes_get():
    """Retorna config completa. SMTP_PASSWORD mascarado."""
    import src.config as config_mod
    from src.config_loader import _CONFIG_KEYS

    result = {}
    for db_key, (attr_name, tipo) in _CONFIG_KEYS.items():
        val = getattr(config_mod, attr_name, "")
        if tipo == bool:
            result[db_key] = bool(val)
        elif tipo == int:
            result[db_key] = int(val) if val else 0
        else:
            result[db_key] = str(val) if val else ""

    # Mascarar senha SMTP
    if result.get("smtp_password"):
        result["smtp_password"] = "\u2022\u2022\u2022\u2022\u2022\u2022"

    # Verificar se arquivo de credenciais existe
    creds_path = Path(config_mod.GOOGLE_CREDENTIALS_PATH)
    result["credentials_file_exists"] = creds_path.exists()
    result["google_credentials_path"] = str(config_mod.GOOGLE_CREDENTIALS_PATH)

    return jsonify(result)


@app.route("/api/configuracoes", methods=["PUT"])
@login_required
@role_required("admin")
def api_configuracoes_put():
    """Salva + aplica config em runtime. Se smtp_password == mascarado, mantem atual."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados invalidos."}), 400

    import src.config as config_mod

    # Se senha mascarada, manter a atual
    if data.get("smtp_password") == "\u2022\u2022\u2022\u2022\u2022\u2022":
        data["smtp_password"] = config_mod.SMTP_PASSWORD

    # Log config changes (exclude sensitive fields)
    safe_keys = [k for k in data if k not in ("smtp_password",)]
    aplicar_config_runtime(SQLITE_DB_PATH, data)
    _audit("ALTERAR_CONFIG", "Alterou configuracoes do sistema",
           detalhes={"campos_alterados": safe_keys},
           entidade_tipo="config")
    return jsonify({"mensagem": "Configuracoes salvas com sucesso."})


@app.route("/api/configuracoes/testar-sheets", methods=["POST"])
@login_required
@role_required("admin")
def api_testar_sheets():
    """Testa conexao com Google Sheets."""
    try:
        from src.sheets_writer import testar_conexao
        result = testar_conexao()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/configuracoes/testar-smtp", methods=["POST"])
@login_required
@role_required("admin")
def api_testar_smtp():
    """Envia email de teste SMTP."""
    try:
        from src.email_sender import testar_smtp
        testar_smtp()
        return jsonify({"mensagem": "Email de teste enviado com sucesso."})
    except Exception as e:
        return jsonify({"error": f"Erro SMTP: {str(e)}"}), 500


@app.route("/api/configuracoes/upload-credentials", methods=["POST"])
@login_required
@role_required("admin")
def api_upload_credentials():
    """Recebe JSON file de credenciais, valida e salva."""
    import json

    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nenhum arquivo selecionado."}), 400

    try:
        content = file.read()
        json.loads(content)  # Valida que e JSON valido
    except (json.JSONDecodeError, ValueError):
        return jsonify({"error": "Arquivo nao e um JSON valido."}), 400

    import src.config as config_mod
    creds_path = Path(config_mod.GOOGLE_CREDENTIALS_PATH)
    creds_path.parent.mkdir(parents=True, exist_ok=True)
    creds_path.write_bytes(content)

    _audit("UPLOAD_CREDENCIAIS", "Fez upload de arquivo de credenciais Google",
           entidade_tipo="config")

    return jsonify({
        "mensagem": "Credenciais salvas com sucesso.",
        "path": str(creds_path),
    })


# === GERENCIAR USUARIOS (admin only) ===

@app.route("/usuarios")
@login_required
@role_required("admin")
def usuarios_page():
    return render_template("usuarios.html", active_page="usuarios")


@app.route("/api/usuarios", methods=["GET"])
@login_required
@role_required("admin")
def api_usuarios_list():
    """Lista todos os usuarios."""
    users = listar_usuarios(SQLITE_DB_PATH)
    return jsonify({"usuarios": users})


@app.route("/api/usuarios", methods=["POST"])
@login_required
@role_required("admin")
def api_usuarios_create():
    """Cria novo usuario."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados invalidos."}), 400

    try:
        user_id = criar_usuario(
            SQLITE_DB_PATH,
            data.get("email", ""),
            data.get("name", ""),
            data.get("password", ""),
            data.get("role", "consulta"),
        )
        _audit("CRIAR_USUARIO",
               f"Criou usuario {data.get('email')} ({data.get('role', 'consulta')})",
               detalhes={"email": data.get("email"), "name": data.get("name"),
                         "role": data.get("role", "consulta")},
               entidade_tipo="usuario", entidade_id=str(user_id))
        return jsonify({"id": user_id, "mensagem": "Usuario criado com sucesso."})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/usuarios/<int:user_id>", methods=["PUT"])
@login_required
@role_required("admin")
def api_usuarios_update(user_id):
    """Atualiza usuario (name, role, password)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados invalidos."}), 400

    try:
        atualizar_usuario(
            SQLITE_DB_PATH,
            user_id,
            name=data.get("name"),
            role=data.get("role"),
            password=data.get("password") if data.get("password") else None,
        )
        campos = [k for k in ("name", "role", "password") if data.get(k)]
        _audit("ATUALIZAR_USUARIO",
               f"Atualizou usuario ID {user_id}",
               detalhes={"user_id": user_id, "campos_alterados": campos},
               entidade_tipo="usuario", entidade_id=str(user_id))
        return jsonify({"mensagem": "Usuario atualizado com sucesso."})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/usuarios/<int:user_id>", methods=["DELETE"])
@login_required
@role_required("admin")
def api_usuarios_delete(user_id):
    """Exclui usuario."""
    # Prevent admin from deleting themselves
    if user_id == current_user.id:
        return jsonify({"error": "Voce nao pode excluir seu proprio usuario."}), 400

    try:
        excluir_usuario(SQLITE_DB_PATH, user_id)
        _audit("EXCLUIR_USUARIO",
               f"Excluiu usuario ID {user_id}",
               detalhes={"user_id": user_id},
               entidade_tipo="usuario", entidade_id=str(user_id))
        return jsonify({"mensagem": "Usuario excluido com sucesso."})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# === AUDITORIA — admin, manager ===

@app.route("/auditoria")
@login_required
@role_required("admin", "manager")
def auditoria_page():
    return render_template("auditoria.html", active_page="auditoria")


@app.route("/api/auditoria")
@login_required
@role_required("admin", "manager")
def api_auditoria():
    """Lista registros de auditoria com filtros e paginacao."""
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")
    user_email = request.args.get("user_email")
    operacao = request.args.get("operacao")

    registros, total = listar_auditoria(
        SQLITE_DB_PATH, data_inicio=data_inicio, data_fim=data_fim,
        user_email=user_email, operacao=operacao, page=page, per_page=per_page,
    )

    return jsonify({
        "registros": registros,
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@app.route("/api/auditoria/filtros")
@login_required
@role_required("admin", "manager")
def api_auditoria_filtros():
    """Retorna listas distintas de usuarios e operacoes."""
    filtros = obter_filtros_auditoria(SQLITE_DB_PATH)
    return jsonify(filtros)


# Initialize scheduler if enabled
from src.scheduler import iniciar_scheduler
iniciar_scheduler(app, dashboard_service)


if __name__ == "__main__":
    app.run(debug=True, port=4000)
