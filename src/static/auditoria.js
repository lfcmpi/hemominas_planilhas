/* Auditoria - client-side logic */

const state = {
    page: 1,
    per_page: 25,
    data_inicio: "",
    data_fim: "",
    user_email: "",
    operacao: "",
};

const BADGE_COLORS = {
    LOGIN: "#16a34a",
    LOGOUT: "#6b7280",
    LOGIN_FALHA: "#dc2626",
    UPLOAD_PDF: "#2563eb",
    UPLOAD_BATCH: "#2563eb",
    ENVIAR_PLANILHA: "#7c3aed",
    ENVIAR_BATCH: "#7c3aed",
    EDITAR_CAMPO: "#d97706",
    CRIAR_USUARIO: "#0891b2",
    ATUALIZAR_USUARIO: "#0891b2",
    EXCLUIR_USUARIO: "#dc2626",
    ALTERAR_CONFIG: "#4b5563",
    ALTERAR_ALERTAS: "#d97706",
    UPLOAD_CREDENCIAIS: "#4b5563",
    SYNC_MANUAL: "#059669",
    SYNC_PENDENTES: "#059669",
};

function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

function formatTimestamp(ts) {
    if (!ts) return "-";
    try {
        const d = new Date(ts);
        return d.toLocaleDateString("pt-BR") + " " +
            d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
        return ts;
    }
}

function formatDetalhes(detalhesStr) {
    if (!detalhesStr) return "";
    try {
        const obj = JSON.parse(detalhesStr);
        const parts = [];
        for (const [k, v] of Object.entries(obj)) {
            if (k === "valor_anterior" || k === "valor_novo") continue;
            parts.push(`<span class="audit-detail-key">${esc(k)}:</span> ${esc(String(v))}`);
        }
        if (obj.valor_anterior !== undefined || obj.valor_novo !== undefined) {
            const ant = obj.valor_anterior || "(vazio)";
            const novo = obj.valor_novo || "(vazio)";
            parts.push(`<span class="audit-change">${esc(ant)} &rarr; ${esc(novo)}</span>`);
        }
        return parts.join(", ");
    } catch {
        return esc(detalhesStr);
    }
}

function carregarDados() {
    const params = new URLSearchParams({
        page: state.page,
        per_page: state.per_page,
    });
    if (state.data_inicio) params.set("data_inicio", state.data_inicio);
    if (state.data_fim) params.set("data_fim", state.data_fim);
    if (state.user_email) params.set("user_email", state.user_email);
    if (state.operacao) params.set("operacao", state.operacao);

    fetch("/api/auditoria?" + params.toString())
        .then(r => r.json())
        .then(data => {
            renderTabela(data.registros);
            renderPaginacao(data.total, data.page, data.per_page);
        })
        .catch(() => {
            document.getElementById("audit-tbody").innerHTML =
                '<tr><td colspan="5" style="text-align:center;color:#999;padding:2rem">Erro ao carregar dados.</td></tr>';
        });
}

function renderTabela(rows) {
    const tbody = document.getElementById("audit-tbody");
    if (!rows || rows.length === 0) {
        tbody.innerHTML =
            '<tr><td colspan="5" style="text-align:center;color:#999;padding:2rem">Nenhum registro encontrado.</td></tr>';
        return;
    }

    tbody.innerHTML = rows.map(r => {
        const color = BADGE_COLORS[r.operacao] || "#6b7280";
        const badge = `<span class="audit-badge" style="background:${color}">${esc(r.operacao)}</span>`;
        const user = r.user_name ? `${esc(r.user_name)}<br><small>${esc(r.user_email)}</small>` : esc(r.user_email);
        return `<tr>
            <td>${formatTimestamp(r.timestamp)}</td>
            <td>${user}</td>
            <td>${badge}</td>
            <td>${esc(r.descricao)}</td>
            <td class="audit-detalhes-cell">${formatDetalhes(r.detalhes)}</td>
        </tr>`;
    }).join("");
}

function renderPaginacao(total, page, perPage) {
    const totalPages = Math.ceil(total / perPage) || 1;
    const info = document.getElementById("pagination-info");
    const start = total === 0 ? 0 : (page - 1) * perPage + 1;
    const end = Math.min(page * perPage, total);
    info.textContent = `${start}-${end} de ${total} registros`;

    const btns = document.getElementById("pagination-btns");
    let html = "";

    html += `<button class="btn btn-secondary btn-sm" ${page <= 1 ? "disabled" : ""} onclick="irPagina(${page - 1})">Anterior</button>`;

    const maxBtns = 5;
    let startP = Math.max(1, page - Math.floor(maxBtns / 2));
    let endP = Math.min(totalPages, startP + maxBtns - 1);
    if (endP - startP < maxBtns - 1) startP = Math.max(1, endP - maxBtns + 1);

    for (let i = startP; i <= endP; i++) {
        const cls = i === page ? "btn-primary" : "btn-secondary";
        html += `<button class="btn ${cls} btn-sm" onclick="irPagina(${i})">${i}</button>`;
    }

    html += `<button class="btn btn-secondary btn-sm" ${page >= totalPages ? "disabled" : ""} onclick="irPagina(${page + 1})">Proximo</button>`;
    btns.innerHTML = html;
}

function irPagina(p) {
    if (p < 1) return;
    state.page = p;
    carregarDados();
}

function filtrar() {
    state.data_inicio = document.getElementById("audit-data-inicio").value;
    state.data_fim = document.getElementById("audit-data-fim").value;
    state.user_email = document.getElementById("audit-usuario").value;
    state.operacao = document.getElementById("audit-operacao").value;
    state.page = 1;
    carregarDados();
}

function limparFiltros() {
    document.getElementById("audit-data-inicio").value = "";
    document.getElementById("audit-data-fim").value = "";
    document.getElementById("audit-usuario").value = "";
    document.getElementById("audit-operacao").value = "";
    state.data_inicio = "";
    state.data_fim = "";
    state.user_email = "";
    state.operacao = "";
    state.page = 1;
    carregarDados();
}

function carregarFiltros() {
    fetch("/api/auditoria/filtros")
        .then(r => r.json())
        .then(data => {
            const selUser = document.getElementById("audit-usuario");
            data.usuarios.forEach(u => {
                const opt = document.createElement("option");
                opt.value = u;
                opt.textContent = u;
                selUser.appendChild(opt);
            });
            const selOp = document.getElementById("audit-operacao");
            data.operacoes.forEach(o => {
                const opt = document.createElement("option");
                opt.value = o;
                opt.textContent = o;
                selOp.appendChild(opt);
            });
        })
        .catch(() => {});
}

document.getElementById("per-page-select").addEventListener("change", e => {
    state.per_page = parseInt(e.target.value);
    state.page = 1;
    carregarDados();
});

// Init
carregarFiltros();
carregarDados();
