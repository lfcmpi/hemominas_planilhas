document.addEventListener("DOMContentLoaded", () => {
  const historyBody = document.getElementById("history-body");
  const paginationInfo = document.getElementById("pagination-info");
  const btnPrev = document.getElementById("btn-prev");
  const btnNext = document.getElementById("btn-next");
  const filterInicio = document.getElementById("filter-inicio");
  const filterFim = document.getElementById("filter-fim");
  const btnFilter = document.getElementById("btn-filter");
  const btnClearFilter = document.getElementById("btn-clear-filter");

  let currentPage = 1;
  const perPage = 20;

  async function loadHistory() {
    let url = "/api/historico?page=" + currentPage + "&per_page=" + perPage;

    if (filterInicio.value) {
      url += "&data_inicio=" + filterInicio.value;
    }
    if (filterFim.value) {
      url += "&data_fim=" + filterFim.value;
    }

    try {
      const resp = await fetch(url);
      const data = await resp.json();

      historyBody.innerHTML = "";

      if (data.importacoes.length === 0) {
        historyBody.innerHTML =
          '<tr><td colspan="5" style="text-align:center;color:#999;padding:2rem">Nenhuma importacao encontrada.</td></tr>';
      }

      data.importacoes.forEach((imp) => {
        const tr = document.createElement("tr");
        tr.style.cursor = "pointer";

        const ts = imp.timestamp
          ? new Date(imp.timestamp).toLocaleString("pt-BR")
          : "-";

        const statusClass =
          imp.status === "sucesso"
            ? "status-ok"
            : imp.status === "parcial"
            ? "status-warn"
            : "status-error";
        const statusIcon =
          imp.status === "sucesso"
            ? "&#10003;"
            : imp.status === "parcial"
            ? "!"
            : "&#10007;";

        tr.innerHTML =
          "<td>" + ts + "</td>" +
          "<td>" + (imp.filename || "-") + "</td>" +
          "<td>" + (imp.comprovante_nums || "-") + "</td>" +
          "<td>" + imp.bolsa_count + "</td>" +
          '<td class="col-status"><span class="' + statusClass + '">' + statusIcon + "</span></td>";

        tr.addEventListener("click", () => {
          window.location.href = "/historico/" + imp.id;
        });

        historyBody.appendChild(tr);
      });

      // Pagination
      const totalPages = Math.ceil(data.total / perPage);
      paginationInfo.textContent =
        "Mostrando " +
        data.importacoes.length +
        " de " +
        data.total +
        " importacoes (pagina " +
        currentPage +
        " de " +
        Math.max(totalPages, 1) +
        ")";

      btnPrev.disabled = currentPage <= 1;
      btnNext.disabled = currentPage >= totalPages;
    } catch (err) {
      historyBody.innerHTML =
        '<tr><td colspan="5" style="text-align:center;color:#991b1b;padding:2rem">Erro ao carregar historico.</td></tr>';
    }
  }

  btnFilter.addEventListener("click", () => {
    currentPage = 1;
    loadHistory();
  });

  btnClearFilter.addEventListener("click", () => {
    filterInicio.value = "";
    filterFim.value = "";
    currentPage = 1;
    loadHistory();
  });

  btnPrev.addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      loadHistory();
    }
  });

  btnNext.addEventListener("click", () => {
    currentPage++;
    loadHistory();
  });

  loadHistory();
});
