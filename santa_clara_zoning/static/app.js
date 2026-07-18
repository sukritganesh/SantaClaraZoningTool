(() => {
  "use strict";

  const triggers = [...document.querySelectorAll("[data-source-popover]")];
  if (!triggers.length) return;

  const supportsPopover = typeof HTMLElement.prototype.showPopover === "function";
  const states = new WeakMap();

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
    panel.addEventListener("toggle", () => {
      const open = isOpen(panel);
      trigger.setAttribute("aria-expanded", String(open));
      if (!open) state.pinned = false;
    });
  }

  const repositionOpenPanels = () => {
    for (const trigger of triggers) {
      const panel = panelFor(trigger);
      if (panel && isOpen(panel)) positionPanel(trigger, panel);
    }
  };

  window.addEventListener("resize", repositionOpenPanels);
  window.addEventListener("scroll", repositionOpenPanels, true);
})();
