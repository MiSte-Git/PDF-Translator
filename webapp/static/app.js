"use strict";

/* webapp/static/app.js - Umbau auf lokaler Server + pywebview, siehe
 * Backlog.md 26.08.2026 und /root/.claude/plans/moonlit-humming-brook.md.
 *
 * Schritt 3: GET /api/config (Formular füllen) + POST /api/analyze
 * (Kostenschätzung anzeigen).
 * Schritt 5: das Bestätigungs-Gate Ende-zu-Ende - der Start-Button wird
 * erst nutzbar, nachdem /api/analyze erfolgreich war UND die Checkbox
 * "Analyse und Kostenschätzung geprüft" angehakt ist (mirrors
 * ui/app.py::_start_blocked_reason()); jede Formular-Änderung
 * entwertet eine vorhandene Analyse wieder (mirrors
 * ui/app.py::_invalidate_analysis(), an dieselben Feld-Änderungssignale
 * angehängt). POST /api/jobs startet den Lauf, GET .../status wird
 * gepollt, GET .../result zeigt das Ergebnis. Die serverseitige
 * Nachprüfung in webapp/job_bridge.py::start_job() gilt unabhängig
 * davon, ob hier überhaupt zuvor analysiert wurde - dieses Gate ist
 * Verteidigung in der Tiefe, keine alleinige Kontrolle.
 *
 * Schritt 6: läuft diese Seite in pywebview (webapp/__main__.py), stellt
 * es `window.pywebview.api.pick_images()`/`pick_output_dir()` bereit -
 * echte native OS-Dialoge, die die beiden Textfelder ersetzen (ein
 * `<input type="file">` kann im normalen Browser aus Sicherheitsgründen
 * keinen echten Dateisystempfad liefern, siehe webapp/__main__.py's
 * Api-Klasse). Feature-Erkennung statt Annahme: im normalen Browser
 * (python -m webapp.server) bleiben die Textfelder die einzige
 * Möglichkeit, `window.pywebview` existiert dort schlicht nicht.
 *
 * Schritt 7: das Ergebnis listet jedes Bild einzeln auf (Dateiname,
 * Statistik, ein Button, der GET /api/jobs/<id>/qa-report?file=... lädt
 * und den Bericht inline in einem <pre> ein-/ausblendet) statt nur die
 * aggregierte Zusammenfassung zu zeigen - siehe renderJobResultFiles().
 *
 * Schritt 8: jede Zeile mit korrigierbaren Regionen bekommt einen
 * "Übersetzung korrigieren"-Button (siehe runCorrectFile()) - startet
 * eine Korrektur-Runde in einem separaten Fenster/Tab
 * (image_translate_cli/review_server.py's eigene Seite, über
 * webapp/review_bridge.py nicht-blockierend gestartet) und pollt bis zum
 * Ergebnis, statt die Hauptseite währenddessen einzufrieren.
 *
 * Kein Framework/Build-Schritt, exakt wie image_translate_cli/review_server.py's
 * eigenes Frontend und wie im Plan festgehalten ("echte Dateien statt
 * Python-String" - aber weiterhin ohne Abhängigkeit).
 */

let catalogue = {};
let currentLanguage = "de";
let lastAnalysis = null; // null, or the last successful /api/analyze response
let activeJobId = null;
let pollTimer = null;
let lastJobResultFiles = []; // Schritt 8: re-rendered in place after a correction applies
let lastOutputDir = null; // Nachbesserung: Ziel für den "Ordner öffnen"-Button (siehe runOpenOutputFolder())

function t(key, fallback) {
  return catalogue[key] !== undefined ? catalogue[key] : (fallback !== undefined ? fallback : key);
}

async function loadCatalogue(language) {
  const response = await fetch(`i18n/${language}.json`);
  if (!response.ok) {
    throw new Error(`i18n/${language}.json: HTTP ${response.status}`);
  }
  catalogue = await response.json();
  currentLanguage = language;
  applyCatalogue();
}

