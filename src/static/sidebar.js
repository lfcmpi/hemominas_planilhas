document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.getElementById("sidebar");
    const hamburger = document.getElementById("hamburger-btn");
    const overlay = document.getElementById("sidebar-overlay");

    if (hamburger) {
        hamburger.addEventListener("click", () => {
            sidebar.classList.toggle("open");
            overlay.classList.toggle("open");
        });
    }

    if (overlay) {
        overlay.addEventListener("click", () => {
            sidebar.classList.remove("open");
            overlay.classList.remove("open");
        });
    }

    // Fetch alert badge count
    fetch("/api/alertas/pendentes")
        .then(r => r.json())
        .then(data => {
            const total = (data.vencidas || 0) + (data.urgente || 0) + (data.atencao || 0);
            const badge = document.getElementById("sidebar-alert-badge");
            if (badge && total > 0) {
                badge.textContent = total;
                badge.style.display = "inline-flex";
            }
        })
        .catch(() => {});
});
