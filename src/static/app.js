document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const screens = {
    upload: document.getElementById("screen-upload"),
    processing: document.getElementById("screen-processing"),
    results: document.getElementById("screen-results"),
    success: document.getElementById("screen-success"),
  };

  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const btnSelect = document.getElementById("btn-select");
  const fileList = document.getElementById("file-list");
  const fileCounter = document.getElementById("file-counter");
  const fileCountText = document.getElementById("file-count-text");
  const btnProcess = document.getElementById("btn-process");
  const processingStep = document.getElementById("processing-step");
  const resultsSummary = document.getElementById("results-summary");
  const resultsBody = document.getElementById("results-body");
  const btnCancel = document.getElementById("btn-cancel");
  const btnSend = document.getElementById("btn-send");
  const successMessage = document.getElementById("success-message");
  const btnNew = document.getElementById("btn-new");
  const errorBar = document.getElementById("error-bar");
  const errorMessage = document.getElementById("error-message");
  const btnErrorClose = document.getElementById("btn-error-close");

  // Phase 2 elements
  const selectAll = document.getElementById("select-all");
  const badgeFiles = document.getElementById("badge-files");
  const badgeComprovantes = document.getElementById("badge-comprovantes");
  const badgeBolsas = document.getElementById("badge-bolsas");
  const badgeDuplicatas = document.getElementById("badge-duplicatas");
  const badgeErros = document.getElementById("badge-erros");
  const badgeWarnings = document.getElementById("badge-warnings");
  const previewBlocker = document.getElementById("preview-blocker");
  const blockerMsg = document.getElementById("blocker-msg");
  const inlineEditor = document.getElementById("inline-editor");
  const editBolsaNum = document.getElementById("edit-bolsa-num");
  const editTipo = document.getElementById("edit-tipo");
  const editGsRh = document.getElementById("edit-gs-rh");
  const editVolume = document.getElementById("edit-volume");
  const editCancel = document.getElementById("edit-cancel");
  const editSave = document.getElementById("edit-save");

  // Phase 3 elements
  const batchSummary = document.getElementById("batch-summary");

  // Offline fallback elements
  const offlineBanner = document.getElementById("offline-banner");

  let selectedFiles = []; // Phase 3: array of files
  let extractedData = null;
  let batchFilesInfo = []; // Info about batch files for history
  let editingIndex = -1;
  let sheetsOnline = true; // Track if Sheets was online during preview

  // Screen management
  function showScreen(name) {
    Object.values(screens).forEach((s) => s.classList.remove("active"));
    screens[name].classList.add("active");
  }

  function showError(msg) {
    errorMessage.textContent = msg;
    errorBar.classList.remove("hidden");
    setTimeout(() => errorBar.classList.add("hidden"), 8000);
  }

  function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  // File selection (Phase 3: multiple)
  function handleFiles(newFiles) {
    for (const file of newFiles) {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        showError("'" + file.name + "' nao e PDF. Apenas arquivos PDF sao aceitos.");
        continue;
      }
      if (file.size > 10 * 1024 * 1024) {
        showError("'" + file.name + "' e muito grande (max 10 MB).");
        continue;
      }
      // Check duplicate filename
      if (selectedFiles.some((f) => f.name === file.name)) {
        showError("'" + file.name + "' ja esta na lista.");
        continue;
      }
      if (selectedFiles.length >= 10) {
        showError("Maximo 10 arquivos por lote.");
        break;
      }
      selectedFiles.push(file);
    }
    renderFileList();
  }

  function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderFileList();
  }

  function renderFileList() {
    if (selectedFiles.length === 0) {
      fileList.classList.add("hidden");
      fileCounter.classList.add("hidden");
      btnProcess.classList.add("hidden");
      return;
    }

    fileList.classList.remove("hidden");
    fileCounter.classList.remove("hidden");
    btnProcess.classList.remove("hidden");

    fileCountText.textContent = selectedFiles.length + " arquivo(s) selecionado(s)";
    btnProcess.textContent =
      selectedFiles.length === 1 ? "Processar PDF" : "Processar Todos (" + selectedFiles.length + ")";

    fileList.innerHTML = "";
    selectedFiles.forEach((file, i) => {
      const div = document.createElement("div");
      div.className = "file-item";
      div.innerHTML =
        '<span class="file-item-name">' +
        escapeHtml(file.name) +
        '</span><span class="file-item-size">' +
        formatFileSize(file.size) +
        '</span><button type="button" class="btn-icon file-remove" data-index="' +
        i +
        '" title="Remover">&times;</button>';
      fileList.appendChild(div);
    });

    // Add click handlers for remove buttons
    fileList.querySelectorAll(".file-remove").forEach((btn) => {
      btn.addEventListener("click", () => {
        removeFile(parseInt(btn.dataset.index));
      });
    });
  }

  function clearFiles() {
    selectedFiles = [];
    fileInput.value = "";
    renderFileList();
  }

  // Drag and drop
  dropZone.addEventListener("click", () => fileInput.click());
  btnSelect.addEventListener("click", (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) handleFiles(fileInput.files);
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files);
  });

  // Process PDFs (Phase 3: batch)
  btnProcess.addEventListener("click", async () => {
    if (selectedFiles.length === 0) return;

    showScreen("processing");

    if (selectedFiles.length === 1) {
      // Single file: use original endpoint for backward compatibility
      processingStep.textContent = "Lendo PDF...";
      const formData = new FormData();
      formData.append("file", selectedFiles[0]);

      try {
        processingStep.textContent = "Extraindo e validando dados...";
        const response = await fetch("/api/upload", {
          method: "POST",
          body: formData,
        });
        const data = await response.json();
        if (!response.ok) {
          showError(data.error || "Erro ao processar PDF.");
          showScreen("upload");
          return;
        }
        // Wrap single file response to match batch format
        data.summary = data.resumo;
        data.summary.total_files = 1;
        data.summary.success_files = 1;
        data.summary.error_files = 0;
        data.files = [{ filename: selectedFiles[0].name, status: "done" }];
        extractedData = data;
        sheetsOnline = data.sheets_online !== false;
        batchFilesInfo = [{ filename: selectedFiles[0].name, comprovante_nums: "" }];
        renderPreview(data);
        showScreen("results");
      } catch (err) {
        showError("Erro de conexao. Tente novamente.");
        showScreen("upload");
      }
    } else {
      // Batch: use batch endpoint
      processingStep.textContent =
        "Processando " + selectedFiles.length + " arquivos...";
      const formData = new FormData();
      selectedFiles.forEach((f) => formData.append("files", f));

      try {
        const response = await fetch("/api/batch/upload", {
          method: "POST",
          body: formData,
        });
        const data = await response.json();
        if (!response.ok) {
          showError(data.error || "Erro no processamento em lote.");
          showScreen("upload");
          return;
        }
        extractedData = data;
        extractedData.resumo = data.summary;
        sheetsOnline = data.sheets_online !== false;
        batchFilesInfo = (data.files || [])
          .filter((f) => f.status === "done")
          .map((f) => ({
            filename: f.filename,
            comprovante_nums: f.comprovante_nums || "",
          }));
        renderPreview(data);
        showScreen("results");
      } catch (err) {
        showError("Erro de conexao. Tente novamente.");
        showScreen("upload");
      }
    }
  });

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
  }

  // Render preview table (Phase 2 + 3)
  function renderPreview(data) {
    const summary = data.summary || data.resumo;

    // Offline banner
    if (offlineBanner) {
      if (!sheetsOnline) {
        offlineBanner.classList.remove("hidden");
      } else {
        offlineBanner.classList.add("hidden");
      }
    }

    // Badge: files (Phase 3)
    if (summary.total_files && summary.total_files > 1) {
      badgeFiles.textContent = summary.success_files + "/" + summary.total_files + " arquivos";
      badgeFiles.classList.remove("hidden");
    } else {
      badgeFiles.classList.add("hidden");
    }

    // Badges
    const totalComprovantes = summary.total_comprovantes || summary.success_files || 0;
    const totalBolsas = summary.total_bolsas || 0;
    badgeComprovantes.textContent = totalComprovantes + " comprov.";
    badgeBolsas.textContent = totalBolsas + " bolsas";

    if (summary.total_duplicatas > 0) {
      badgeDuplicatas.textContent = summary.total_duplicatas + " duplicata(s)";
      badgeDuplicatas.classList.remove("hidden");
    } else {
      badgeDuplicatas.classList.add("hidden");
    }

    if (summary.total_erros_criticos > 0) {
      badgeErros.textContent = summary.total_erros_criticos + " erro(s)";
      badgeErros.classList.remove("hidden");
    } else {
      badgeErros.classList.add("hidden");
    }

    if (summary.total_warnings > 0) {
      badgeWarnings.textContent = summary.total_warnings + " aviso(s)";
      badgeWarnings.classList.remove("hidden");
    } else {
      badgeWarnings.classList.add("hidden");
    }

    // Batch file summary (Phase 3)
    if (data.files && data.files.length > 1) {
      batchSummary.classList.remove("hidden");
      batchSummary.innerHTML = "";
      data.files.forEach((f) => {
        const div = document.createElement("div");
        div.className = "batch-file-result " + (f.status === "done" ? "batch-ok" : "batch-err");
        if (f.status === "done") {
          div.innerHTML =
            '<span class="batch-icon">&#10003;</span> ' +
            escapeHtml(f.filename) +
            " — " + (f.comprovantes || 0) + " comprov., " + (f.bolsas || 0) + " bolsas";
        } else {
          div.innerHTML =
            '<span class="batch-icon">&#10007;</span> ' +
            escapeHtml(f.filename) +
            " — " + escapeHtml(f.error);
        }
        batchSummary.appendChild(div);
      });
    } else {
      batchSummary.classList.add("hidden");
    }

    // Populate dropdowns with base values
    if (data.base_values) {
      populateDropdown(editTipo, data.base_values.tipos_hemocomponente);
      populateDropdown(editGsRh, data.base_values.gs_rh);
    }

    // Render table
    resultsBody.innerHTML = "";
    data.linhas.forEach((linha, i) => {
      const tr = document.createElement("tr");
      tr.dataset.index = i;

      const hasError = linha.erros.some((e) => e.nivel === "error");
      const hasWarning = linha.erros.some((e) => e.nivel === "warning");
      const isDup = !!linha.duplicata;

      if (hasError) tr.classList.add("row-error");
      else if (isDup) tr.classList.add("row-dup");
      else if (hasWarning) tr.classList.add("row-warning");

      // Status icon
      let statusIcon = '<span class="status-ok" title="OK">&#10003;</span>';
      if (hasError) {
        const errMsg = linha.erros
          .filter((e) => e.nivel === "error")
          .map((e) => e.mensagem)
          .join("; ");
        statusIcon =
          '<span class="status-error" title="' +
          escapeHtml(errMsg) +
          '">&#10007;</span>';
      } else if (isDup) {
        statusIcon =
          '<span class="status-dup" title="Duplicata: bolsa ja existe na planilha">D</span>';
      } else if (hasWarning) {
        const warnMsg = linha.erros
          .filter((e) => e.nivel === "warning")
          .map((e) => e.mensagem)
          .join("; ");
        statusIcon =
          '<span class="status-warn" title="' +
          escapeHtml(warnMsg) +
          '">!</span>';
      }

      tr.innerHTML =
        '<td class="col-check"><input type="checkbox" class="row-check" data-index="' +
        i +
        '"' +
        (linha.selecionada ? " checked" : "") +
        "></td>" +
        "<td>" + escapeHtml(linha.data_entrada) + "</td>" +
        "<td>" + escapeHtml(linha.data_validade) + "</td>" +
        "<td>" + escapeHtml(linha.tipo_hemocomponente) + "</td>" +
        "<td>" + escapeHtml(linha.gs_rh) + "</td>" +
        "<td>" + linha.volume + "</td>" +
        "<td>" + escapeHtml(linha.num_bolsa) + "</td>" +
        '<td class="col-status">' + statusIcon + "</td>";

      // Click to edit (not on checkbox)
      tr.addEventListener("click", (e) => {
        if (e.target.type === "checkbox") return;
        openEditor(i);
      });

      resultsBody.appendChild(tr);
    });

    updateSendButton();

    // Responsavel info in summary
    const responsaveis = [
      ...new Set(data.linhas.map((l) => l.responsavel).filter(Boolean)),
    ];
    if (responsaveis.length > 0) {
      resultsSummary.textContent = "Responsavel: " + responsaveis.join(", ");
    } else {
      resultsSummary.textContent = "";
    }
  }

  function populateDropdown(select, values) {
    select.innerHTML = '<option value="">-- Selecione --</option>';
    values.forEach((v) => {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      select.appendChild(opt);
    });
  }

  // Select all checkbox
  selectAll.addEventListener("change", () => {
    const checks = resultsBody.querySelectorAll(".row-check");
    checks.forEach((cb) => {
      const idx = parseInt(cb.dataset.index);
      extractedData.linhas[idx].selecionada = selectAll.checked;
      cb.checked = selectAll.checked;
    });
    updateSendButton();
  });

  // Individual checkbox
  resultsBody.addEventListener("change", (e) => {
    if (e.target.classList.contains("row-check")) {
      const idx = parseInt(e.target.dataset.index);
      extractedData.linhas[idx].selecionada = e.target.checked;
      updateSendButton();
    }
  });

  // Update send button state
  function updateSendButton() {
    if (!extractedData) return;

    const selected = extractedData.linhas.filter((l) => l.selecionada);
    const selectedWithErrors = selected.filter((l) =>
      l.erros.some((e) => e.nivel === "error")
    );

    if (selected.length === 0) {
      btnSend.disabled = true;
      btnSend.textContent = "Nenhuma bolsa selecionada";
      previewBlocker.classList.add("hidden");
    } else if (selectedWithErrors.length > 0) {
      btnSend.disabled = true;
      btnSend.textContent = "Confirmar e Enviar";
      previewBlocker.classList.remove("hidden");
      // Collect specific error details per row
      const errorDetails = selectedWithErrors.map((l) => {
        const criticalErrors = l.erros.filter((e) => e.nivel === "error");
        const details = criticalErrors
          .map((e) => {
            if (e.campo === "gs_rh") return "GS/RH nao compativel (" + escapeHtml(e.valor_atual) + ")";
            if (e.campo === "tipo_hemocomponente") return "Tipo hemocomponente nao compativel (" + escapeHtml(e.valor_atual) + ")";
            return escapeHtml(e.mensagem);
          })
          .join(", ");
        return "Bolsa " + escapeHtml(l.num_bolsa) + ": " + details;
      });
      blockerMsg.innerHTML =
        "Corrija " +
        selectedWithErrors.length +
        " erro(s) critico(s) para confirmar:<br>" +
        '<ul style="margin:4px 0 0 0;padding-left:20px;text-align:left">' +
        errorDetails.map((d) => "<li>" + d + "</li>").join("") +
        "</ul>";
    } else {
      btnSend.disabled = false;
      btnSend.textContent =
        "Confirmar e Enviar (" + selected.length + " bolsas)";
      previewBlocker.classList.add("hidden");
    }
  }

  // Inline editor
  function openEditor(index) {
    editingIndex = index;
    const linha = extractedData.linhas[index];
    editBolsaNum.textContent = linha.num_bolsa;
    editTipo.value = linha.tipo_hemocomponente;
    editGsRh.value = linha.gs_rh;
    editVolume.value = linha.volume;
    inlineEditor.classList.remove("hidden");
  }

  editCancel.addEventListener("click", () => {
    inlineEditor.classList.add("hidden");
    editingIndex = -1;
  });

  editSave.addEventListener("click", async () => {
    if (editingIndex < 0) return;

    const linha = extractedData.linhas[editingIndex];
    const newTipo = editTipo.value;
    const newGsRh = editGsRh.value;
    const newVolume = parseInt(editVolume.value) || 0;

    // Update data
    linha.tipo_hemocomponente = newTipo;
    linha.gs_rh = newGsRh;
    linha.volume = newVolume;

    // Revalidate via backend
    try {
      const newErros = [];

      const respTipo = await fetch("/api/validate-field", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ campo: "tipo_hemocomponente", valor: newTipo }),
      });
      const dataTipo = await respTipo.json();
      if (!dataTipo.valido) {
        newErros.push({
          campo: "tipo_hemocomponente",
          valor_atual: newTipo,
          mensagem: dataTipo.mensagem,
          nivel: "error",
          valores_validos: extractedData.base_values ? extractedData.base_values.tipos_hemocomponente : [],
        });
      }

      const respGs = await fetch("/api/validate-field", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ campo: "gs_rh", valor: newGsRh }),
      });
      const dataGs = await respGs.json();
      if (!dataGs.valido) {
        newErros.push({
          campo: "gs_rh",
          valor_atual: newGsRh,
          mensagem: dataGs.mensagem,
          nivel: "error",
          valores_validos: extractedData.base_values ? extractedData.base_values.gs_rh : [],
        });
      }

      if (newVolume <= 0) {
        newErros.push({
          campo: "volume",
          valor_atual: String(newVolume),
          mensagem: "Volume deve ser maior que zero",
          nivel: "warning",
          valores_validos: [],
        });
      }

      const respWarning = linha.erros.find(
        (e) => e.campo === "responsavel_recepcao"
      );
      if (respWarning) newErros.push(respWarning);

      linha.erros = newErros;
    } catch (err) {
      // On network error, keep existing errors
    }

    inlineEditor.classList.add("hidden");
    editingIndex = -1;
    renderPreview(extractedData);
  });

  // Cancel
  btnCancel.addEventListener("click", () => {
    extractedData = null;
    batchFilesInfo = [];
    clearFiles();
    inlineEditor.classList.add("hidden");
    editingIndex = -1;
    showScreen("upload");
  });

  // Send to Sheets (Phase 3: supports batch with history)
  btnSend.addEventListener("click", async () => {
    if (!extractedData) return;

    const selected = extractedData.linhas.filter((l) => l.selecionada);
    if (selected.length === 0) return;

    const withErrors = selected.filter((l) =>
      l.erros.some((e) => e.nivel === "error")
    );
    if (withErrors.length > 0) {
      const errorList = withErrors.map((l) => {
        const msgs = l.erros
          .filter((e) => e.nivel === "error")
          .map((e) => {
            if (e.campo === "gs_rh") return "GS/RH nao compativel";
            if (e.campo === "tipo_hemocomponente") return "Tipo hemocomponente nao compativel";
            return e.mensagem;
          })
          .join(", ");
        return "Bolsa " + l.num_bolsa + ": " + msgs;
      }).join(" | ");
      showError(
        "Corrija os erros criticos antes de enviar (" +
          withErrors.length +
          " bolsa(s) com erro). " + errorList
      );
      return;
    }

    btnSend.disabled = true;
    btnSend.textContent = "Enviando...";

    try {
      const linhasEnviar = selected.map((l) => ({
        data_entrada: l.data_entrada,
        data_validade: l.data_validade,
        tipo_hemocomponente: l.tipo_hemocomponente,
        gs_rh: l.gs_rh,
        volume: l.volume,
        responsavel: l.responsavel,
        num_bolsa: l.num_bolsa,
      }));

      // Use batch/enviar for batch mode (with history recording)
      const endpoint =
        batchFilesInfo.length > 0 ? "/api/batch/enviar" : "/api/enviar";
      const payload = { linhas: linhasEnviar };
      if (batchFilesInfo.length > 0) {
        payload.files_info = batchFilesInfo;
      }

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        showError(data.error || "Erro ao enviar para planilha.");
        btnSend.disabled = false;
        updateSendButton();
        return;
      }

      const summary = extractedData.summary || extractedData.resumo;
      const totalFiles = summary.total_files || 1;
      let successMsg;
      if (data.destino === "banco_local") {
        successMsg =
          data.linhas_inseridas +
          " bolsa(s) salva(s) localmente. " +
          "Serao sincronizadas com a planilha quando a conexao for restabelecida.";
      } else if (totalFiles > 1) {
        successMsg =
          totalFiles +
          " arquivos processados, " +
          data.linhas_inseridas +
          " bolsa(s) importada(s).";
      } else {
        successMsg = data.mensagem;
      }
      successMessage.textContent = successMsg;
      showScreen("success");
    } catch (err) {
      showError("Erro de conexao. Tente novamente.");
      btnSend.disabled = false;
      updateSendButton();
    }
  });

  // New import
  btnNew.addEventListener("click", () => {
    extractedData = null;
    batchFilesInfo = [];
    sheetsOnline = true;
    clearFiles();
    btnSend.disabled = false;
    btnSend.textContent = "Confirmar e Enviar";
    inlineEditor.classList.add("hidden");
    editingIndex = -1;
    batchSummary.classList.add("hidden");
    if (offlineBanner) offlineBanner.classList.add("hidden");
    showScreen("upload");
  });

  // Error close
  btnErrorClose.addEventListener("click", () => {
    errorBar.classList.add("hidden");
  });
});