function applyCatalogue() {
  document.documentElement.lang = currentLanguage;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.getAttribute("data-i18n"), el.textContent);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder"), el.getAttribute("placeholder") || ""));
  });
}

/* Formatiert Python-artige Platzhalter wie "{characters:,}" oder
 * "{cost:.2f}" innerhalb der aus ui/i18n_data.py exportierten
 * Vorlagen-Strings (analysis.summary etc.) - die Vorlagen selbst
 * enthalten diese Format-Spezifikationen wörtlich als Text, siehe
 * webapp/tools/export_i18n.py. Absichtlich IMMER Komma als
 * Tausendertrennzeichen (nicht lokal-abhängig) - deckungsgleich mit
 * Pythons eigenem Standardverhalten für f"{value:,}", das die
 * bestehende Qt-App auch deutschen Nutzern bereits so anzeigt. */
function formatTemplate(template, values) {
  return template.replace(/\{(\w+)(:[^}]+)?\}/g, (match, key, specWithColon) => {
    if (!(key in values) || values[key] === null || values[key] === undefined) {
      return "";
    }
    const value = values[key];
    const spec = specWithColon ? specWithColon.slice(1) : null;
    if (spec === ",") {
      return Number(value).toLocaleString("en-US");
    }
    const floatMatch = spec && spec.match(/^\.(\d+)f$/);
    if (floatMatch) {
      return Number(value).toFixed(Number(floatMatch[1]));
    }
    return String(value);
  });
}

function setOptions(select, entries, availability, hintEl) {
  select.innerHTML = "";
  entries.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = t(`${select.dataset.i18nPrefix}.${name}`, name);
    if (availability && availability[name] === false) {
      option.disabled = true;
      option.textContent += ` (${t("ocr_engine.unavailable", "nicht verfügbar")})`;
    }
    select.appendChild(option);
  });
  if (hintEl) {
    select.addEventListener("change", () => updateAvailabilityHint(select, availability, hintEl));
    updateAvailabilityHint(select, availability, hintEl);
  }
}

function updateAvailabilityHint(select, availability, hintEl) {
  const current = select.value;
  if (availability && availability[current] === false) {
    const key = `${select.dataset.i18nPrefix}.${current}.unavailable`;
    hintEl.textContent = t(key, t(`${select.dataset.i18nPrefix}.unavailable`, ""));
  } else {
    hintEl.textContent = "";
  }
}

async function loadConfig() {
  const response = await fetch("/api/config");
  const config = await response.json();

  const providerSelect = document.getElementById("provider");
  providerSelect.dataset.i18nPrefix = "field.provider"; // no per-provider i18n keys today - fall back to the raw name
  providerSelect.innerHTML = "";
  config.providers.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    const status = t(config.provider_credential_status[name], config.provider_credential_status[name]);
    option.textContent = `${name} (${status})`;
    providerSelect.appendChild(option);
  });

  const ocrSelect = document.getElementById("ocr-engine");
  ocrSelect.dataset.i18nPrefix = "ocr_engine";
  setOptions(ocrSelect, config.ocr_engines, config.ocr_engine_available, document.getElementById("ocr-engine-hint"));

  const inpaintingSelect = document.getElementById("inpainting-backend");
  inpaintingSelect.dataset.i18nPrefix = "inpainting_backend";
  setOptions(
    inpaintingSelect,
    config.inpainting_backends,
    config.inpainting_backend_available,
    document.getElementById("inpainting-backend-hint")
  );

  // Zuletzt gespeicherten Formular-Stand vorbelegen (webapp/settings_store.py) -
  // dieselbe "nicht erneut eintippen müssen"-Absicht wie ui/app.py's
  // QSettings-Restore.
  const saved = config.last_form_state || {};
  if (saved.provider) providerSelect.value = saved.provider;
  const form = saved.form || {};
  if (form.source_lang) document.getElementById("source-language").value = form.source_lang;
  if (form.target_lang) document.getElementById("target-language").value = form.target_lang;
  if (form.protected_terms) document.getElementById("protected-terms").value = form.protected_terms;
  if (form.ocr_engine) ocrSelect.value = form.ocr_engine;
  if (form.inpainting_backend) inpaintingSelect.value = form.inpainting_backend;
  // 27.08.2026 - real user report, Backlog.md 27.08.2026: "Der
  // Zielordner wird nicht gespeichert." webapp/job_bridge.py::start_job()
  // has always SAVED last_output_dir (see its own 27.08.2026 comment -
  // the same fix that made source_lang/target_lang/etc. above survive a
  // restart), and build_config() has always returned it right here in
  // `saved` - this loop above just never read it back into the
  // #output-dir field, the one part of "last_form_state" this function
  // silently dropped on the floor.
  if (saved.last_output_dir) document.getElementById("output-dir").value = saved.last_output_dir;
  updateAvailabilityHint(ocrSelect, config.ocr_engine_available, document.getElementById("ocr-engine-hint"));
  updateAvailabilityHint(inpaintingSelect, config.inpainting_backend_available, document.getElementById("inpainting-backend-hint"));
}

