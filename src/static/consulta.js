/* Consulta de Dados - client-side logic */

const state = {
    page: 1,
    per_page: 25,
    search: "",
    sort_by: "data_entrada",
    sort_dir: "desc",
    filters: {},
};

let debounceTimer = null;
let canEdit = false;

// Fields that can be edited inline
const EDITABLE_FIELDS = [
    "data_transfusao", "destino", "nome_paciente", "setor_transfusao",
    "prontuario_salus", "prontuario_mv", "sus_laudo",
    "reacao_transfusional", "bolsa_sbs", "responsavel_recepcao",
];

// Fields that require validation against BASE before saving
const VALIDATE_FIELDS = ["tipo_hemocomponente", "gs_rh"];

/* ========================
   DATA LOADING
   ======================== */

function carregarDados() {
    const params = new URLSearchParams({
        page: state.page,
        per_page: state.per_page,
        search: state.search,
        sort_by: state.sort_by,
        sort_dir: state.sort_dir,
    });

    for (const [k, v] of Object.entries(state.filters)) {
        if (v) params.set(k, v);
    }

    fetch("/api/consulta?" + params.toString())
        .then(r => r.json())
        .then(data => {
            renderTabela(data.rows);
            renderPaginacao(data.total, data.page, data.per_page);
            atualizarFiltrosUnicos(data.rows);
        })
        .catch(() => {
            document.getElementById("consulta-tbody").innerHTML =
                '<tr><td colspan="18" style="text-align:center;color:#999;padding:2rem">Erro ao carregar dados. Tente sincronizar primeiro.</td></tr>';
        });
}

function renderTabela(rows) {
    const tbody = document.getElementById("consulta-tbody");

    if (!rows || rows.length === 0) {
        tbody.innerHTML =
            '<tr><td colspan="18" style="text-align:center;color:#999;padding:2rem">Nenhum dado encontrado. Clique em "Sincronizar" para importar dados da planilha.</td></tr>';
        return;
    }

    const columns = [
        "status_vencimento", "data_entrada", "data_validade",
        "dias_antes_vencimento", "data_transfusao", "destino",
        "nome_paciente", "tipo_hemocomponente", "gs_rh",
        "volume", "responsavel_recepcao", "setor_transfusao",
        "num_bolsa", "prontuario_salus", "prontuario_mv",
        "sus_laudo", "reacao_transfusional", "bolsa_sbs"
    ];

    tbody.innerHTML = rows.map(r => {
        const statusClass = getStatusClass(r.status_vencimento);
        const numBolsa = esc(r.num_bolsa || "");

        return `<tr data-num-bolsa="${numBolsa}">` + columns.map(col => {
            const val = col === "volume" ? (r[col] != null ? r[col] : "-") : esc(r[col] || "-");
            const isEditable = canEdit && EDITABLE_FIELDS.includes(col);
            const editClass = isEditable ? ' class="editable" data-field="' + col + '"' : '';

            if (col === "status_vencimento") {
                return `<td><span class="${statusClass}">${val}</span></td>`;
            }
            return `<td${editClass}>${val}</td>`;
        }).join("") + `</tr>`;
    }).join("");

    // Attach double-click handlers for editable cells
    if (canEdit) {
        attachEditHandlers();
    }
}

function getStatusClass(status) {
    if (!status) return "status-tag";
    const s = status.toUpperCase();
    if (s === "VENCIDO") return "status-tag status-vencido";
    if (s === "VENCE HOJE") return "status-tag status-hoje";
    if (s.startsWith("VENCE EM")) {
        const match = s.match(/\d+/);
        if (match && parseInt(match[0]) <= 7) return "status-tag status-urgente";
    }
    return "status-tag";
}

function esc(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}

/* ========================
   INLINE EDITING
   ======================== */

function attachEditHandlers() {
    document.querySelectorAll(".consulta-table td.editable").forEach(td => {
        td.addEventListener("dblclick", startEditing);
    });
}

