/* Gerenciamento de Usuarios - client-side logic */

let editingUserId = null;

function carregarUsuarios() {
    fetch("/api/usuarios")
        .then(r => r.json())
        .then(data => renderUsuarios(data.usuarios))
        .catch(() => {
            document.getElementById("users-tbody").innerHTML =
                '<tr><td colspan="5" style="text-align:center;color:#c00;padding:1rem">Erro ao carregar usuarios.</td></tr>';
        });
}

function renderUsuarios(users) {
    const tbody = document.getElementById("users-tbody");
    if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:1rem;color:#999">Nenhum usuario cadastrado.</td></tr>';
        return;
    }

    tbody.innerHTML = users.map(u => {
        const roleBadge = `<span class="sidebar-role-badge" style="background:${getRoleColor(u.role)};color:#fff">${esc(u.role)}</span>`;
        return `<tr>
            <td>${u.id}</td>
            <td>${esc(u.name)}</td>
            <td>${esc(u.email)}</td>
            <td>${roleBadge}</td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="editarUsuario(${u.id}, '${esc(u.name)}', '${esc(u.email)}', '${esc(u.role)}')">Editar</button>
                <button class="btn btn-secondary btn-sm" style="color:#c00" onclick="excluirUsuario(${u.id}, '${esc(u.name)}')">Excluir</button>
            </td>
        </tr>`;
    }).join("");
}

function getRoleColor(role) {
    switch (role) {
        case "admin": return "#a70202";
        case "manager": return "#1d4ed8";
        case "uploader": return "#059669";
        case "consulta": return "#7c3aed";
        default: return "#666";
    }
}

function esc(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}

function salvarUsuario() {
    const name = document.getElementById("user-name").value.trim();
    const email = document.getElementById("user-email").value.trim();
    const password = document.getElementById("user-password").value;
    const role = document.getElementById("user-role").value;

    if (!name || !email) {
        showFeedback("Nome e email sao obrigatorios.", true);
        return;
    }

    if (editingUserId) {
        // Update existing user
        const body = { name, role };
        if (password) body.password = password;

        fetch(`/api/usuarios/${editingUserId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        })
            .then(r => r.json().then(d => ({ ok: r.ok, data: d })))
            .then(({ ok, data }) => {
                if (!ok) throw new Error(data.error || "Erro");
                showFeedback("Usuario atualizado com sucesso.", false);
                cancelarEdicao();
                carregarUsuarios();
            })
            .catch(err => showFeedback(err.message, true));
    } else {
        // Create new user
        if (!password || password.length < 6) {
            showFeedback("Senha deve ter pelo menos 6 caracteres.", true);
            return;
        }

        fetch("/api/usuarios", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email, password, role }),
        })
            .then(r => r.json().then(d => ({ ok: r.ok, data: d })))
            .then(({ ok, data }) => {
                if (!ok) throw new Error(data.error || "Erro");
                showFeedback("Usuario criado com sucesso.", false);
                limparFormulario();
                carregarUsuarios();
            })
            .catch(err => showFeedback(err.message, true));
    }
}

function editarUsuario(id, name, email, role) {
    editingUserId = id;
    document.getElementById("form-title").textContent = "Editar Usuario";
    document.getElementById("edit-user-id").value = id;
    document.getElementById("user-name").value = name;
    document.getElementById("user-email").value = email;
    document.getElementById("user-email").disabled = true;
    document.getElementById("user-password").value = "";
    document.getElementById("user-password").placeholder = "Deixe vazio para manter";
    document.getElementById("user-role").value = role;
    document.getElementById("btn-cancel-edit").style.display = "";
    document.getElementById("btn-save-user").textContent = "Atualizar";

    // Scroll to form
    document.getElementById("form-title").scrollIntoView({ behavior: "smooth" });
}

function cancelarEdicao() {
    editingUserId = null;
    document.getElementById("form-title").textContent = "Novo Usuario";
    document.getElementById("edit-user-id").value = "";
    document.getElementById("user-email").disabled = false;
    document.getElementById("user-password").placeholder = "Minimo 6 caracteres";
    document.getElementById("btn-cancel-edit").style.display = "none";
    document.getElementById("btn-save-user").textContent = "Salvar";
    limparFormulario();
}

function limparFormulario() {
    document.getElementById("user-name").value = "";
    document.getElementById("user-email").value = "";
    document.getElementById("user-password").value = "";
    document.getElementById("user-role").value = "consulta";
}

function excluirUsuario(id, name) {
    if (!confirm(`Tem certeza que deseja excluir o usuario "${name}"?`)) return;

    fetch(`/api/usuarios/${id}`, { method: "DELETE" })
        .then(r => r.json().then(d => ({ ok: r.ok, data: d })))
        .then(({ ok, data }) => {
            if (!ok) throw new Error(data.error || "Erro");
            showFeedback("Usuario excluido.", false);
            carregarUsuarios();
        })
        .catch(err => showFeedback(err.message, true));
}

function showFeedback(msg, isError) {
    const el = document.getElementById("user-feedback");
    el.textContent = msg;
    el.className = "settings-feedback" + (isError ? " error" : " success");
    el.classList.remove("hidden");
    setTimeout(() => el.classList.add("hidden"), 4000);
}

document.addEventListener("DOMContentLoaded", function () {
    carregarUsuarios();
});