function gatherRequestBody() {
  const sourcePaths = document
    .getElementById("source-paths")
    .value.split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  const protectedTerms = document
    .getElementById("protected-terms")
    .value.split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  return {
    source_paths: sourcePaths,
    provider: document.getElementById("provider").value,
    source_language: document.getElementById("source-language").value.trim() || null,
    target_language: document.getElementById("target-language").value.trim() || "DE",
    protected_terms: protectedTerms,
    ocr_engine: document.getElementById("ocr-engine").value,
    inpainting_backend: document.getElementById("inpainting-backend").value,
  };
}

function renderAnalysisResult(result) {
  const resultEl = document.getElementById("analysis-result");
  const summaryEl = document.getElementById("analysis-summary");
  const warningsEl = document.getElementById("analysis-warnings");
  const statusEl = document.getElementById("analysis-status");
  const checkbox = document.getElementById("confirm-checkbox");
  warningsEl.innerHTML = "";

  if (!result.ok) {
    resultEl.classList.add("hidden");
    statusEl.textContent = `${t("analysis.failed", "Analyse fehlgeschlagen.")} ${result.errors.join(" ")}`;
    // Mirrors ui/app.py::_analysis_failed(): a failed re-analysis leaves
    // any PREVIOUS successful analysis (lastAnalysis) untouched - only a
    // form-field change (invalidateAnalysis()) or a SUCCESSFUL analyze
    // clears it. updateStartState() re-reads whatever lastAnalysis
    // already is.
    updateStartState();
    return;
  }

  const cost = result.cost;
  const limitState = cost.within_run_limit
    ? t("analysis.within", "innerhalb")
    : t("analysis.exceeded", "ÜBERSCHRITTEN");
  const warningsText = result.warnings.length
    ? result.warnings.map((key) => t(key, key)).join(" ")
    : t("analysis.no_warnings", "Keine Analysewarnungen.");

  summaryEl.innerHTML = formatTemplate(t("analysis.summary"), {
    units: result.units,
    unit_label: t(result.unit_label, result.unit_label),
    characters: result.text_characters,
    images: result.embedded_images,
    provider: cost.provider,
    usage: cost.month_usage,
    free: cost.free_tier,
    cost: cost.estimated_cost_usd,
    limit: cost.max_chars_per_run,
    limit_state: limitState,
    warnings: warningsText,
  });

  if (cost.live_usage_available) {
    const li = document.createElement("li");
    if (cost.live_character_limit === null) {
      li.innerHTML = formatTemplate(t("analysis.live_quota_unlimited"), { used: cost.live_characters_used });
    } else {
      li.innerHTML = formatTemplate(t("analysis.live_quota"), {
        used: cost.live_characters_used,
        limit: cost.live_character_limit,
        remaining: cost.live_character_limit - cost.live_characters_used,
      });
    }
    warningsEl.appendChild(li);
  }

  resultEl.classList.remove("hidden");
  statusEl.textContent = "";

  lastAnalysis = result;
  // Mirrors ui/app.py::_analysis_finished(): the confirm checkbox is only
  // enabled when the estimated run stays within max_chars_per_run - an
  // over-limit analysis can be SEEN but not confirmed/started from here.
  checkbox.checked = false;
  checkbox.disabled = !cost.within_run_limit;
  updateStartState();
}