function startEditing(e) {
    const td = e.currentTarget;
    if (td.classList.contains("editing")) return;

    const field = td.dataset.field;
    const row = td.closest("tr");
    const numBolsa = row.dataset.numBolsa;
    const currentValue = td.textContent === "-" ? "" : td.textContent;

    td.classList.add("editing");
    td.innerHTML = "";

    const input = document.createElement("input");
    input.type = "text";
    input.value = currentValue;
    input.dataset.originalValue = currentValue;
    td.appendChild(input);
    input.focus();
    input.select();

    // Save on Enter, cancel on Escape
    input.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            finishEditing(td, numBolsa, field, input.value, input.dataset.originalValue);
        } else if (ev.key === "Escape") {
            cancelEditing(td, input.dataset.originalValue);
        }
    });

    // Save on blur (click away)
    input.addEventListener("blur", function () {
        // Delay to allow keydown to fire first
        setTimeout(() => {
            if (td.classList.contains("editing")) {
                finishEditing(td, numBolsa, field, input.value, input.dataset.originalValue);
            }
        }, 100);
    });
}

function cancelEditing(td, originalValue) {
    td.classList.remove("editing");
    td.textContent = originalValue || "-";
}

function finishEditing(td, numBolsa, field, newValue, originalValue) {
    td.classList.remove("editing");

    // If value didn't change, just restore
    if (newValue === originalValue) {
        td.textContent = newValue || "-";
        return;
    }

    td.textContent = newValue || "-";

    // Save via API
    saveField(td, numBolsa, field, newValue);
}

