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

  const propertyMap = document.querySelector("[data-property-map]");
  const mapFallback = document.querySelector("[data-map-fallback]");
  const mapLegend = document.querySelector("[data-map-legend]");
  const mapZoneLegend = document.querySelector("[data-map-zone-legend]");
  const mapSummary = document.querySelector("[data-map-summary]");
  const mapStatus = document.querySelector("[data-map-status]");
  const mapLegendSummary = mapLegend?.querySelector("summary");

  if (
    propertyMap instanceof HTMLElement
    && mapFallback instanceof HTMLElement
    && mapLegend instanceof HTMLElement
    && mapLegendSummary instanceof HTMLElement
    && mapZoneLegend instanceof HTMLElement
    && mapSummary instanceof HTMLElement
    && mapStatus instanceof HTMLElement
  ) {
    const frame = propertyMap.closest(".property-map-frame");
    const endpoint = propertyMap.dataset.endpoint || "";
    const selectedZone = propertyMap.dataset.selectedZone || "";
    const tileUrl = propertyMap.dataset.tileUrl || "";
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    mapLegendSummary.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        mapLegend.open = !mapLegend.open;
      }
    });
    mapLegend.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && mapLegend.open) {
        event.preventDefault();
        mapLegend.open = false;
        mapLegendSummary.focus();
      }
    });
    document.addEventListener("click", (event) => {
      if (
        mapLegend.open
        && event.target instanceof Node
        && !mapLegend.contains(event.target)
      ) {
        mapLegend.open = false;
      }
    });

    // High-saturation categorical colors maximize separation between the 12
    // supported designations. They are presentation values, not analysis inputs.
    const zoneDisplayColors = Object.freeze({
      "R1-6L": "#0067c5",
      "R1-8L": "#f28e00",
      R2: "#009e49",
      R3: "#7a3e9d",
      R4: "#d62728",
      R5: "#00a6d6",
      R6: "#e6c200",
      "PH-R5": "#c51b7d",
      UC: "#8c510a",
      UV: "#008c95",
      VR: "#7a9a01",
      HDF: "#444444",
    });
    const defaultZoningColor = "#6b7280";

    const announceMap = (message) => {
      mapStatus.textContent = "";
      window.requestAnimationFrame(() => {
        mapStatus.textContent = message;
      });
    };

    const setMapState = (state, message = "") => {
      if (frame instanceof HTMLElement) frame.dataset.mapState = state;
      if (message) mapFallback.textContent = message;
    };

    const addLegendItem = (zone, selected) => {
      const item = document.createElement("li");
      const swatch = document.createElement("span");
      swatch.className = selected
        ? "map-swatch map-swatch--selected-zone"
        : "map-swatch";
      swatch.style.setProperty(
        "--swatch-color",
        zoneDisplayColors[zone] || defaultZoningColor,
      );
      swatch.setAttribute("aria-hidden", "true");
      const label = document.createElement("span");
      label.textContent = zone;
      if (selected) item.setAttribute("aria-label", `${zone}, selected zoning`);
      item.append(swatch, label);
      mapZoneLegend.append(item);
    };

    const bindZoningTooltip = (feature, layer) => {
      const zone = feature?.properties?.zone;
      if (!zone || typeof layer.bindTooltip !== "function") return;
      const tooltip = document.createElement("span");
      tooltip.textContent = `Zoning: ${zone}`;
      layer.bindTooltip(tooltip, {
        className: "zoning-hover-tooltip",
        direction: "top",
        offset: [0, -4],
        opacity: 0.98,
        sticky: true,
      });
    };

    const renderPropertyMap = async () => {
      if (!endpoint || !selectedZone || typeof window.L !== "object") {
        setMapState(
          "error",
          "Parcel and zoning map context is unavailable. The zoning result remains usable.",
        );
        announceMap("Parcel and zoning map context is unavailable.");
        return;
      }

      setMapState("loading", "Loading local parcel and zoning context…");
      try {
        const response = await fetch(endpoint, {
          headers: { Accept: "application/json" },
        });
        const payload = await response.json();
        if (
          !response.ok
          || payload.status !== "ok"
          || payload.contract_version !== "1.0.0"
          || payload.property?.zone !== selectedZone
          || payload.selected_parcel?.type !== "Feature"
          || payload.supported_zoning?.type !== "FeatureCollection"
          || !Array.isArray(payload.supported_zoning.features)
        ) {
          throw new Error("Invalid property map response");
        }

        const leaflet = window.L;
        const map = leaflet.map(propertyMap, {
          attributionControl: false,
          boxZoom: false,
          fadeAnimation: !reducedMotion,
          keyboard: true,
          maxBoundsViscosity: 1,
          maxZoom: 19,
          markerZoomAnimation: !reducedMotion,
          scrollWheelZoom: false,
          touchZoom: true,
          zoomAnimation: !reducedMotion,
          zoomControl: true,
        });

        let basemapTileLoaded = false;
        let basemapFailureAnnounced = false;
        if (tileUrl) {
          leaflet.tileLayer(tileUrl, {
            maxNativeZoom: 19,
            maxZoom: 19,
            updateWhenIdle: true,
          })
            .on("tileload", () => {
              if (basemapTileLoaded) return;
              basemapTileLoaded = true;
              if (frame?.dataset.mapState === "tiles-unavailable") {
                setMapState("ready");
                announceMap("Street basemap is available. Local zoning context remains displayed.");
              }
            })
            .on("tileerror", () => {
              if (basemapTileLoaded || basemapFailureAnnounced) return;
              basemapFailureAnnounced = true;
              setMapState(
                "tiles-unavailable",
                "Street basemap unavailable; local zoning geometry is still shown.",
              );
              announceMap(
                "Street basemap unavailable. Local parcel and zoning geometry remains displayed.",
              );
            })
            .addTo(map);
        }

        const visibleZones = new Set();
        leaflet.geoJSON(payload.supported_zoning, {
          interactive: true,
          onEachFeature: bindZoningTooltip,
          style: (feature) => {
            const zone = feature?.properties?.zone || "";
            const selected = zone === selectedZone;
            if (zone) visibleZones.add(zone);
            return {
              className: selected
                ? "zoning-overlay zoning-overlay--selected"
                : "zoning-overlay",
              color: selected ? "#4b4b3f" : "#6e6e6e",
              fillColor: zoneDisplayColors[zone] || defaultZoningColor,
              fillOpacity: selected ? 0.62 : 0.48,
              opacity: selected ? 0.9 : 0.65,
              weight: selected ? 1.2 : 0.65,
            };
          },
        }).addTo(map);

        leaflet.geoJSON(payload.selected_parcel, {
          interactive: false,
          style: {
            className: "selected-parcel-halo",
            color: "#ffffff",
            fill: false,
            opacity: 0.95,
            weight: 10,
          },
        }).addTo(map);
        leaflet.geoJSON(payload.selected_parcel, {
          interactive: false,
          style: {
            className: "selected-parcel-outline",
            color: "#10482d",
            fill: false,
            opacity: 1,
            weight: 5,
          },
        }).addTo(map);

        const selectedBounds = leaflet.latLngBounds(
          [payload.selected_bounds.south, payload.selected_bounds.west],
          [payload.selected_bounds.north, payload.selected_bounds.east],
        );
        const contextBounds = leaflet.latLngBounds(
          [payload.context_bounds.south, payload.context_bounds.west],
          [payload.context_bounds.north, payload.context_bounds.east],
        );
        map.setMaxBounds(contextBounds);
        map.fitBounds(selectedBounds, {
          animate: false,
          maxZoom: 19,
          padding: [32, 32],
        });
        map.setMinZoom(Math.max(0, map.getZoom() - 1));

        mapZoneLegend.replaceChildren();
        const orderedZones = Array.isArray(payload.supported_zones)
          ? payload.supported_zones.filter((zone) => visibleZones.has(zone))
          : [...visibleZones].sort();
        for (const zone of orderedZones) addLegendItem(zone, zone === selectedZone);
        mapLegend.hidden = false;
        mapSummary.textContent = (
          `The outlined parcel ${payload.property.apn} is in the ${selectedZone} `
          + `supported zoning overlay. ${payload.zoning_feature_count} nearby `
          + `supported zoning polygons are displayed using a high-contrast categorical palette.`
        );
        if (!basemapFailureAnnounced || basemapTileLoaded) {
          setMapState("ready");
        }
        announceMap(
          `Parcel and zoning map loaded for ${payload.property.display_address}. `
          + `${payload.zoning_feature_count} supported zoning polygons are visible.`,
        );
        window.requestAnimationFrame(() => map.invalidateSize(false));
      } catch (error) {
        setMapState(
          "error",
          "Parcel and zoning map context is unavailable. The zoning result remains usable.",
        );
        announceMap("Parcel and zoning map context is unavailable.");
      }
    };

    renderPropertyMap();
  }

  const evidenceViewer = document.querySelector("[data-evidence-viewer]");
  if (evidenceViewer instanceof HTMLElement) {
    const pages = [...evidenceViewer.querySelectorAll("[data-evidence-page]")];
    const pageContainer = evidenceViewer.querySelector(".evidence-pages");
    const previousButton = evidenceViewer.querySelector("[data-evidence-previous]");
    const nextButton = evidenceViewer.querySelector("[data-evidence-next]");
    const fitButton = evidenceViewer.querySelector("[data-evidence-fit]");
    const zoomOutButton = evidenceViewer.querySelector("[data-evidence-zoom-out]");
    const zoomInButton = evidenceViewer.querySelector("[data-evidence-zoom-in]");
    const pageStatus = evidenceViewer.querySelector("[data-evidence-page-status]");

    if (
      pages.length
      && pageContainer instanceof HTMLElement
      && previousButton instanceof HTMLButtonElement
      && nextButton instanceof HTMLButtonElement
      && fitButton instanceof HTMLButtonElement
      && zoomOutButton instanceof HTMLButtonElement
      && zoomInButton instanceof HTMLButtonElement
      && pageStatus instanceof HTMLElement
    ) {
      const zoomLevels = [75, 100, 125, 150, 175, 200];
      let activePage = 0;
      let zoomIndex = 1;
      evidenceViewer.classList.add("evidence-viewer--enhanced");

      const scrollToHighlight = () => {
        const page = pages[activePage];
        const firstHighlight = page.querySelector(".evidence-highlights rect");
        const y = firstHighlight instanceof SVGElement
          ? Number(firstHighlight.getAttribute("y"))
          : 0;
        pageContainer.scrollTop = Math.max(
          0,
          page.scrollHeight * Math.max(0, y - 0.12),
        );
        pageContainer.scrollLeft = 0;
      };

      const renderEvidencePage = ({ moveFocus = false } = {}) => {
        for (const [index, page] of pages.entries()) {
          page.hidden = index !== activePage;
        }
        previousButton.disabled = activePage === 0;
        nextButton.disabled = activePage === pages.length - 1;
        pageStatus.textContent = `Page ${activePage + 1} of ${pages.length}`;
        window.requestAnimationFrame(scrollToHighlight);
        if (moveFocus) pageContainer.focus();
      };

      const setPage = (index, moveFocus = false) => {
        activePage = Math.max(0, Math.min(index, pages.length - 1));
        renderEvidencePage({ moveFocus });
      };

      const setZoom = (index) => {
        zoomIndex = Math.max(0, Math.min(index, zoomLevels.length - 1));
        evidenceViewer.dataset.zoom = String(zoomLevels[zoomIndex]);
        zoomOutButton.disabled = zoomIndex === 0;
        zoomInButton.disabled = zoomIndex === zoomLevels.length - 1;
        window.requestAnimationFrame(scrollToHighlight);
      };

      previousButton.addEventListener("click", () => setPage(activePage - 1, true));
      nextButton.addEventListener("click", () => setPage(activePage + 1, true));
      fitButton.addEventListener("click", () => setZoom(1));
      zoomOutButton.addEventListener("click", () => setZoom(zoomIndex - 1));
      zoomInButton.addEventListener("click", () => setZoom(zoomIndex + 1));
      pageContainer.addEventListener("keydown", (event) => {
        if (["ArrowRight", "PageDown"].includes(event.key)) {
          setPage(activePage + 1);
        } else if (["ArrowLeft", "PageUp"].includes(event.key)) {
          setPage(activePage - 1);
        } else if (event.key === "Home") {
          setPage(0);
        } else if (event.key === "End") {
          setPage(pages.length - 1);
        } else if (event.key === "+" || event.key === "=") {
          setZoom(zoomIndex + 1);
        } else if (event.key === "-") {
          setZoom(zoomIndex - 1);
        } else {
          return;
        }
        event.preventDefault();
      });

      renderEvidencePage();
      setZoom(1);
    }
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