/* Entwertet eine vorhandene Analyse - mirrors
 * ui/app.py::_invalidate_analysis(), an dieselben Signale angehängt wie
 * dort (jede relevante Formular-Änderung). Ohne das könnte der
 * Start-Button mit einer Kostenschätzung für ein längst geändertes
 * Formular losgeschickt werden. */
function invalidateAnalysis() {
  lastAnalysis = null;
  const checkbox = document.getElementById("confirm-checkbox");
  checkbox.checked = false;
  checkbox.disabled = true;
  document.getElementById("analysis-result").classList.add("hidden");
  document.getElementById("analysis-status").textContent = "";
  updateStartState();
}

/* Mirrors ui/app.py::_start_blocked_reason() - exactly one reason is
 * shown at a time, in the same priority order. */
function updateStartState() {
  const startButton = document.getElementById("start-button");
  const startStatus = document.getElementById("start-status");
  const checkbox = document.getElementById("confirm-checkbox");

  let reasonKey = null;
  if (activeJobId !== null) {
    reasonKey = "start.blocked_running";
  } else if (!lastAnalysis) {
    reasonKey = "start.blocked_no_analysis";
  } else if (!checkbox.checked) {
    reasonKey = "start.blocked_not_confirmed";
  }

  startButton.disabled = reasonKey !== null;
  startStatus.textContent = reasonKey ? t(reasonKey) : t("start.ready", "Bereit zum Start.");
}

async function runAnalysis() {
  const statusEl = document.getElementById("analysis-status");
  const button = document.getElementById("analyze-button");
  button.disabled = true;
  statusEl.textContent = t("analysis.running", "Analyse läuft …");
  document.getElementById("analysis-result").classList.add("hidden");
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(gatherRequestBody()),
    });
    const result = await response.json();
    renderAnalysisResult(result);
  } catch (error) {
    statusEl.textContent = `${t("analysis.failed", "Analyse fehlgeschlagen.")} ${error}`;
  } finally {
    button.disabled = false;
  }
}

async function runStart() {
  if (!lastAnalysis) return;
  const outputDir = document.getElementById("output-dir").value.trim();
  const startStatus = document.getElementById("start-status");
  if (!outputDir) {
    startStatus.textContent = "Zielordner fehlt.";
    return;
  }

  const cost = lastAnalysis.cost;
  const sourceCount = document
    .getElementById("source-paths")
    .value.split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0).length;
  const summary = formatTemplate(t("start.confirm_summary_images"), {
    characters: cost.characters,
    provider: cost.provider,
    cost: cost.estimated_cost_usd,
    count: sourceCount,
    folder: outputDir,
  });
  // window.confirm() - a plain native dialog is enough for this
  // browser-only interim step (pywebview's own window.confirm() also
  // maps to a native dialog once Schritt 6 lands, so no rewrite needed
  // there); mirrors ui/app.py::_start()'s QMessageBox.question() gate.
  if (!window.confirm(summary)) return;

  const body = { ...gatherRequestBody(), output_dir: outputDir };
  document.getElementById("job-result").classList.add("hidden");
  startStatus.textContent = t("job.running", "Übersetzung läuft …");

  let response;
  try {
    response = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (error) {
    startStatus.textContent = String(error);
    return;
  }
  const result = await response.json();
  if (!result.ok) {
    startStatus.textContent = result.errors.join(" ");
    updateStartState();
    return;
  }

  activeJobId = result.job_id;
  document.getElementById("cancel-button").classList.remove("hidden");
  // Realer Nutzer-Feedback (26.08.2026): "Was fehlt ist eine
  // Fortschrittsanzeige. Ich sehe nur in der Shell dass etwas passiert."
  // Kein value-Attribut gesetzt/entfernt hier - das <progress>-Element
  // bleibt ohne "value" schon durch index.html unbestimmt/animiert,
  // dieser Aufruf blendet es nur ein.
  document.getElementById("job-progress-bar").classList.remove("hidden");
  updateStartState();
  pollJobStatus();
}

