document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) lucide.createIcons();
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");
  const toggle = document.getElementById("menuToggle");
  const closeMenu = () => {
    sidebar?.classList.remove("open");
    overlay?.classList.remove("show");
  };
  toggle?.addEventListener("click", () => {
    sidebar?.classList.toggle("open");
    overlay?.classList.toggle("show");
  });
  overlay?.addEventListener("click", closeMenu);

  const formPanel = document.getElementById("form-panel");
  if (formPanel && window.innerWidth <= 1050) {
    formPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const contractType = document.querySelector("[data-contract-type]");
  const contractStart = document.querySelector("[data-contract-start]");
  const contractEnd = document.querySelector("[data-contract-end]");
  const updateContractFields = () => {
    const isCdd = contractType?.value === "CDD";
    [contractStart, contractEnd].forEach((input) => {
      if (!input) return;
      input.closest("label")?.classList.toggle("contract-date-hidden", !isCdd);
      input.required = isCdd;
      if (!isCdd) input.value = "";
    });
  };
  contractType?.addEventListener("change", updateContractFields);
  updateContractFields();

  const alertBell = document.querySelector("[data-alert-bell]");
  const alertsNav = document.querySelector("[data-alerts-nav]");
  if (alertBell) {
    let knownUnread = Number(alertBell.querySelector("span")?.textContent || 0);

    const updateBadge = (container, className, count) => {
      let badge = container?.querySelector(`.${className}`);
      if (!count) {
        badge?.remove();
        return;
      }
      if (!badge) {
        badge = document.createElement("span");
        badge.className = className;
        container?.appendChild(badge);
      }
      badge.textContent = count;
    };

    const showAlertToast = (alert) => {
      if (!alert) return;
      document.querySelector(".gps-alert-toast")?.remove();
      const toast = document.createElement("a");
      toast.className = "gps-alert-toast";
      toast.href = "/alertes/";
      toast.innerHTML = `
        <span class="gps-alert-toast-icon"><i data-lucide="wifi-off"></i></span>
        <span><strong>Nouvelle alerte</strong><small>${alert.message}</small></span>
        <i data-lucide="chevron-right"></i>`;
      document.body.appendChild(toast);
      if (window.lucide) lucide.createIcons();
      window.setTimeout(() => toast.classList.add("visible"), 50);
      window.setTimeout(() => toast.remove(), 10000);
    };

    const pollAlerts = async () => {
      try {
        const response = await fetch("/api/alerts/unread-count/", { credentials: "same-origin" });
        if (!response.ok) return;
        const data = await response.json();
        updateBadge(alertBell, "alert-live-count", data.unread_count);
        updateBadge(alertsNav, "nav-alert-count", data.unread_count);
        if (data.unread_count > knownUnread) showAlertToast(data.latest_alert);
        knownUnread = data.unread_count;
      } catch (_error) {
        // La prochaine vérification reprendra automatiquement.
      }
    };

    pollAlerts();
    window.setInterval(pollAlerts, 30000);
  }
});