function saveField(td, numBolsa, field, value) {
    fetch(`/api/planilha_data/${encodeURIComponent(numBolsa)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ campo: field, valor: value }),
    })
        .then(r => {
            if (!r.ok) return r.json().then(d => { throw new Error(d.error || "Erro"); });
            return r.json();
        })
        .then(() => {
            // Visual feedback: green flash
            td.classList.remove("edit-error");
            td.classList.add("edit-saved");
            setTimeout(() => td.classList.remove("edit-saved"), 1500);
        })
        .catch(err => {
            // Visual feedback: red flash
            td.classList.remove("edit-saved");
            td.classList.add("edit-error");
            setTimeout(() => td.classList.remove("edit-error"), 1500);
            console.error("Erro ao salvar:", err.message);
        });
}

/* ========================
   PAGINATION
   ======================== */

function renderPaginacao(total, page, perPage) {
    const totalPages = Math.max(1, Math.ceil(total / perPage));
    const start = total === 0 ? 0 : (page - 1) * perPage + 1;
    const end = Math.min(page * perPage, total);

    document.getElementById("pagination-info").textContent =
        `Mostrando ${start}-${end} de ${total}`;

    const btnsEl = document.getElementById("pagination-btns");
    let html = "";

    html += `<button class="btn btn-secondary btn-sm" ${page <= 1 ? "disabled" : ""} onclick="mudarPagina(${page - 1})">Anterior</button>`;

    // Show page numbers (max 5 visible)
    let startPage = Math.max(1, page - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    if (endPage - startPage < 4) startPage = Math.max(1, endPage - 4);

    for (let i = startPage; i <= endPage; i++) {
        const cls = i === page ? "btn btn-primary btn-sm" : "btn btn-secondary btn-sm";
        html += ` <button class="${cls}" onclick="mudarPagina(${i})">${i}</button>`;
    }

    html += ` <button class="btn btn-secondary btn-sm" ${page >= totalPages ? "disabled" : ""} onclick="mudarPagina(${page + 1})">Proximo</button>`;

    btnsEl.innerHTML = html;
}

function mudarPagina(n) {
    if (n < 1) return;
    state.page = n;
    carregarDados();
}

/* ========================
   SEARCH & FILTERS
   ======================== */

function buscar(termo) {
    state.search = termo;
    state.page = 1;
    carregarDados();
}

function aplicarFiltro(campo, valor) {
    if (valor) {
        state.filters[campo] = valor;
    } else {
        delete state.filters[campo];
    }
    state.page = 1;
    carregarDados();
}

function limparFiltros() {
    state.search = "";
    state.filters = {};
    state.page = 1;
    document.getElementById("search-input").value = "";
    document.getElementById("filter-gs-rh").value = "";
    document.getElementById("filter-tipo").value = "";
    // Remove vencimento filter badge
    const badge = document.getElementById("vencimento-filter-badge");
    if (badge) badge.remove();
    // Clean URL params without reload
    if (window.history.replaceState) {
        window.history.replaceState({}, "", "/consulta");
    }
    carregarDados();
}

/* ========================
   SORT
   ======================== */

function ordenar(coluna) {
    if (state.sort_by === coluna) {
        state.sort_dir = state.sort_dir === "asc" ? "desc" : "asc";
    } else {
        state.sort_by = coluna;
        state.sort_dir = "asc";
    }
    state.page = 1;
    atualizarSortIndicators();
    carregarDados();
}

function atualizarSortIndicators() {
    document.querySelectorAll(".consulta-table th.sortable").forEach(th => {
        th.classList.remove("sorted-asc", "sorted-desc");
        if (th.dataset.col === state.sort_by) {
            th.classList.add(state.sort_dir === "asc" ? "sorted-asc" : "sorted-desc");
        }
    });
}

/* ========================
   SYNC
   ======================== */

function sincronizar() {
    const btn = document.getElementById("btn-sync");
    btn.disabled = true;
    btn.classList.add("syncing");

    fetch("/api/sync", { method: "POST" })
        .then(r => r.json())
        .then(data => {
            btn.disabled = false;
            btn.classList.remove("syncing");
            carregarDados();
            carregarStatus();
        })
        .catch(() => {
            btn.disabled = false;
            btn.classList.remove("syncing");
        });
}

function carregarStatus() {
    fetch("/api/sync/status")
        .then(r => r.json())
        .then(data => {
            const badge = document.getElementById("sync-badge");
            if (data.last_sync_at) {
                const dt = new Date(data.last_sync_at);
                const time = dt.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
                badge.textContent = `Sync: ${time} (${data.last_sync_rows} linhas)`;
                badge.className = data.last_sync_status === "sucesso"
                    ? "sync-badge sync-badge-ok" : "sync-badge sync-badge-err";
            } else {
                badge.textContent = "Sem sync";
                badge.className = "sync-badge";
            }
        })
        .catch(() => {});
}

/* ========================
   FILTER OPTIONS (populated from data)
   ======================== */

const seenGsRh = new Set();
const seenTipo = new Set();

function atualizarFiltrosUnicos(rows) {
    if (!rows) return;

    let gsChanged = false;
    let tipoChanged = false;

    rows.forEach(r => {
        if (r.gs_rh && !seenGsRh.has(r.gs_rh)) {
            seenGsRh.add(r.gs_rh);
            gsChanged = true;
        }
        if (r.tipo_hemocomponente && !seenTipo.has(r.tipo_hemocomponente)) {
            seenTipo.add(r.tipo_hemocomponente);
            tipoChanged = true;
        }
    });

    if (gsChanged) {
        const sel = document.getElementById("filter-gs-rh");
        const current = sel.value;
        sel.innerHTML = '<option value="">GS/RH (Todos)</option>';
        [...seenGsRh].sort().forEach(v => {
            sel.innerHTML += `<option value="${esc(v)}">${esc(v)}</option>`;
        });
        sel.value = current;
    }

    if (tipoChanged) {
        const sel = document.getElementById("filter-tipo");
        const current = sel.value;
        sel.innerHTML = '<option value="">Hemocomponente (Todos)</option>';
        [...seenTipo].sort().forEach(v => {
            sel.innerHTML += `<option value="${esc(v)}">${esc(v)}</option>`;
        });
        sel.value = current;
    }
}

/* ========================
   CSV EXPORT
   ======================== */

function exportarCSV() {
    const params = new URLSearchParams({
        page: 1,
        per_page: 99999,
        search: state.search,
        sort_by: state.sort_by,
        sort_dir: state.sort_dir,
    });
    for (const [k, v] of Object.entries(state.filters)) {
        if (v) params.set(k, v);
    }

    fetch("/api/consulta?" + params.toString())
        .then(r => r.json())
        .then(data => {
            if (!data.rows || data.rows.length === 0) return;

            const cols = [
                "status_vencimento", "data_entrada", "data_validade",
                "dias_antes_vencimento", "data_transfusao", "destino",
                "nome_paciente", "tipo_hemocomponente", "gs_rh",
                "volume", "responsavel_recepcao", "setor_transfusao",
                "num_bolsa", "prontuario_salus", "prontuario_mv",
                "sus_laudo", "reacao_transfusional", "bolsa_sbs"
            ];
            const headers = [
                "Status", "Entrada", "Validade", "Dias Venc.",
                "Transfusao", "Destino", "Paciente", "Hemocomponente",
                "GS/RH", "Volume", "Responsavel", "Setor",
                "Num Bolsa", "Pront. SALUS", "Pront. MV",
                "SUS/Laudo", "Reacao", "Bolsa SBS"
            ];

            let csv = headers.join(";") + "\n";
            data.rows.forEach(r => {
                csv += cols.map(c => {
                    let val = r[c] != null ? String(r[c]) : "";
                    if (val.includes(";") || val.includes('"') || val.includes("\n")) {
                        val = '"' + val.replace(/"/g, '""') + '"';
                    }
                    return val;
                }).join(";") + "\n";
            });

            const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "consulta_dados.csv";
            a.click();
            URL.revokeObjectURL(url);
        });
}

/* ========================
   INIT
   ======================== */

document.addEventListener("DOMContentLoaded", function () {
    // Detect edit permission from template
    const tableWrap = document.querySelector(".consulta-table-wrap");
    canEdit = tableWrap && tableWrap.dataset.canEdit === "true";

    // Read URL params for vencimento filter (from dashboard links)
    const urlParams = new URLSearchParams(window.location.search);
    const vencimento = urlParams.get("vencimento");
    const diasMax = urlParams.get("dias_max");
    const emEstoque = urlParams.get("em_estoque");
    if (vencimento && diasMax) {
        if (vencimento === "vencidas") {
            state.filters.vencidas = "1";
        } else {
            state.filters.dias_vencimento_max = diasMax;
        }
        if (emEstoque) {
            state.filters.em_estoque = "1";
        }
        state.sort_by = "dias_antes_vencimento";
        state.sort_dir = "asc";
        showVencimentoFilter(vencimento, diasMax);
    }

    // Search with debounce
    document.getElementById("search-input").addEventListener("input", function () {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => buscar(this.value.trim()), 300);
    });

    // Filter dropdowns
    document.getElementById("filter-gs-rh").addEventListener("change", function () {
        aplicarFiltro("gs_rh", this.value);
    });
    document.getElementById("filter-tipo").addEventListener("change", function () {
        aplicarFiltro("tipo_hemocomponente", this.value);
    });

    // Per-page selector
    document.getElementById("per-page-select").addEventListener("change", function () {
        state.per_page = parseInt(this.value);
        state.page = 1;
        carregarDados();
    });

    // Sortable column headers
    document.querySelectorAll(".consulta-table th.sortable").forEach(th => {
        th.addEventListener("click", () => ordenar(th.dataset.col));
    });

    // Initial load
    carregarDados();
    carregarStatus();
});

function showVencimentoFilter(tipo, dias) {
    // Show a filter badge above the table to indicate active vencimento filter
    const existing = document.getElementById("vencimento-filter-badge");
    if (existing) existing.remove();

    const filtersArea = document.querySelector(".consulta-filters");
    const badge = document.createElement("div");
    badge.id = "vencimento-filter-badge";
    badge.className = "vencimento-badge vencimento-badge-" + tipo;

    let label;
    if (tipo === "vencidas") {
        label = "Bolsas ja vencidas";
    } else if (tipo === "urgente") {
        label = "Vencimento em ate " + dias + " dias (urgente)";
    } else {
        label = "Vencimento em ate " + dias + " dias (atencao)";
    }

    badge.innerHTML =
        '<span>' + label + '</span>' +
        '<button type="button" class="vencimento-badge-close" onclick="limparVencimento()" title="Remover filtro">&times;</button>';

    filtersArea.parentNode.insertBefore(badge, filtersArea.nextSibling);
}

function limparVencimento() {
    delete state.filters.dias_vencimento_max;
    delete state.filters.vencidas;
    delete state.filters.em_estoque;
    state.page = 1;
    const badge = document.getElementById("vencimento-filter-badge");
    if (badge) badge.remove();
    if (window.history.replaceState) {
        window.history.replaceState({}, "", "/consulta");
    }
    carregarDados();
}