function renderJobProgress(status) {
  const progressText = formatTemplate(t("job.progress_count_files"), {
    processed: status.files_processed,
    total: status.files_total,
  });
  const detail = status.progress_message
    ? formatTemplate(t("job.progress_prefix"), { location: status.progress_message })
    : "";
  document.getElementById("start-status").textContent = [t("job.running"), progressText, detail]
    .filter((part) => part)
    .join(" — ");
}

function pollJobStatus() {
  if (pollTimer) clearInterval(pollTimer);
  // 800ms - within the plan's stated 750ms-1s polling interval (see
  // /root/.claude/plans/moonlit-humming-brook.md's "Polling statt
  // SSE/WebSockets"-Entscheidung).
  pollTimer = setInterval(async () => {
    if (!activeJobId) return;
    const jobId = activeJobId;
    let response;
    try {
      response = await fetch(`/api/jobs/${jobId}/status`);
    } catch (error) {
      return; // transient network hiccup - try again on the next tick
    }
    const status = await response.json();
    if (!status.ok) return;
    renderJobProgress(status);
    if (status.status !== "running") {
      clearInterval(pollTimer);
      pollTimer = null;
      await finishJob(jobId, status);
    }
  }, 800);
}

async function finishJob(jobId, status) {
  activeJobId = null;
  document.getElementById("cancel-button").classList.add("hidden");
  document.getElementById("job-progress-bar").classList.add("hidden");
  const startStatus = document.getElementById("start-status");

  if (status.status === "failed") {
    startStatus.textContent = `${t("job.failed_title", "Übersetzung fehlgeschlagen")}: ${status.error || ""}`;
  } else {
    const response = await fetch(`/api/jobs/${jobId}/result`);
    const result = await response.json();
    if (result.ok) {
      renderJobResult(result, status.status === "cancelled", jobId);
    } else {
      startStatus.textContent = result.errors.join(" ");
    }
  }

  // Jeder abgeschlossene Lauf (erfolgreich, abgebrochen oder
  // fehlgeschlagen) verlangt vor dem nächsten Start wieder eine frische
  // Analyse + Bestätigung - dasselbe Leitprinzip wie bei jeder
  // Formular-Änderung, nur hier durch den Lauf selbst ausgelöst statt
  // durch eine Eingabe.
  invalidateAnalysis();
}

function renderJobResult(result, wasCancelled, jobId) {
  const translated = result.files.reduce((sum, file) => sum + file.translated, 0);
  const failed = result.files.reduce((sum, file) => sum + file.failed, 0);
  const chars = result.files.reduce((sum, file) => sum + file.chars_sent, 0);
  let text = formatTemplate(t("job.result_summary_images"), {
    files: result.files.length,
    translated,
    failed,
    chars,
    output_dir: result.output_dir,
  });
  if (wasCancelled) {
    text += t("job.result_cancelled_suffix", "");
  }
  document.getElementById("job-result-summary").textContent = text;
  lastJobResultFiles = result.files;
  lastOutputDir = result.output_dir;
  renderJobResultFiles(lastJobResultFiles, jobId);
  document.getElementById("job-result").classList.remove("hidden");
}

/* "Ordner öffnen"-Button (realer Nutzer-Feedback 26.08.2026: "Es fehlt
 * auch noch ein Button um den Zielordner ... zu öffnen.") - nur unter
 * pywebview sichtbar (siehe enableNativeDialogs()), ruft
 * webapp/__main__.py::Api.open_folder() über die JS-Bridge auf. */
