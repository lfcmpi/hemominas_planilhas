document.addEventListener("DOMContentLoaded", () => {
  // DOM references
  const fields = {
    google_sheets_id: document.getElementById("cfg-google-sheets-id"),
    sheet_tab_name: document.getElementById("cfg-sheet-tab-name"),
    sheet_header_row: document.getElementById("cfg-sheet-header-row"),
    base_tab_name: document.getElementById("cfg-base-tab-name"),
    base_gs_rh_range: document.getElementById("cfg-base-gs-rh-range"),
    base_tipos_range: document.getElementById("cfg-base-tipos-range"),
    base_responsaveis_range: document.getElementById("cfg-base-responsaveis-range"),
    base_destinos_range: document.getElementById("cfg-base-destinos-range"),
    base_reacao_range: document.getElementById("cfg-base-reacao-range"),
    smtp_enabled: document.getElementById("cfg-smtp-enabled"),
    smtp_host: document.getElementById("cfg-smtp-host"),
    smtp_port: document.getElementById("cfg-smtp-port"),
    smtp_user: document.getElementById("cfg-smtp-user"),
    smtp_password: document.getElementById("cfg-smtp-password"),
    smtp_from: document.getElementById("cfg-smtp-from"),
    alert_email_to: document.getElementById("cfg-alert-email-to"),
    scheduler_enabled: document.getElementById("cfg-scheduler-enabled"),
    scheduler_alert_hour: document.getElementById("cfg-scheduler-alert-hour"),
    scheduler_alert_minute: document.getElementById("cfg-scheduler-alert-minute"),
    sync_interval_minutes: document.getElementById("cfg-sync-interval-minutes"),
    cache_ttl_seconds: document.getElementById("cfg-cache-ttl-seconds"),
    session_lifetime_minutes: document.getElementById("cfg-session-lifetime-minutes"),
    max_batch_files: document.getElementById("cfg-max-batch-files"),
    max_upload_size_mb: document.getElementById("cfg-max-upload-size-mb"),
  };

  const credentialsFile = document.getElementById("cfg-credentials-file");
  const credentialsBadge = document.getElementById("cfg-credentials-badge");
  const btnUploadCreds = document.getElementById("btn-upload-credentials");
  const btnTestarSheets = document.getElementById("btn-testar-sheets");
  const btnTestarSmtp = document.getElementById("btn-testar-smtp");
  const btnSave = document.getElementById("btn-save-config");
  const feedback = document.getElementById("config-feedback");
  const sheetsResult = document.getElementById("sheets-result");

  const checkboxFields = ["smtp_enabled", "scheduler_enabled"];
  const numberFields = [
    "sheet_header_row", "smtp_port", "scheduler_alert_hour",
    "scheduler_alert_minute", "sync_interval_minutes",
    "cache_ttl_seconds", "session_lifetime_minutes",
    "max_batch_files", "max_upload_size_mb",
  ];

  // Load config
  async function loadConfig() {
    try {
      const resp = await fetch("/api/configuracoes");
      const data = await resp.json();

      for (const [key, el] of Object.entries(fields)) {
        if (!el) continue;
        if (checkboxFields.includes(key)) {
          el.checked = !!data[key];
        } else if (numberFields.includes(key)) {
          el.value = data[key] || 0;
        } else {
          el.value = data[key] || "";
        }
      }

      // Credentials badge
      if (data.credentials_file_exists) {
        credentialsBadge.textContent = "Arquivo encontrado";
        credentialsBadge.className = "badge badge-info";
        credentialsBadge.style.display = "";
      } else {
        credentialsBadge.textContent = "Nao encontrado";
        credentialsBadge.className = "badge badge-err";
        credentialsBadge.style.display = "";
      }
    } catch (err) {
      showFeedback("Erro ao carregar configuracoes.", "err");
    }
  }

  // Save config
  async function saveConfig() {
    const payload = {};
    for (const [key, el] of Object.entries(fields)) {
      if (!el) continue;
      if (checkboxFields.includes(key)) {
        payload[key] = el.checked;
      } else if (numberFields.includes(key)) {
        payload[key] = parseInt(el.value) || 0;
      } else {
        payload[key] = el.value;
      }
    }

    try {
      btnSave.disabled = true;
      btnSave.textContent = "Salvando...";
      const resp = await fetch("/api/configuracoes", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (resp.ok) {
        showFeedback("Configuracoes salvas com sucesso.", "ok");
      } else {
        const data = await resp.json();
        showFeedback(data.error || "Erro ao salvar.", "err");
      }
    } catch (err) {
      showFeedback("Erro de conexao.", "err");
    } finally {
      btnSave.disabled = false;
      btnSave.textContent = "Salvar";
    }
  }

  // Test Sheets connection
  async function testarSheets() {
    btnTestarSheets.disabled = true;
    btnTestarSheets.textContent = "Testando...";
    sheetsResult.classList.remove("hidden");
    sheetsResult.className = "settings-connection-result";
    sheetsResult.textContent = "Conectando...";

    try {
      const resp = await fetch("/api/configuracoes/testar-sheets", { method: "POST" });
      const data = await resp.json();
      if (resp.ok) {
        sheetsResult.className = "settings-connection-result settings-connection-ok";
        sheetsResult.innerHTML =
          "<strong>Conexao OK</strong><br>" +
          "Titulo: " + data.titulo + "<br>" +
          "Aba: " + data.aba + "<br>" +
          "Total linhas: " + data.total_linhas;
      } else {
        sheetsResult.className = "settings-connection-result settings-connection-err";
        sheetsResult.textContent = data.error || "Erro ao conectar.";
      }
    } catch (err) {
      sheetsResult.className = "settings-connection-result settings-connection-err";
      sheetsResult.textContent = "Erro de conexao.";
    } finally {
      btnTestarSheets.disabled = false;
      btnTestarSheets.textContent = "Testar Conexao";
    }
  }

  // Test SMTP
  async function testarEmail() {
    btnTestarSmtp.disabled = true;
    btnTestarSmtp.textContent = "Enviando...";
    try {
      const resp = await fetch("/api/configuracoes/testar-smtp", { method: "POST" });
      if (resp.ok) {
        showFeedback("Email de teste enviado com sucesso.", "ok");
      } else {
        const data = await resp.json();
        showFeedback(data.error || "Erro ao enviar email.", "err");
      }
    } catch (err) {
      showFeedback("Erro de conexao.", "err");
    } finally {
      btnTestarSmtp.disabled = false;
      btnTestarSmtp.textContent = "Testar Email";
    }
  }

  // Upload credentials
  async function uploadCredentials() {
    const file = credentialsFile.files[0];
    if (!file) {
      showFeedback("Selecione um arquivo JSON.", "err");
      return;
    }

    btnUploadCreds.disabled = true;
    btnUploadCreds.textContent = "Enviando...";

    const formData = new FormData();
    formData.append("file", file);

    try {
      const resp = await fetch("/api/configuracoes/upload-credentials", {
        method: "POST",
        body: formData,
      });
      const data = await resp.json();
      if (resp.ok) {
        showFeedback(data.mensagem, "ok");
        credentialsBadge.textContent = "Arquivo encontrado";
        credentialsBadge.className = "badge badge-info";
        credentialsBadge.style.display = "";
        credentialsFile.value = "";
      } else {
        showFeedback(data.error || "Erro ao enviar.", "err");
      }
    } catch (err) {
      showFeedback("Erro de conexao.", "err");
    } finally {
      btnUploadCreds.disabled = false;
      btnUploadCreds.textContent = "Upload Credenciais";
    }
  }

  // Feedback auto-hide 5s
  function showFeedback(msg, type) {
    feedback.textContent = msg;
    feedback.className = "settings-feedback settings-feedback-" + type;
    feedback.classList.remove("hidden");
    setTimeout(() => feedback.classList.add("hidden"), 5000);
  }

  // Event listeners
  btnSave.addEventListener("click", saveConfig);
  btnTestarSheets.addEventListener("click", testarSheets);
  btnTestarSmtp.addEventListener("click", testarEmail);
  btnUploadCreds.addEventListener("click", uploadCredentials);

  // Init
  loadConfig();
});
