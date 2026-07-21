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

  const searchForm = document.querySelector("[data-address-search-form]");
  const autocomplete = document.querySelector("[data-address-autocomplete]");
  const addressInput = document.getElementById("address");
  const suggestionPopup = document.getElementById("address-suggestion-popup");
  const suggestionList = document.getElementById("address-suggestion-list");
  const suggestionNote = document.getElementById("address-suggestion-note");
  const suggestionStatus = document.getElementById("address-suggestion-status");

  if (
    searchForm instanceof HTMLFormElement
    && autocomplete instanceof HTMLElement
    && addressInput instanceof HTMLInputElement
    && suggestionPopup instanceof HTMLElement
    && suggestionList instanceof HTMLElement
    && suggestionNote instanceof HTMLElement
    && suggestionStatus instanceof HTMLElement
  ) {
    let suggestions = [];
    let activeIndex = -1;
    let debounceTimer = null;
    let requestController = null;
    let renderedQuery = "";

    const announce = (message) => {
      suggestionStatus.textContent = "";
      window.requestAnimationFrame(() => {
        suggestionStatus.textContent = message;
      });
    };

    const setActive = (index) => {
      const options = [...suggestionList.querySelectorAll("[role='option']")];
      if (!options.length) {
        activeIndex = -1;
        addressInput.removeAttribute("aria-activedescendant");
        return;
      }
      activeIndex = Math.max(0, Math.min(index, options.length - 1));
      for (const [optionIndex, option] of options.entries()) {
        option.setAttribute("aria-selected", String(optionIndex === activeIndex));
      }
      const active = options[activeIndex];
      addressInput.setAttribute("aria-activedescendant", active.id);
      active.scrollIntoView({ block: "nearest" });
    };

    const closeSuggestions = () => {
      suggestionPopup.hidden = true;
      addressInput.setAttribute("aria-expanded", "false");
      addressInput.removeAttribute("aria-activedescendant");
      activeIndex = -1;
    };

    const showNote = (
      message,
      { announceMessage = message, state = "notice" } = {},
    ) => {
      suggestions = [];
      activeIndex = -1;
      suggestionList.replaceChildren();
      suggestionNote.textContent = message;
      suggestionNote.hidden = false;
      suggestionPopup.hidden = false;
      suggestionPopup.dataset.state = state;
      addressInput.setAttribute("aria-expanded", "true");
      addressInput.removeAttribute("aria-activedescendant");
      announce(announceMessage);
    };

    const submitSuggestion = (index) => {
      const suggestion = suggestions[index];
      if (!suggestion) return;
      addressInput.value = suggestion.value;
      closeSuggestions();
      if (typeof searchForm.requestSubmit === "function") searchForm.requestSubmit();
      else searchForm.submit();
    };

    const renderSuggestions = (payload) => {
      const rawSuggestions = Array.isArray(payload.suggestions)
        ? payload.suggestions
        : [];
      suggestions = rawSuggestions.filter((suggestion) =>
        suggestion
        && typeof suggestion.value === "string"
        && typeof suggestion.display_address === "string"
        && typeof suggestion.secondary_text === "string"
        && Number.isInteger(suggestion.source_record_count)
        && suggestion.source_record_count > 0
      );
      activeIndex = -1;
      suggestionList.replaceChildren();
      addressInput.removeAttribute("aria-activedescendant");

      if (!suggestions.length) {
        showNote(
          "No matching Santa Clara addresses. Keep typing or enter the full address.",
          { state: "no-results" },
        );
        return;
      }

      const fragment = document.createDocumentFragment();
      for (const [index, suggestion] of suggestions.entries()) {
        const option = document.createElement("li");
        option.id = `address-suggestion-${index}`;
        option.className = "address-suggestion-option";
        option.setAttribute("role", "option");
        option.setAttribute("aria-selected", "false");

        const primary = document.createElement("span");
        primary.className = "address-suggestion-primary";
        primary.textContent = suggestion.display_address;
        option.append(primary);

        const secondary = document.createElement("span");
        secondary.className = "address-suggestion-secondary";
        secondary.textContent = suggestion.secondary_text;
        option.append(secondary);

        if (suggestion.source_record_count > 1) {
          const duplicate = document.createElement("span");
          duplicate.className = "address-suggestion-duplicate";
          duplicate.textContent = `${suggestion.source_record_count} matching City records; lookup may require review`;
          option.append(duplicate);
        }

        option.addEventListener("mouseenter", () => setActive(index));
        option.addEventListener("click", () => submitSuggestion(index));
        fragment.append(option);
      }
      suggestionList.append(fragment);

      const total = Number.isInteger(payload.total_matches)
        ? payload.total_matches
        : suggestions.length;
      const truncated = payload.truncated === true;
      suggestionNote.hidden = !truncated;
      suggestionNote.textContent = truncated
        ? `${total} matching addresses. Continue typing a street or unit number to narrow the list.`
        : "";
      suggestionPopup.hidden = false;
      suggestionPopup.dataset.state = truncated ? "truncated" : "results";
      addressInput.setAttribute("aria-expanded", "true");
      announce(
        truncated
          ? `${total} matching addresses. ${suggestions.length} shown. Continue typing to narrow the list.`
          : `${suggestions.length} address ${suggestions.length === 1 ? "suggestion" : "suggestions"} available.`,
      );
    };

    const fetchSuggestions = async (query) => {
      if (requestController) requestController.abort();
      requestController = new AbortController();
      const controller = requestController;
      try {
        const response = await fetch(
          `/api/address-suggestions?q=${encodeURIComponent(query)}`,
          {
            headers: { Accept: "application/json" },
            signal: controller.signal,
          },
        );
        const payload = await response.json();
        if (controller.signal.aborted || addressInput.value !== query) return;
        if (!response.ok || payload.query !== query) {
          throw new Error("Address suggestions unavailable");
        }
        renderedQuery = query;
        if (payload.status === "query_too_short") {
          showNote(
            "Type at least 3 address characters after abbreviations and locality details are normalized.",
            { state: "no-results" },
          );
          return;
        }
        renderSuggestions(payload);
      } catch (error) {
        if (controller.signal.aborted) return;
        showNote(
          "Suggestions are unavailable. Enter the full address and use the lookup button.",
          { state: "unavailable" },
        );
      }
    };

    addressInput.addEventListener("input", () => {
      window.clearTimeout(debounceTimer);
      if (requestController) requestController.abort();
      renderedQuery = "";
      suggestions = [];
      closeSuggestions();
      const query = addressInput.value;
      if (query.length > 120) {
        showNote(
          "Address suggestions accept at most 120 characters. Shorten the search or use the lookup button.",
          { state: "unavailable" },
        );
        return;
      }
      const alphanumericLength = (query.match(/[A-Za-z0-9]/g) || []).length;
      if (alphanumericLength < 3) {
        announce("Type at least 3 characters for Santa Clara address suggestions.");
        return;
      }
      showNote("Loading address suggestions…", {
        announceMessage: "Loading address suggestions.",
        state: "loading",
      });
      debounceTimer = window.setTimeout(() => fetchSuggestions(query), 150);
    });

    addressInput.addEventListener("focus", () => {
      if (suggestions.length && renderedQuery === addressInput.value) {
        suggestionPopup.hidden = false;
        addressInput.setAttribute("aria-expanded", "true");
      }
    });

    addressInput.addEventListener("keydown", (event) => {
      if (!suggestions.length) {
        if (event.key === "Escape") closeSuggestions();
        return;
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        if (suggestionPopup.hidden) {
          suggestionPopup.hidden = false;
          addressInput.setAttribute("aria-expanded", "true");
        }
        setActive(activeIndex < 0 ? 0 : (activeIndex + 1) % suggestions.length);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        if (suggestionPopup.hidden) {
          suggestionPopup.hidden = false;
          addressInput.setAttribute("aria-expanded", "true");
        }
        setActive(activeIndex < 0 ? suggestions.length - 1 : (activeIndex - 1 + suggestions.length) % suggestions.length);
      } else if (event.key === "Home" && activeIndex >= 0) {
        event.preventDefault();
        setActive(0);
      } else if (event.key === "End" && activeIndex >= 0) {
        event.preventDefault();
        setActive(suggestions.length - 1);
      } else if (event.key === "Enter" && activeIndex >= 0) {
        event.preventDefault();
        submitSuggestion(activeIndex);
      } else if (event.key === "Escape") {
        event.preventDefault();
        closeSuggestions();
      } else if (event.key === "Tab") {
        closeSuggestions();
      }
    });

    searchForm.addEventListener("submit", () => {
      window.clearTimeout(debounceTimer);
      if (requestController) requestController.abort();
      closeSuggestions();
    });

    document.addEventListener("pointerdown", (event) => {
      if (!(event.target instanceof Node) || autocomplete.contains(event.target)) return;
      closeSuggestions();
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