async function runOpenOutputFolder() {
  if (!lastOutputDir) return;
  const statusEl = document.getElementById("start-status");
  const ok = await window.pywebview.api.open_folder(lastOutputDir);
  if (!ok) {
    statusEl.textContent = t("job.open_folder_failed", "Ordner konnte nicht geöffnet werden.");
  }
}

/* Schritt 7: eine Zeile pro Bild mit einem Button, der dessen eigenen
 * QA-Bericht per GET /api/jobs/<id>/qa-report?file=... inline lädt und
 * ein-/ausblendet - siehe webapp/job_bridge.py::job_qa_report()'s
 * Docstring dazu, warum das der Bild-Modus-eigene Ersatz für
 * ui/app.py's QDesktopServices-basiertes "QA-Bericht öffnen" ist (das es
 * für den Bild-Modus in der Qt-App gar nicht gibt - dort nur "Ordner
 * öffnen", ohne Web-Äquivalent hier). Der Bericht wird höchstens einmal
 * pro Bild geladen (loaded-Flag) - erneutes Ein-/Ausblenden braucht dann
 * keinen weiteren Request mehr. */
function renderJobResultFiles(files, jobId) {
  const filesEl = document.getElementById("job-result-files");
  filesEl.innerHTML = "";
  files.forEach((file, fileIndex) => {
    const li = document.createElement("li");
    li.className = "job-result-file";

    const nameEl = document.createElement("div");
    // Nur der Dateiname - der Ausgabeordner steht bereits einmal in der
    // Zusammenfassung oben, ihn hier pro Zeile zu wiederholen wäre nur
    // Rauschen. Trennzeichen bewusst sowohl "/" als auch "\" (Quellpfade
    // können von einem Windows-Gerät stammen, auch wenn dieser Server
    // hier unter Linux läuft).
    const baseName = file.source.split(/[\\/]/).pop();
    nameEl.textContent = baseName;
    li.appendChild(nameEl);

    const statsEl = document.createElement("span");
    statsEl.className = "hint";
    statsEl.textContent = formatTemplate(t("job.stats_summary"), {
      translated: file.translated,
      skipped: file.skipped,
      failed: file.failed,
      chars: file.chars_sent,
    });
    li.appendChild(statsEl);

    const reportButton = document.createElement("button");
    reportButton.type = "button";
    reportButton.textContent = t("job.show_report");

    const reportPre = document.createElement("pre");
    reportPre.className = "qa-report hidden";

    let loaded = false;
    reportButton.addEventListener("click", async () => {
      const isHidden = reportPre.classList.contains("hidden");
      if (!isHidden) {
        reportPre.classList.add("hidden");
        reportButton.textContent = t("job.show_report");
        return;
      }
      if (!loaded) {
        reportButton.disabled = true;
        try {
          const response = await fetch(
            `/api/jobs/${jobId}/qa-report?file=${encodeURIComponent(file.qa_report)}`
          );
          const data = await response.json();
          if (data.ok) {
            reportPre.textContent = data.text;
            loaded = true;
          } else {
            reportPre.textContent = `${t("job.report_load_error")} ${(data.errors || []).join(" ")}`;
          }
        } catch (error) {
          reportPre.textContent = `${t("job.report_load_error")} ${error}`;
        } finally {
          reportButton.disabled = false;
        }
      }
      reportPre.classList.remove("hidden");
      reportButton.textContent = t("job.hide_report");
    });

    li.appendChild(reportButton);
    li.appendChild(reportPre);

    // Schritt 8: nur anbieten, wenn dieses Bild tatsächlich korrigierbare
    // Regionen hat - mirrors ui/app.py::_show_job_result()'s identische
    // Bedingung fürs Einblenden des "Übersetzung korrigieren"-Buttons.
    if (file.has_correctable_regions) {
      const correctButton = document.createElement("button");
      correctButton.type = "button";
      correctButton.textContent = t("job.correct_translation");

      const correctionStatusEl = document.createElement("p");
      // "correction-status" (not just "hint", which #statsEl above also
      // uses) so the re-render below can find THIS specific element again
      // after rebuilding the row from scratch.
      correctionStatusEl.className = "hint correction-status";

      correctButton.addEventListener("click", () =>
        runCorrectFile(jobId, fileIndex, correctButton, correctionStatusEl)
      );

      li.appendChild(correctButton);
      li.appendChild(correctionStatusEl);
    }

    filesEl.appendChild(li);
  });
}

