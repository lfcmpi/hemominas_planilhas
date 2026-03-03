document.addEventListener("DOMContentLoaded", () => {
  const thresholdUrgente = document.getElementById("threshold-urgente");
  const thresholdAtencao = document.getElementById("threshold-atencao");
  const inappEnabled = document.getElementById("inapp-enabled");
  const emailEnabled = document.getElementById("email-enabled");
  const emailTo = document.getElementById("email-to");
  const btnTestEmail = document.getElementById("btn-test-email");
  const btnSave = document.getElementById("btn-save");
  const feedback = document.getElementById("feedback");

  // Load current config
  async function loadConfig() {
    try {
      const resp = await fetch("/api/alertas/config");
      const data = await resp.json();

      thresholdUrgente.value = data.threshold_urgente;
      thresholdAtencao.value = data.threshold_atencao;
      inappEnabled.checked = data.inapp_enabled;
      emailEnabled.checked = data.email_enabled;
      emailTo.value = data.email_to || "";
    } catch (err) {
      showFeedback("Erro ao carregar configuracao.", "err");
    }
  }

  // Enable/disable test email button
  emailEnabled.addEventListener("change", () => {
    btnTestEmail.disabled = !emailEnabled.checked;
  });

  // Save config
  btnSave.addEventListener("click", async () => {
    const urgente = parseInt(thresholdUrgente.value);
    const atencao = parseInt(thresholdAtencao.value);

    if (urgente >= atencao) {
      showFeedback("Threshold urgente deve ser menor que atencao.", "err");
      return;
    }

    try {
      const resp = await fetch("/api/alertas/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          threshold_urgente: urgente,
          threshold_atencao: atencao,
          email_enabled: emailEnabled.checked,
          email_to: emailTo.value || null,
          inapp_enabled: inappEnabled.checked,
        }),
      });

      if (resp.ok) {
        showFeedback("Configuracao salva com sucesso.", "ok");
      } else {
        const data = await resp.json();
        showFeedback(data.error || "Erro ao salvar.", "err");
      }
    } catch (err) {
      showFeedback("Erro de conexao.", "err");
    }
  });

  // Test email
  btnTestEmail.addEventListener("click", async () => {
    btnTestEmail.disabled = true;
    btnTestEmail.textContent = "Enviando...";
    try {
      const resp = await fetch("/api/alertas/testar-email", { method: "POST" });
      if (resp.ok) {
        showFeedback("Email de teste enviado.", "ok");
      } else {
        const data = await resp.json();
        showFeedback(data.error || "Erro ao enviar email de teste.", "err");
      }
    } catch (err) {
      showFeedback("Erro de conexao.", "err");
    } finally {
      btnTestEmail.disabled = false;
      btnTestEmail.textContent = "Testar Email";
    }
  });

  function showFeedback(msg, type) {
    feedback.textContent = msg;
    feedback.className = "settings-feedback settings-feedback-" + type;
    feedback.classList.remove("hidden");
    setTimeout(() => feedback.classList.add("hidden"), 5000);
  }

  loadConfig();
});
