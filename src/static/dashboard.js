document.addEventListener("DOMContentLoaded", () => {
  const btnRefresh = document.getElementById("btn-refresh");

  async function loadDashboard(forceRefresh) {
    const url = "/api/dashboard" + (forceRefresh ? "?force_refresh=true" : "");
    setKpiLoading();

    try {
      const resp = await fetch(url);
      if (!resp.ok) {
        showWarning("Erro ao carregar dados do dashboard.");
        return;
      }
      const data = await resp.json();
      render(data);
    } catch (err) {
      showWarning("Erro de conexao com o servidor.");
    }
  }

  function setKpiLoading() {
    ["kpi-estoque", "kpi-entradas-7d", "kpi-entradas-30d", "kpi-alertas"].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = "...";
    });
  }

  function showWarning(msg) {
    const w = document.getElementById("sheets-warning");
    const m = document.getElementById("sheets-warning-msg");
    if (w && m) {
      m.textContent = msg;
      w.classList.remove("hidden");
    }
  }

  function render(data) {
    const hist = data.historico || {};
    const stats = hist.stats || {};
    const estoque = data.estoque || null;

    // Connection warning
    if (data.estoque_erro) {
      showWarning(data.estoque_erro);
    } else {
      document.getElementById("sheets-warning").classList.add("hidden");
    }

    // Store thresholds for links
    const thresholdUrgente = data.threshold_urgente || 7;
    const thresholdAtencao = data.threshold_atencao || 14;

    // === KPI Cards ===
    if (estoque) {
      setText("kpi-estoque", estoque.total_em_estoque);
      setText("kpi-estoque-sub", "Tempo real (planilha)");
      const vencidasCount = estoque.vencendo.vencidas ? (estoque.vencendo.vencidas.count || 0) : 0;
      const alertCount = vencidasCount + (estoque.vencendo.urgente.count || 0) + (estoque.vencendo.atencao.count || 0);
      setText("kpi-alertas", alertCount);
      const kpiAlertasCard = document.getElementById("kpi-alertas").closest(".kpi-card");
      if (alertCount > 0) {
        kpiAlertasCard.classList.add("kpi-danger");
        kpiAlertasCard.style.cursor = "pointer";
        kpiAlertasCard.title = "Ver bolsas com vencimento proximo";
        kpiAlertasCard.onclick = () => {
          window.location.href = "/consulta?vencimento=atencao&dias_max=" + thresholdAtencao + "&em_estoque=1";
        };
      }
      const subParts = [];
      if (vencidasCount > 0) subParts.push(vencidasCount + " vencida(s)");
      subParts.push((estoque.vencendo.urgente.count || 0) + " urgente");
      subParts.push((estoque.vencendo.atencao.count || 0) + " atencao");
      setText("kpi-alertas-sub", subParts.join(", "));
    } else {
      setText("kpi-estoque", "-");
      setText("kpi-estoque-sub", "Planilha indisponivel");
      setText("kpi-alertas", "-");
      setText("kpi-alertas-sub", "Requer planilha");
    }

    setText("kpi-entradas-7d", stats.bolsas_7d || 0);
    setText("kpi-entradas-7d-sub", (stats.importacoes_7d || 0) + " importacoes");
    setText("kpi-entradas-30d", stats.bolsas_30d || 0);
    setText("kpi-entradas-30d-sub", (stats.importacoes_30d || 0) + " importacoes");

    // === Alert Banners ===
    const alertBanners = document.getElementById("alert-banners");
    alertBanners.innerHTML = "";
    if (estoque) {
      if (estoque.vencendo.vencidas && estoque.vencendo.vencidas.count > 0) {
        alertBanners.appendChild(makeBanner(
          "vencidas",
          estoque.vencendo.vencidas.count + " bolsa(s) ja vencida(s)",
          "/consulta?vencimento=vencidas&dias_max=0&em_estoque=1"
        ));
      }
      if (estoque.vencendo.urgente.count > 0) {
        alertBanners.appendChild(makeBanner(
          "urgente",
          estoque.vencendo.urgente.count + " bolsa(s) vence(m) em ate " + thresholdUrgente + " dias",
          "/consulta?vencimento=urgente&dias_max=" + thresholdUrgente + "&em_estoque=1"
        ));
      }
      if (estoque.vencendo.atencao.count > 0) {
        alertBanners.appendChild(makeBanner(
          "atencao",
          estoque.vencendo.atencao.count + " bolsa(s) vence(m) em ate " + thresholdAtencao + " dias",
          "/consulta?vencimento=atencao&dias_max=" + thresholdAtencao + "&em_estoque=1"
        ));
      }
    }

    // === Stock Charts ===
    const dist = hist.distribuicao || {};

    // Choose source: live stock if available, else historical distribution
    if (estoque) {
      renderBars("chart-gs-rh", estoque.por_gs_rh, "bar-fill-blood");
      renderBars("chart-hemo", estoque.por_hemocomponente, "bar-fill-component");
    } else {
      renderBars("chart-gs-rh", dist.por_gs_rh || [], "bar-fill-blood");
      renderBars("chart-hemo", dist.por_hemocomponente || [], "bar-fill-component");
    }

    // === Evolution Chart ===
    renderEvolution(hist.evolucao_diaria || []);

    // === Statistics ===
    setText("stat-total-imports", stats.total_importacoes || 0);
    setText("stat-total-bolsas", stats.total_bolsas || 0);
    setText("stat-media-bolsas", stats.media_bolsas_por_importacao || 0);
    setText("stat-media-vol", (stats.media_volume_ml || 0) + " mL");
    if (stats.ultima_importacao) {
      try {
        const d = new Date(stats.ultima_importacao);
        setText("stat-ultima", d.toLocaleString("pt-BR"));
      } catch (e) {
        setText("stat-ultima", stats.ultima_importacao);
      }
    }

    // Volume distribution
    renderBars("chart-volume", (dist.por_volume || []).map(v => ({tipo: v.faixa, count: v.count})), "bar-fill-component");

    // Historical by type
    renderHistTipo(hist.evolucao_tipo || []);

    // === Expiry Section ===
    const expirySection = document.getElementById("expiry-section");
    const expiryEmpty = document.getElementById("expiry-empty");
    expirySection.innerHTML = "";
    let hasExpiry = false;

    if (estoque) {
      if (estoque.vencendo.vencidas && estoque.vencendo.vencidas.bolsas && estoque.vencendo.vencidas.bolsas.length > 0) {
        expirySection.appendChild(renderExpiryGroup(
          "Vencidas", estoque.vencendo.vencidas.bolsas, "vencidas",
          "/consulta?vencimento=vencidas&dias_max=0&em_estoque=1"
        ));
        hasExpiry = true;
      }
      if (estoque.vencendo.urgente.bolsas && estoque.vencendo.urgente.bolsas.length > 0) {
        expirySection.appendChild(renderExpiryGroup(
          "Urgente", estoque.vencendo.urgente.bolsas, "urgente",
          "/consulta?vencimento=urgente&dias_max=" + thresholdUrgente + "&em_estoque=1"
        ));
        hasExpiry = true;
      }
      if (estoque.vencendo.atencao.bolsas && estoque.vencendo.atencao.bolsas.length > 0) {
        expirySection.appendChild(renderExpiryGroup(
          "Atencao", estoque.vencendo.atencao.bolsas, "atencao",
          "/consulta?vencimento=atencao&dias_max=" + thresholdAtencao + "&em_estoque=1"
        ));
        hasExpiry = true;
      }
    }
    expiryEmpty.classList.toggle("hidden", hasExpiry);

    // === Recent Imports Table ===
    const recentBody = document.getElementById("recent-body");
    const recentEmpty = document.getElementById("recent-empty");
    recentBody.innerHTML = "";
    const recentes = hist.recentes || [];
    if (recentes.length > 0) {
      recentEmpty.classList.add("hidden");
      recentes.forEach(b => {
        const tr = document.createElement("tr");
        let tsFormatted = "-";
        if (b.timestamp) {
          try { tsFormatted = new Date(b.timestamp).toLocaleString("pt-BR"); } catch(e) {}
        }
        tr.innerHTML =
          "<td>" + esc(b.num_bolsa) + "</td>" +
          "<td>" + esc(b.tipo_hemocomponente) + "</td>" +
          "<td>" + esc(b.gs_rh) + "</td>" +
          "<td>" + (b.volume || 0) + " mL</td>" +
          "<td>" + esc(b.data_validade) + "</td>" +
          "<td>" + tsFormatted + "</td>";
        recentBody.appendChild(tr);
      });
    } else {
      recentEmpty.classList.remove("hidden");
    }

    // Updated at
    const updatedAt = document.getElementById("updated-at");
    if (estoque && estoque.ultima_atualizacao) {
      updatedAt.textContent = "Estoque atualizado em: " + estoque.ultima_atualizacao;
    } else {
      updatedAt.textContent = "Dados historicos atualizados agora";
    }
  }

  // === Render helpers ===

  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function makeBanner(level, text, href) {
    const div = document.createElement("div");
    div.className = "alert-banner alert-banner-" + level;
    if (href) {
      const link = document.createElement("a");
      link.href = href;
      link.className = "alert-banner-link";
      link.innerHTML = '<span>' + esc(text) + '</span><span class="alert-banner-action">Ver na Consulta &rarr;</span>';
      div.appendChild(link);
    } else {
      div.textContent = text;
    }
    return div;
  }

  function renderBars(containerId, items, fillClass) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";

    if (!items || items.length === 0) {
      container.innerHTML = '<p class="dash-empty-inline">Sem dados</p>';
      return;
    }

    const maxVal = Math.max(...items.map(i => i.count));

    items.forEach(item => {
      const pct = maxVal > 0 ? (item.count / maxVal) * 100 : 0;
      const row = document.createElement("div");
      row.className = "bar-row";
      row.innerHTML =
        '<span class="bar-label">' + esc(item.tipo) + '</span>' +
        '<div class="bar-track"><div class="bar-fill ' + fillClass + '" style="width:' + pct + '%"></div></div>' +
        '<span class="bar-count">' + item.count + '</span>';
      container.appendChild(row);
    });
  }

  function renderEvolution(data) {
    const container = document.getElementById("evolution-chart");
    if (!container) return;
    container.innerHTML = "";

    if (!data || data.length === 0) {
      container.innerHTML = '<p class="dash-empty-inline">Sem dados de evolucao ainda</p>';
      return;
    }

    // Fill in missing days
    const filled = fillDays(data, 30);
    const maxVal = Math.max(...filled.map(d => d.total), 1);

    const chart = document.createElement("div");
    chart.className = "evo-bars";

    filled.forEach(d => {
      const col = document.createElement("div");
      col.className = "evo-col";

      const bar = document.createElement("div");
      bar.className = "evo-bar";
      const h = Math.max((d.total / maxVal) * 100, d.total > 0 ? 4 : 0);
      bar.style.height = h + "%";
      bar.title = d.dia + ": " + d.total + " bolsas";

      const label = document.createElement("div");
      label.className = "evo-label";
      // Show label every 5 days
      const idx = filled.indexOf(d);
      if (idx % 5 === 0 || idx === filled.length - 1) {
        label.textContent = d.dia.substring(5); // MM-DD
      }

      col.appendChild(bar);
      col.appendChild(label);
      chart.appendChild(col);
    });

    container.appendChild(chart);
  }

  function fillDays(data, days) {
    const map = {};
    data.forEach(d => { map[d.dia] = d.total; });

    const result = [];
    const now = new Date();
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const key = d.toISOString().substring(0, 10);
      result.push({ dia: key, total: map[key] || 0 });
    }
    return result;
  }

  function renderHistTipo(data) {
    const container = document.getElementById("chart-tipo-hist");
    if (!container) return;
    container.innerHTML = "";

    if (!data || data.length === 0) {
      container.innerHTML = '<p class="dash-empty-inline">Sem dados</p>';
      return;
    }

    // Aggregate by gs_rh
    const agg = {};
    data.forEach(d => {
      if (!agg[d.gs_rh]) agg[d.gs_rh] = 0;
      agg[d.gs_rh] += d.count;
    });

    const items = Object.entries(agg)
      .sort((a, b) => b[1] - a[1])
      .map(([tipo, count]) => ({ tipo, count }));

    renderBars("chart-tipo-hist", items, "bar-fill-blood");
  }

  function renderExpiryGroup(title, bolsas, level, consultaHref) {
    const div = document.createElement("div");
    div.style.marginBottom = "0.75rem";

    const header = document.createElement("div");
    header.className = "expiry-header expiry-header-" + level;
    header.style.cursor = "pointer";
    header.innerHTML =
      '<span>' + esc(title) + ' (' + bolsas.length + ' bolsas)</span>' +
      '<a href="' + consultaHref + '" class="expiry-consulta-link" title="Filtrar na Consulta">Ver na Consulta &rarr;</a>';

    // Prevent link click from toggling the list
    header.querySelector(".expiry-consulta-link").addEventListener("click", e => e.stopPropagation());

    const list = document.createElement("div");
    list.className = "expiry-list";

    bolsas.forEach(b => {
      const item = document.createElement("div");
      item.className = "expiry-item";
      const diasLabel = b.dias_restantes < 0
        ? Math.abs(b.dias_restantes) + "d atras"
        : b.dias_restantes + "d";
      item.innerHTML =
        '<span class="expiry-days expiry-days-' + level + '">' + diasLabel + '</span>' +
        '<span>' + esc(b.num_bolsa) + '</span>' +
        '<span>' + esc(b.tipo) + '</span>' +
        '<span>' + esc(b.gs_rh) + '</span>' +
        '<span>' + b.volume + 'mL</span>' +
        '<span>' + esc(b.data_validade) + '</span>';
      list.appendChild(item);
    });

    header.addEventListener("click", () => {
      list.style.display = list.style.display === "none" ? "block" : "none";
    });

    div.appendChild(header);
    div.appendChild(list);
    return div;
  }

  function esc(text) {
    const div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
  }

  btnRefresh.addEventListener("click", () => loadDashboard(true));
  loadDashboard(false);
});