/* Schritt 8: startet eine Korrektur-Runde für EIN Bild
 * (POST /api/jobs/<id>/files/<index>/correct, siehe
 * webapp/review_bridge.py), öffnet die zurückgegebene URL in einem neuen
 * Fenster/Tab (window.open() - in pywebview mit Qt-Backend empirisch als
 * eigenes natives Fenster bestätigt, siehe Backlog.md 26.08.2026s
 * Schritt-8-Eintrag) und pollt GET /api/corrections/<id>/status (dieselbe
 * "Polling statt Push"-Entscheidung wie bei /api/jobs/<id>/status) bis
 * der Mensch dort "Anwenden"/"Abbrechen" geklickt hat oder die
 * Zeitüberschreitung erreicht ist. Bei "applied" wird die komplette
 * Dateiliste neu gerendert (renderJobResultFiles()) statt nur einzelner
 * DOM-Knoten - baut dabei automatisch einen frischen QA-Bericht-Button
 * (loaded=false) auf, statt den alten, jetzt veralteten Berichtstext
 * weiter anzuzeigen. */
async function runCorrectFile(jobId, fileIndex, button, statusEl) {
  button.disabled = true;
  statusEl.textContent = t("job.correction_starting", "Korrektur wird gestartet …");

  let response;
  try {
    response = await fetch(`/api/jobs/${jobId}/files/${fileIndex}/correct`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
  } catch (error) {
    statusEl.textContent = `${t("job.correction_error")} ${error}`;
    button.disabled = false;
    return;
  }
  const result = await response.json();
  if (!result.ok) {
    statusEl.textContent = (result.errors || []).join(" ") || t("job.correction_error");
    button.disabled = false;
    return;
  }

  statusEl.textContent = t("job.correction_opened");
  window.open(result.url);

  const correctionPollTimer = setInterval(async () => {
    let statusResponse;
    try {
      statusResponse = await fetch(`/api/corrections/${result.correction_id}/status`);
    } catch (error) {
      return; // transient network hiccup - try again on the next tick
    }
    const statusPayload = await statusResponse.json();
    if (!statusPayload.ok || statusPayload.status === "pending") return;

    clearInterval(correctionPollTimer);
    button.disabled = false;

    if (statusPayload.status === "applied") {
      lastJobResultFiles[fileIndex] = statusPayload.file;
      renderJobResultFiles(lastJobResultFiles, jobId);
      // The row (and statusEl within it) was just rebuilt from scratch -
      // find the fresh element for this file to show the confirmation on,
      // rather than writing into the now-detached old `statusEl`.
      const filesEl = document.getElementById("job-result-files");
      const newRow = filesEl.children[fileIndex];
      const newStatusEl = newRow && newRow.querySelector(".correction-status");
      if (newStatusEl) newStatusEl.textContent = t("job.correction_applied");
    } else if (statusPayload.status === "cancelled") {
      statusEl.textContent = t("job.correction_cancelled");
    } else if (statusPayload.status === "timeout") {
      statusEl.textContent = t("job.correction_timeout");
    } else {
      statusEl.textContent = formatTemplate(t("job.correction_failed"), {
        error: (statusPayload.errors || []).join(" "),
      });
    }
  }, 1500);
}

async function runCancel() {
  if (!activeJobId) return;
  const button = document.getElementById("cancel-button");
  button.disabled = true;
  document.getElementById("start-status").textContent = t("job.cancel_requested");
  try {
    await fetch(`/api/jobs/${activeJobId}/cancel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
  } finally {
    button.disabled = false;
  }
}

/* Schritt 6 - läuft diese Seite in pywebview, ersetzt window.pywebview.api's
 * echte native Dialoge die beiden Textfeld-Provisorien. Aufgerufen sowohl
 * sofort (falls pywebview schon vor diesem Skript bereit war) als auch
 * über das "pywebviewready"-Event (der übliche, dokumentierte Weg, auf
 * die Bridge zu warten - sie ist nicht zwingend schon beim Laden der
 * Seite injiziert).
 */
function enableNativeDialogs() {
  document.getElementById("pick-images-button").classList.remove("hidden");
  document.getElementById("source-paths-hint").classList.add("hidden");
  document.getElementById("pick-output-dir-button").classList.remove("hidden");
  document.getElementById("output-dir-hint").classList.add("hidden");
  // Nur unter pywebview sinnvoll (Api.open_folder() ruft eine native
  // Bridge-Methode auf, die es im normalen Browser nicht gibt) - bleibt
  // dort dauerhaft eingeblendet, tatsächlich sichtbar wird der Button
  // aber erst zusätzlich, sobald #job-result selbst sichtbar ist.
  document.getElementById("open-output-folder-button").classList.remove("hidden");
}

async function runPickImages() {
  const selection = await window.pywebview.api.pick_images();
  if (!selection.length) return; // Dialog abgebrochen - Feld unverändert lassen
  document.getElementById("source-paths").value = selection.join("\n");
  // Programmatisches Setzen von .value löst kein "input"-Event aus - der
  // price-relevant-Feld-Listener unten würde sonst nie feuern.
  invalidateAnalysis();
}

async function runPickOutputDir() {
  const selection = await window.pywebview.api.pick_output_dir();
  if (!selection) return; // Dialog abgebrochen
  document.getElementById("output-dir").value = selection;
}

async function init() {
  await loadCatalogue(currentLanguage);
  await loadConfig();
  updateStartState();

  document.getElementById("language-select").value = currentLanguage;
  document.getElementById("language-select").addEventListener("change", async (event) => {
    await loadCatalogue(event.target.value);
    // Verfügbarkeits-Hinweise und dynamisch erzeugte Texte hängen an der
    // aktuellen Sprache - Config-getriebene Teile werden nach jedem
    // Sprachwechsel neu aufgebaut statt nur die statischen data-i18n-
    // Knoten zu aktualisieren.
    await loadConfig();
    updateStartState();
  });

  document.getElementById("analyze-button").addEventListener("click", runAnalysis);
  document.getElementById("confirm-checkbox").addEventListener("change", updateStartState);
  document.getElementById("start-button").addEventListener("click", runStart);
  document.getElementById("cancel-button").addEventListener("click", runCancel);
  document.getElementById("pick-images-button").addEventListener("click", runPickImages);
  document.getElementById("pick-output-dir-button").addEventListener("click", runPickOutputDir);
  document.getElementById("open-output-folder-button").addEventListener("click", runOpenOutputFolder);

  if (window.pywebview) {
    enableNativeDialogs();
  } else {
    window.addEventListener("pywebviewready", enableNativeDialogs);
  }

  // Jede Änderung an einem preisrelevanten Feld entwertet eine
  // vorhandene Analyse - mirrors ui/app.py's _invalidate_analysis()-
  // Verdrahtung an dieselben Felder. "output-dir" ist bewusst NICHT
  // dabei: der Zielordner fließt nicht in die Kostenschätzung ein.
  const priceRelevantFieldIds = [
    "source-paths",
    "provider",
    "source-language",
    "target-language",
    "protected-terms",
    "ocr-engine",
    "inpainting-backend",
  ];
  priceRelevantFieldIds.forEach((id) => {
    const el = document.getElementById(id);
    const eventName = el.tagName === "SELECT" ? "change" : "input";
    el.addEventListener(eventName, invalidateAnalysis);
  });
}

init();
