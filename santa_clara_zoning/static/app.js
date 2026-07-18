(() => {
  "use strict";

  for (const region of document.querySelectorAll(".table-scroll")) {
    region.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      const direction = event.key === "ArrowRight" ? 1 : -1;
      region.scrollLeft += direction * Math.max(80, region.clientWidth * 0.35);
      event.preventDefault();
    });
  }

  const triggers = [...document.querySelectorAll("[data-source-popover]")];
  if (!triggers.length) return;

  const supportsPopover = typeof HTMLElement.prototype.showPopover === "function";
  const states = new WeakMap();
  const entries = [];

  const panelFor = (trigger) =>
    document.getElementById(trigger.dataset.sourcePopover);

  const isOpen = (panel) =>
    supportsPopover ? panel.matches(":popover-open") : !panel.hidden;

  const positionPanel = (trigger, panel) => {
    const gap = 8;
    const edge = 8;
    const triggerBox = trigger.getBoundingClientRect();
    const panelBox = panel.getBoundingClientRect();
    const left = Math.min(
      window.innerWidth - panelBox.width - edge,
      Math.max(edge, triggerBox.left + triggerBox.width / 2 - panelBox.width / 2),
    );
    const roomBelow = window.innerHeight - triggerBox.bottom;
    const top = roomBelow >= panelBox.height + gap
      ? triggerBox.bottom + gap
      : Math.max(edge, triggerBox.top - panelBox.height - gap);

    panel.style.left = `${left}px`;
    panel.style.top = `${top}px`;
  };

  const openPanel = (trigger, panel) => {
    if (!isOpen(panel)) {
      if (supportsPopover) panel.showPopover();
      else panel.hidden = false;
    }
    trigger.setAttribute("aria-expanded", "true");
    positionPanel(trigger, panel);
  };

  const closePanel = (trigger, panel) => {
    if (isOpen(panel)) {
      if (supportsPopover) panel.hidePopover();
      else panel.hidden = true;
    }
    trigger.setAttribute("aria-expanded", "false");
  };

  const cancelClose = (state) => {
    window.clearTimeout(state.closeTimer);
    state.closeTimer = null;
  };

  const scheduleClose = (trigger, panel, state) => {
    cancelClose(state);
    state.closeTimer = window.setTimeout(() => {
      const focusInside = trigger === document.activeElement || panel.contains(document.activeElement);
      const hoverInside = trigger.matches(":hover") || panel.matches(":hover");
      if (!state.pinned && !focusInside && !hoverInside) closePanel(trigger, panel);
    }, 140);
  };

  for (const trigger of triggers) {
    const panel = panelFor(trigger);
    if (!panel) continue;

    const state = { pinned: false, closeTimer: null };
    states.set(trigger, state);
    entries.push({ trigger, panel, state });
    if (supportsPopover) panel.hidden = false;

    trigger.addEventListener("mouseenter", () => {
      cancelClose(state);
      openPanel(trigger, panel);
    });
    trigger.addEventListener("mouseleave", () => scheduleClose(trigger, panel, state));
    trigger.addEventListener("focus", () => {
      cancelClose(state);
      openPanel(trigger, panel);
    });
    trigger.addEventListener("blur", () => scheduleClose(trigger, panel, state));
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      if (isOpen(panel) && state.pinned) {
        state.pinned = false;
        closePanel(trigger, panel);
      } else {
        state.pinned = true;
        openPanel(trigger, panel);
      }
    });

    panel.addEventListener("mouseenter", () => cancelClose(state));
    panel.addEventListener("mouseleave", () => scheduleClose(trigger, panel, state));
    panel.addEventListener("focusin", () => cancelClose(state));
    panel.addEventListener("focusout", () => scheduleClose(trigger, panel, state));
    panel.addEventListener("click", (event) => {
      if (!(event.target instanceof Element)) return;
      const link = event.target.closest("a[href^='#source-']");
      if (!link) return;

      const target = document.querySelector(link.hash);
      if (!target) return;

      event.preventDefault();
      state.pinned = false;
      closePanel(trigger, panel);
      const disclosure = target.closest("details");
      if (disclosure) disclosure.open = true;
      target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
      target.scrollIntoView({ block: "start" });
      window.history.pushState(null, "", link.hash);
      target.addEventListener("blur", () => target.removeAttribute("tabindex"), {
        once: true,
      });
    });
    panel.addEventListener("toggle", () => {
      const open = isOpen(panel);
      trigger.setAttribute("aria-expanded", String(open));
      if (!open) state.pinned = false;
    });
  }

  const closeAllPanels = (restoreFocus) => {
    for (const { trigger, panel, state } of entries) {
      if (!isOpen(panel)) continue;
      const focusWasInside = panel.contains(document.activeElement);
      state.pinned = false;
      closePanel(trigger, panel);
      if (restoreFocus && focusWasInside) trigger.focus();
    }
  };

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeAllPanels(true);
  });

  document.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) return;
    if (event.target.closest("[data-source-popover], .source-popover")) return;
    closeAllPanels(false);
  });

  const repositionOpenPanels = () => {
    for (const trigger of triggers) {
      const panel = panelFor(trigger);
      if (panel && isOpen(panel)) positionPanel(trigger, panel);
    }
  };

  window.addEventListener("resize", repositionOpenPanels);
  window.addEventListener("scroll", repositionOpenPanels, true);
})();
