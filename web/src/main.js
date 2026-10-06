import {
  DEFAULT_CONFIG, normalizeConfig, parseCsv, prepareGovRows, buildGovPreview, parseOverpass, matchRecords,
  mergeTags, osmXml, govNoCoordCsv, nominatimQueryForRow, nominatimDebugUrl, geocodeUnmatchedAfterStages,
} from "./core.js";
import { createSessionZip, readSessionZip } from "./session.js";
import { loadSession, saveSession } from "./persistence.js";
import "./style.css";

const app = document.querySelector("#app");
const clone = (value) => structuredClone(value);
const state = {
  config: clone(DEFAULT_CONFIG), csvText: "", osmText: "", govRows: [], osmRows: [],
  results: null, manual: {}, page: "csv", status: "Gotowy do pracy", busy: false,
  csvFileName: "", osmFileName: "", csvErrors: [], abortController: null,
};
let previewRefreshTimer = null;
let previewSaveTimer = null;

const steps = [
  ["csv", "Dane GOV", "01"],
  ["osm", "Dane OSM", "02"],
  ["rules", "Reguły", "03"],
  ["review", "Dopasowania", "04"],
  ["export", "Eksport", "05"],
];

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

function notify(message, error = false) {
  state.status = message;
  const status = document.querySelector("[data-status]");
  if (status) {
    status.textContent = message;
    status.classList.toggle("is-error", error);
  }
}

function persist() {
  saveSession({
    config: state.config, csvText: state.csvText, osmText: state.osmText,
    csvFileName: state.csvFileName, osmFileName: state.osmFileName,
    manual: state.manual,
  }).catch(() => notify("Nie udało się zapisać sesji w tej przeglądarce.", true));
}

function render() {
  app.innerHTML = `
    <header class="topbar">
      <a class="wordmark" href="#csv" aria-label="GOV i OSM merger">
        <span class="wordmark-mark"><span></span><span></span></span>
        <span>GOV <i>×</i> OSM<small>MERGER / BROWSER EDITION</small></span>
      </a>
      <div class="top-actions">
        <span class="privacy"><span class="privacy-dot"></span>Przetwarzanie lokalne</span>
        <input id="zip-input" type="file" accept=".zip" hidden />
        <button class="icon-button" data-action="open-zip" title="Otwórz pakiet sesji" aria-label="Otwórz pakiet sesji">↥</button>
        <button class="icon-button" data-action="save-zip" title="Zapisz pakiet sesji" aria-label="Zapisz pakiet sesji">↧</button>
      </div>
    </header>
    <div class="app-frame">
      <aside class="sidebar">
        <div class="side-label">PROJEKT</div>
        <label class="project-label" for="project-name">Nazwa sesji</label>
        <input class="project-input" id="project-name" value="${escapeHtml(state.config.name)}" placeholder="np. Biblioteki Łódź" />
        <div class="side-label workflow-label">PRZEPŁYW PRACY</div>
        <nav class="step-nav" aria-label="Etapy pracy">
          ${steps.map(([id, title, number]) => `<button class="step-link ${state.page === id ? "is-active" : ""} ${stepReady(id) ? "is-ready" : ""}" data-page="${id}"><span class="step-number">${number}</span><span>${title}</span>${stepReady(id) ? '<span class="step-check">✓</span>' : ""}</button>`).join("")}
        </nav>
        <div class="side-bottom">
          <div class="save-indicator"><span class="save-dot"></span>Sesja zapisywana lokalnie</div>
          <p>Dane zostają w tej przeglądarce. Pakiet projektu zawiera kopię CSV i OSM.</p>
        </div>
      </aside>
      <main class="main-panel">
        <div class="status-line"><span class="status-indicator"></span><span data-status>${escapeHtml(state.status)}</span><span class="status-right">${state.csvFileName ? escapeHtml(state.csvFileName) : "BRAK CSV"}</span></div>
        ${state.busy ? `<div class="busy-overlay" aria-live="polite"><div class="busy-panel"><span class="busy-spinner"></span><strong>Trwa dopasowanie rekordów</strong><small>To może chwilę potrwać — nie zamykaj okna.</small></div></div>` : ""}
        <section class="workspace">${renderPage()}</section>
      </main>
    </div>
    <div class="toast" aria-live="polite"></div>
  `;
  wireEvents();
}

function stepReady(id) {
  return id === "csv" ? state.govRows.length > 0 : id === "osm" ? state.osmRows.length > 0 : id === "review" || id === "export" ? Boolean(state.results) : id === "rules" && (state.govRows.length > 0 || state.osmRows.length > 0);
}

function renderPage() {
  if (state.page === "csv") return renderCsvPage();
  if (state.page === "osm") return renderOsmPage();
  if (state.page === "rules") return renderRulesPage();
  if (state.page === "review") return renderReviewPage();
  return renderExportPage();
}

function pageHeading(eyebrow, title, detail) {
  return `<div class="page-heading"><div><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p class="page-detail">${detail}</p></div><div class="heading-mark">${state.page === "csv" ? "01" : state.page === "osm" ? "02" : state.page === "rules" ? "03" : state.page === "review" ? "04" : "05"}</div></div>`;
}

function renderCsvPage() {
  const headers = state.csvText ? safeHeaders() : [];
  const mapping = state.config.csv.mapping;
  const suggestions = ["name", "addr:street", "addr:housenumber", "addr:city", "addr:place", "addr:postcode", "email", "phone", "website", "__lat", "__lon"];
  const tags = Object.keys(mapping);
  const fieldRows = (tags.length ? tags : suggestions).map((tag) => {
    const rule = mapping[tag] ?? "";
    const isConcat = rule?.type === "concat";
    const isAddress = rule?.type === "address";
    const sourceColumns = isConcat ? rule.columns ?? [] : typeof rule === "string" ? [rule] : [];
    const addressField = (fieldName) => {
      const config = isAddress ? normalizeAddressField(rule?.[fieldName]) : normalizeAddressField("");
      const selectedColumn = config.column;
      const selectedRegexIn = config.regexIn;
      const selectedRegexOut = config.regexOut;
      return `
        <label class="address-field">
          <span class="address-tag-key">${addressTagKey(fieldName)}</span>
          <select data-address-source="${fieldName}" data-map-address="${escapeHtml(tag)}" aria-label="Kolumna dla addr:${fieldName}">
            <option value="">--</option>
            ${headers.map((header) => `<option value="${escapeHtml(header)}" ${selectedColumn === header ? "selected" : ""}>${escapeHtml(header)}</option>`).join("")}
          </select>
          <input data-address-regex-in="${fieldName}" data-map-address="${escapeHtml(tag)}" value="${escapeHtml(selectedRegexIn)}" placeholder="regex in" aria-label="Regex wejściowy dla ${addressTagKey(fieldName)}" />
          <input data-address-regex-out="${fieldName}" data-map-address="${escapeHtml(tag)}" value="${escapeHtml(selectedRegexOut)}" placeholder="$1" aria-label="Regex wyjściowy dla ${addressTagKey(fieldName)}" title="Regex flags: i, m" />
          <span class="address-regex-flags" title="Regex flags: i oraz m">im</span>
        </label>`;
    };
    const tagDisplay = isAddress
      ? `<div class="address-tag-preview">${["city", "street", "housenumber", "postcode", "place"].map((fieldName) => `<small>${addressTagKey(fieldName)}</small>`).join("")}</div>`
      : `<input class="tag-name-input" data-map-tag="${escapeHtml(tag)}" value="${escapeHtml(tag)}" aria-label="Klucz tagu OSM"/>`;
    const sourceControl = isConcat
      ? `<div class="mapping-source-group"><select multiple data-map-source="${escapeHtml(tag)}" aria-label="Kolumny CSV do sklejenia">${headers.map((header) => `<option value="${escapeHtml(header)}" ${sourceColumns.includes(header) ? "selected" : ""}>${escapeHtml(header)}</option>`).join("")}</select><label class="separator-control">Separator<input data-map-separator="${escapeHtml(tag)}" value="${escapeHtml(rule.separator ?? " ")}" aria-label="Separator sklejanych kolumn"/></label></div>`
      : isAddress
        ? `<div class="mapping-source-group address-mapping-group">${["city", "street", "housenumber", "postcode", "place"].map((fieldName) => addressField(fieldName)).join("")}</div>`
        : `<select data-map-source="${escapeHtml(tag)}" aria-label="Kolumna CSV"><option value="">Nie mapuj</option>${headers.map((header) => `<option value="${escapeHtml(header)}" ${sourceColumns[0] === header ? "selected" : ""}>${escapeHtml(header)}</option>`).join("")}</select>`;
    return `<div class="mapping-row">${tagDisplay}${sourceControl}<select data-map-mode="${escapeHtml(tag)}" aria-label="Sposób mapowania"><option value="column" ${!isConcat && !isAddress ? "selected" : ""}>Kolumna</option><option value="concat" ${isConcat ? "selected" : ""}>Sklej kolumny</option><option value="address" ${isAddress ? "selected" : ""}>Adres</option></select><button class="tiny-button" data-action="remove-map" data-key="${escapeHtml(tag)}" title="Usuń mapowanie" aria-label="Usuń mapowanie">×</button></div>`;
  }).join("");
  const filters = (state.config.csv.filters ?? []).map((filter, index) => `<div class="filter-chip"><span>${escapeHtml(filter.column)} ${escapeHtml(filter.operator)} ${escapeHtml(filter.value ?? "")}</span><button class="tiny-button" data-action="remove-filter" data-index="${index}" title="Usuń filtr">×</button></div>`).join("");
  const transforms = (state.config.csv.transforms ?? []).map((transform, index) => renderTransform(transform, index, tags)).join("");
  return `${pageHeading("01 / ŹRÓDŁO URZĘDOWE", "Skonfiguruj dane GOV", "Wczytaj tabelę, przypisz kolumny do tagów i sprawdź próbkę po transformacji.")}
    <div class="content-grid">
      <div class="content-column">
        <section class="section-block">
          <div class="section-title"><div><span class="section-index">A</span><h2>Plik źródłowy</h2></div><span class="section-meta">CSV · UTF-8</span></div>
          <label class="drop-zone" for="csv-input"><span class="upload-icon">↑</span><strong>${state.csvFileName ? escapeHtml(state.csvFileName) : "Wybierz plik CSV"}</strong><small>${state.csvFileName ? `${state.govRows.length} wierszy przygotowanych` : "Przeciągnij plik albo kliknij, aby przeglądać"}</small><input id="csv-input" type="file" accept=".csv,text/csv" hidden /></label>
          <div class="inline-controls"><label>Separator<select id="csv-delimiter">${[[";", "Średnik ;"], [",", "Przecinek ,"], ["\\t", "Tabulator"]].map(([value, label]) => `<option value="${value}" ${state.config.csv.delimiter === (value === "\\t" ? "\t" : value) ? "selected" : ""}>${label}</option>`).join("")}</select></label><label>Znak cytowania<input id="csv-quote" maxlength="1" value="${escapeHtml(state.config.csv.quote)}" /></label><button class="button button-secondary" data-action="prepare-csv" ${state.csvText ? "" : "disabled"}>Przygotuj podgląd</button></div>
        </section>
        <section class="section-block mapping-block">
          <div class="section-title"><div><span class="section-index">B</span><h2>Mapowanie kolumn</h2></div><button class="text-button" data-action="add-map" ${headers.length ? "" : "disabled"}>＋ Dodaj tag</button></div>
          <p class="section-hint">Jednemu tagowi możesz przypisać pojedynczą kolumnę albo skleić kilka kolumn w jedną wartość.</p>
          <div class="mapping-header"><span>TAG OSM</span><span>KOLUMNA LUB KOLUMNY CSV</span><span>TRYB</span><span></span></div>
          <div class="mapping-list">${fieldRows}</div>
          ${filters ? `<div class="filter-chip-list">${filters}</div>` : ""}
          ${headers.length ? `<div class="filter-toolbar"><div><strong>Filtr wierszy</strong><small>Pomiń rekordy niespełniające warunku</small></div><select id="filter-column"><option value="">Kolumna</option>${headers.map((header) => `<option>${escapeHtml(header)}</option>`).join("")}</select><select id="filter-operator"><option value="equals">równa się</option><option value="not-equals">nie równa się</option><option value="contains">zawiera</option><option value="not-empty">niepusta</option></select><input id="filter-value" placeholder="wartość"/><button class="tiny-button" data-action="add-filter" title="Dodaj filtr">+</button></div>` : ""}
        </section>
        <section class="section-block preprocessing-block">
          <div class="section-title"><div><span class="section-index">C</span><h2>Preprocessing</h2></div><button class="text-button" data-action="add-transform" ${tags.length ? "" : "disabled"}>＋ Dodaj operację</button></div>
          <p class="section-hint">Operacje działają po kolei in-place na wartości zmapowanego tagu.</p>
          <div class="transform-list">${transforms || '<div class="empty-rule">Brak operacji. Mapowane wartości pozostaną bez zmian.</div>'}</div>
        </section>
      </div>
      <aside class="preview-rail gov-preview-rail"><div class="rail-title">PODGLĄD DANYCH</div><div data-gov-preview>${renderGovPreview()}</div><div class="rail-note"><span>i</span><p>Wynik pokazuje wszystkie kolumny CSV oraz tagi po mapowaniu i preprocessingu.</p></div><div data-gov-errors>${renderErrors()}</div></aside>
    </div>
    <div class="page-footer"><span class="step-caption">ETAP 1 Z 5</span><button class="button button-primary" data-page="osm">Dalej: dane OSM <span>→</span></button></div>`;
}

function safeHeaders() {
  try { return parseCsv(state.csvText, state.config.csv).headers; }
  catch { return Object.keys(state.govRows[0] ?? {}).filter((key) => key !== "__row"); }
}

function addressTagKey(fieldName) {
  return `addr:${fieldName}`;
}

function normalizeAddressField(field) {
  if (typeof field === "string") return { column: field, regexIn: "", regexOut: "$1", flags: "im" };
  const config = field ?? {};
  return {
    column: config.column ?? "",
    regexIn: config.regexIn ?? config.regex ?? "",
    regexOut: config.regexOut ?? "$1",
    flags: config.flags ?? config.regexFlags ?? "im",
  };
}

function renderGovPreview() {
  if (!state.csvText) return `<div class="empty-preview"><span>CSV</span><p>Podgląd pojawi się po wczytaniu pliku.</p></div>`;
  try {
    const sourceRows = parseCsv(state.csvText, state.config.csv);
    const preview = buildGovPreview(sourceRows, state.govRows, state.config);
    const maxRows = 8;
    const sourceRowsHtml = preview.rows.slice(0, maxRows).map(({ sourceRow, source }) =>
      `<tr><th class="row-number">${sourceRow}</th>${preview.sourceColumns.map((column) => `<td>${escapeHtml(source[column] ?? "") || '<span class="muted">—</span>'}</td>`).join("")}</tr>`
    ).join("");
    const outputRows = preview.rows.filter((row) => row.prepared).slice(0, maxRows);
    const outputRowsHtml = outputRows.map(({ sourceRow, prepared }) =>
      `<tr><th class="row-number">${sourceRow}</th>${preview.tagColumns.map((tag) => `<td class="output-cell">${escapeHtml(prepared.tags[tag] ?? "") || '<span class="muted">—</span>'}</td>`).join("")}</tr>`
    ).join("");
    const sourceTable = `<section class="gov-preview-block"><div class="gov-preview-heading"><strong>Dane źródłowe</strong><span>${sourceRows.length.toLocaleString("pl-PL")} wierszy · ${preview.sourceColumns.length} kolumn</span></div><div class="table-wrap preview-table"><table><thead><tr><th>WIERSZ</th>${preview.sourceColumns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr></thead><tbody>${sourceRowsHtml}</tbody></table></div>${preview.rows.length > maxRows ? `<small class="table-caption">Pokazano ${maxRows} z ${preview.rows.length} wierszy; przewiń poziomo po kolumnach.</small>` : ""}</section>`;
    const outputTable = `<section class="gov-preview-block"><div class="gov-preview-heading"><strong>Po mapowaniu i preprocessingu</strong><span>${state.govRows.length.toLocaleString("pl-PL")} wierszy · ${preview.tagColumns.length} tagów</span></div>${preview.tagColumns.length ? `<div class="table-wrap preview-table"><table><thead><tr><th>WIERSZ</th>${preview.tagColumns.map((tag) => `<th>${escapeHtml(tag)}</th>`).join("")}</tr></thead><tbody>${outputRowsHtml}</tbody></table></div>${state.govRows.length > maxRows ? `<small class="table-caption">Pokazano ${maxRows} z ${state.govRows.length} wierszy; przewiń poziomo po kolumnach.</small>` : ""}` : '<div class="empty-rule">Ustaw mapowanie kolumn, aby zobaczyć tagi wynikowe.</div>'}</section>`;
    return `<div class="gov-preview-stack">${sourceTable}${outputTable}</div>`;
  } catch (error) {
    return `<div class="empty-preview"><span>CSV</span><p>${escapeHtml(error.message)}</p></div>`;
  }
}

function renderErrors() {
  if (!state.csvErrors.length) return "";
  return `<div class="error-list"><strong>${state.csvErrors.length} wierszy pominiętych</strong>${state.csvErrors.slice(0, 4).map((item) => `<small>Wiersz ${item.row}: ${escapeHtml(item.message)}</small>`).join("")}</div>`;
}

function renderTransform(transform, index, tags) {
  const value = transform.type === "replace" ? `${transform.find ?? ""} → ${transform.replace ?? ""}` : transform.value ?? "";
  const target = `<select data-transform-key="${index}" aria-label="Tag do preprocessingu"><option value="">Wybierz tag</option>${tags.map((tag) => `<option value="${escapeHtml(tag)}" ${transform.key === tag ? "selected" : ""}>${escapeHtml(tag)}</option>`).join("")}</select>`;
  if (transform.type === "regex") return `<div class="transform-entry"><div class="transform-row"><select data-transform-type="${index}">${transformOptions(transform.type)}</select>${target}<input data-regex-pattern="${index}" value="${escapeHtml(transform.pattern ?? "")}" placeholder="Wzorzec regex" maxlength="256"/><button class="tiny-button" data-action="remove-transform" data-index="${index}" title="Usuń preprocessing">×</button></div><div class="regex-inline-fields"><label>Flaga<select data-regex-flags="${index}" aria-label="Flagi regex"><option value="" ${transform.flags ? "" : "selected"}>Brak</option><option value="i" ${transform.flags === "i" ? "selected" : ""}>Ignoruj wielkość liter</option></select></label><input data-regex-template="${index}" value="${escapeHtml(transform.template ?? "$1")}" placeholder="Szablon wyniku: $1 $2" aria-label="Szablon wyniku regex"/><small>Wynik zastąpi wartość wskazanego tagu.</small></div></div>`;
  if (transform.type === "trim") return `<div class="transform-row"><select data-transform-type="${index}">${transformOptions(transform.type)}</select>${target}<small class="transform-hint">Przytnij brzegi i zredukuj wielokrotne spacje.</small><button class="tiny-button" data-action="remove-transform" data-index="${index}" title="Usuń transformację">×</button></div>`;
  return `<div class="transform-row"><select data-transform-type="${index}">${transformOptions(transform.type)}</select>${target}<input data-transform-value="${index}" value="${escapeHtml(value)}" placeholder="wartość"/><button class="tiny-button" data-action="remove-transform" data-index="${index}" title="Usuń transformację">×</button></div>`;
}

function transformOptions(selected) {
  return `<option value="trim" ${selected === "trim" ? "selected" : ""}>Usuń zbędne spacje</option><option value="upper" ${selected === "upper" ? "selected" : ""}>Wielkie litery</option><option value="lower" ${selected === "lower" ? "selected" : ""}>Małe litery</option><option value="replace" ${selected === "replace" ? "selected" : ""}>Zastąp tekst</option><option value="prefix" ${selected === "prefix" ? "selected" : ""}>Dodaj prefiks</option><option value="suffix" ${selected === "suffix" ? "selected" : ""}>Dodaj sufiks</option><option value="regex" ${selected === "regex" ? "selected" : ""}>Regex · grupy</option>`;
}

function renderOsmPage() {
  return `${pageHeading("02 / ŹRÓDŁO MAPOWE", "Pobierz dane z OSM", "Wprowadź zapytanie Overpass QL lub wczytaj wcześniej pobrany wynik JSON.")}
    <div class="content-grid osm-grid"><div class="content-column">
      <section class="section-block"><div class="section-title"><div><span class="section-index">A</span><h2>Zapytanie Overpass</h2></div><span class="section-meta">QL / JSON</span></div>
        <label class="field-label" for="overpass-endpoint">Endpoint</label><input class="wide-input" id="overpass-endpoint" value="${escapeHtml(state.config.overpass.endpoint)}" />
        <label class="field-label query-label" for="overpass-query">Treść zapytania</label><textarea class="code-input" id="overpass-query" spellcheck="false" placeholder='[out:json][timeout:90];&#10;(node["amenity"="library"]({{bbox}}););&#10;out center tags;'>${escapeHtml(state.config.overpass.query)}</textarea>
        <div class="action-row"><button class="button button-primary" data-action="fetch-overpass" ${state.busy ? "disabled" : ""}>${state.busy ? "Pobieranie…" : "Uruchom zapytanie"} <span>↗</span></button>${state.busy ? '<button class="button button-secondary" data-action="cancel-request">Anuluj</button>' : ""}<span class="helper-text">Publiczne endpointy mogą ograniczać częstotliwość lub blokować CORS.</span></div>
      </section>
      <section class="section-block"><div class="section-title"><div><span class="section-index">B</span><h2>Albo wczytaj plik OSM</h2></div><span class="section-meta">OVERPASS JSON</span></div>
        <div class="osm-file-row"><label class="drop-zone compact-drop" for="osm-input"><span class="upload-icon">↑</span><strong>${state.osmFileName ? escapeHtml(state.osmFileName) : "Wybierz plik JSON"}</strong><small>${state.osmRows.length ? `${state.osmRows.length} węzłów i dróg` : "Odpowiedź Overpass API"}</small><input id="osm-input" type="file" accept=".json,.osm,application/json" hidden /></label>${state.osmText ? '<button class="button button-secondary remove-osm-button" data-action="remove-osm">Usuń plik OSM</button>' : ""}</div>
      </section>
    </div><aside class="preview-rail"><div class="rail-title">STAN OSM</div><div class="metric-block"><strong>${state.osmRows.length.toLocaleString("pl-PL")}</strong><span>obiektów wczytanych</span></div><div class="metric-pair"><div><b>${state.osmRows.filter((item) => item.type === "node").length}</b><span>węzły</span></div><div><b>${state.osmRows.filter((item) => item.type === "way").length}</b><span>drogi</span></div></div><div class="rail-note"><span>i</span><p>Obsługiwane są węzły i drogi z geometrią. Relacje OSM nie są częścią pierwszej wersji.</p></div></aside></div>
    <div class="page-footer"><button class="button button-secondary" data-page="csv">← Wróć</button><span class="step-caption">ETAP 2 Z 5</span><button class="button button-primary" data-page="rules">Dalej: reguły <span>→</span></button></div>`;
}

function renderRulesPage() {
  const stages = state.config.matching.stages;
  return `${pageHeading("03 / ZASADY ŁĄCZENIA", "Ustaw reguły i tagi", "Etapy działają po kolei. Jednoznaczne trafienie blokuje obiekt przed kolejnymi regułami.")}
    <div class="content-grid rules-grid"><div class="content-column">
      <section class="section-block"><div class="section-title"><div><span class="section-index">A</span><h2>Kolejność dopasowania</h2></div><span class="section-meta">UNIKALNE TRAFIENIE</span></div>
        <div class="stage-list">${stages.map((stage, index) => `<div class="stage-row ${stage.enabled ? "is-enabled" : ""}"><label class="toggle"><input type="checkbox" data-stage-enabled="${index}" ${stage.enabled ? "checked" : ""}><span></span></label><div class="stage-main"><strong>${escapeHtml(stage.label)}</strong><small>${stageDescription(stage)}</small></div><select class="stage-type-select" data-stage-type="${index}" aria-label="Typ reguły"><option value="name" ${stage.type === "name" ? "selected" : ""}>Nazwa</option><option value="address" ${stage.type === "address" ? "selected" : ""}>Adres</option><option value="tags" ${stage.type === "tags" ? "selected" : ""}>Tagi</option><option value="location" ${stage.type === "location" ? "selected" : ""}>Odległość</option></select>${stage.type === "location" ? `<label class="inline-number">Promień <input type="number" min="1" max="5000" data-stage-radius="${index}" value="${Number(stage.toleranceM ?? 100)}"> m</label>` : ""}${stage.type === "address" || stage.type === "tags" ? `<input class="stage-fields" data-stage-fields="${index}" value="${escapeHtml((stage.fields ?? []).join(", "))}" aria-label="Tagi dopasowania"/>` : ""}<div class="reorder"><button class="tiny-button" data-action="move-stage" data-index="${index}" data-delta="-1" ${index === 0 ? "disabled" : ""} title="Przesuń w górę">↑</button><button class="tiny-button" data-action="move-stage" data-index="${index}" data-delta="1" ${index === stages.length - 1 ? "disabled" : ""} title="Przesuń w dół">↓</button><button class="tiny-button danger-button" data-action="remove-stage" data-index="${index}" title="Usuń regułę">×</button></div></div>`).join("")}</div>
        <div class="stage-add-row"><button class="button button-secondary" data-action="add-stage">＋ Dodaj etap</button></div>
        <div class="choice-bar"><label><input type="checkbox" id="nominatim-enabled" ${state.config.nominatim.enabled ? "checked" : ""}><span>Uzupełnij brakujące współrzędne GOV przez Nominatim, gdy używana jest reguła odległości</span></label><small>Zapytania są wykonywane pojedynczo z przerwą zgodną z ograniczeniami usługi.</small></div>
      </section>
      <section class="section-block"><div class="section-title"><div><span class="section-index">B</span><h2>Scalanie tagów</h2></div><span class="section-meta">JAWNA POLITYKA KONFLIKTÓW</span></div>
        <div class="merge-policy"><label for="merge-policy">Gdy OSM i GOV mają już ten sam tag<select id="merge-policy"><option value="keep-osm" ${state.config.merge.conflict === "keep-osm" ? "selected" : ""}>Zachowaj wartość OSM</option><option value="keep-gov" ${state.config.merge.conflict === "keep-gov" ? "selected" : ""}>Nadpisz wartością GOV</option></select></label><label class="check-control"><input type="checkbox" id="update-address" ${state.config.merge.updateAddress ? "checked" : ""}> Aktualizuj istniejący adres OSM</label><label class="check-control"><input type="checkbox" id="add-address-when-missing" ${state.config.merge.addAddressWhenMissing ? "checked" : ""}> Dopisz adresy do miejsc, które ich nie miały</label></div>
        <div class="ops-header"><span>OPERACJA</span><span>KLUCZ TAGU</span><span>WARTOŚĆ / WZORZEC</span><span></span></div>
        <div class="operation-list">${(state.config.merge.operations ?? []).map((operation, index) => renderOperation(operation, index)).join("") || '<div class="empty-rule">Nie dodano jeszcze operacji.</div>'}</div>
        <div class="ops-actions"><button class="text-button" data-action="add-operation" data-type="delete">＋ Usuń tag</button><button class="text-button" data-action="add-operation" data-type="set">＋ Dodaj / ustaw</button><button class="text-button" data-action="add-operation" data-type="replace">＋ Zastąp tekst</button></div>
        <div class="source-tags"><label for="source-key">Klucz OSM<input id="source-key" value="${escapeHtml(state.config.merge.sourceKey ?? "source:office")}" placeholder="source:office" /></label><label for="source-description">Źródło do wypełnienia<input id="source-description" value="${escapeHtml(state.config.merge.source ?? "")}" placeholder="np. Rejestr placówek na dzień 2025-01-01" /></label></div>
      </section>
    </div><aside class="preview-rail"><div class="rail-title">REGUŁY AKTYWNE</div><div class="metric-block"><strong>${stages.filter((stage) => stage.enabled).length}</strong><span>etapów dopasowania</span></div><div class="rule-order">${stages.filter((stage) => stage.enabled).map((stage, index) => `<div><span>${String(index + 1).padStart(2, "0")}</span>${escapeHtml(stage.label)}</div>`).join("") || "<small>Włącz przynajmniej jeden etap.</small>"}</div><div class="rail-note warning-note"><span>!</span><p>Wieloznaczne trafienia pozostają niedopasowane. Sprawdź je ręcznie przed eksportem.</p></div></aside></div>
    <div class="page-footer"><button class="button button-secondary" data-page="osm">← Wróć</button><span class="step-caption">ETAP 3 Z 5</span><button class="button button-primary" data-action="run-match" ${state.busy || !state.govRows.length || !state.osmRows.length ? "disabled" : ""}>${state.busy ? "Przetwarzanie…" : "Dopasuj rekordy"}<span>→</span></button></div>`;
}

function stageDescription(stage) {
  if (stage.type === "name") return "Dokładna nazwa po normalizacji znaków i interpunkcji";
  if (stage.type === "address") return `Wszystkie podane pola adresowe muszą być zgodne: ${(stage.fields ?? []).join(" · ")}`;
  if (stage.type === "tags") return `Wymagana zgodność wartości tagów: ${(stage.fields ?? []).join(" · ")}`;
  return "Najbliższy obiekt w promieniu; tylko pojedynczy kandydat";
}

function renderOperation(operation, index) {
  const typeLabel = { delete: "Usuń", set: "Ustaw", replace: "Zastąp" }[operation.type] ?? operation.type;
  const value = operation.type === "replace" ? `${operation.find ?? ""} → ${operation.replace ?? ""}` : operation.value ?? "";
  return `<div class="operation-row"><select data-op-type="${index}"><option value="delete" ${operation.type === "delete" ? "selected" : ""}>Usuń</option><option value="set" ${operation.type === "set" ? "selected" : ""}>Dodaj / ustaw</option><option value="replace" ${operation.type === "replace" ? "selected" : ""}>Zastąp tekst</option></select><input data-op-key="${index}" value="${escapeHtml(operation.key)}" placeholder="np. amenity"/><input data-op-value="${index}" value="${escapeHtml(value)}" placeholder="* lub wartość"/><button class="tiny-button danger-button" data-action="remove-operation" data-index="${index}" aria-label="Usuń operację">×</button></div>`;
}

function currentResults() {
  if (!state.results) return null;
  const manualGovIds = new Set(Object.keys(state.manual).map(Number));
  const manualOsmKeys = new Set(Object.values(state.manual).filter(Boolean));
  const automatic = matchRecords(
    state.govRows.filter((row) => !manualGovIds.has(row.id)),
    state.osmRows.filter((row) => !manualOsmKeys.has(`${row.type}/${row.id}`)),
    state.config.matching.stages,
  );
  const manuallyMatched = Object.entries(state.manual).flatMap(([govId, osmId]) => {
    if (!osmId) return [];
    const gov = state.govRows.find((row) => row.id === Number(govId));
    const osm = state.osmRows.find((row) => `${row.type}/${row.id}` === osmId);
    return gov && osm ? [{ gov, osm, stage: "Ręczne" }] : [];
  });
  const matchedIds = new Set([...manualGovIds]);
  const manualOsm = new Set(manuallyMatched.map(({ osm }) => `${osm.type}/${osm.id}`));
  const manuallyUnmatched = state.govRows.filter((row) => Object.hasOwn(state.manual, row.id) && !state.manual[row.id]);
  return {
    ...automatic,
    matches: [...automatic.matches, ...manuallyMatched],
    unmatchedGov: [...automatic.unmatchedGov.filter((row) => !matchedIds.has(row.id)), ...manuallyUnmatched],
    unmatchedOsm: automatic.unmatchedOsm.filter((row) => !manualOsm.has(`${row.type}/${row.id}`)),
  };
}

function renderReviewPage() {
  const results = currentResults();
  if (!results) return `${pageHeading("04 / KONTROLA", "Wyniki dopasowania", "Najpierw skonfiguruj dane i uruchom dopasowanie.")}<div class="empty-state"><span>04</span><h2>Brak wyników</h2><p>Po uruchomieniu matcherów tutaj pojawią się kandydaci i rekordy wymagające kontroli.</p><button class="button button-primary" data-page="rules">Przejdź do reguł →</button></div>`;
  const mergeByOsm = new Map();
  const matchRows = results.matches.map((match) => {
    const merged = mergeTags(match.osm.tags, match.gov.tags, state.config.merge);
    const key = `${match.osm.type}/${match.osm.id}`;
    mergeByOsm.set(key, merged);
    return { ...match, merged, key };
  });
  const govKey = (item) => item.gov.tags.name || item.gov.tags["official_name"] || `Wiersz ${item.gov.sourceRow}`;
  return `${pageHeading("04 / KONTROLA", "Sprawdź dopasowania", "Zweryfikuj niejednoznaczne rekordy, przypisz ręcznie brakujące pary i sprawdź zmiany tagów.")}
    <div class="stats-grid"><div><strong>${matchRows.length}</strong><span>dopasowane</span></div><div><strong>${results.unmatchedGov.length}</strong><span>GOV bez OSM</span></div><div><strong>${results.ambiguous.length}</strong><span>niejednoznaczne</span></div><div><strong>${results.unmatchedOsm.length}</strong><span>OSM bez GOV</span></div></div>
    <div class="review-section"><div class="section-title"><div><span class="section-index">A</span><h2>Dopasowane pary</h2></div><span class="section-meta">${matchRows.length} PARA(Y)</span></div>
      ${matchRows.length ? `<div class="table-wrap"><table class="review-table"><thead><tr><th>GOV</th><th>OSM</th><th>REGUŁA</th><th>TAGI DO ZMIANY</th><th></th></tr></thead><tbody>${matchRows.map((item) => `<tr><td><strong>${escapeHtml(govKey(item))}</strong><small>${escapeHtml(formatAddress(item.gov.tags))}</small></td><td><strong>${escapeHtml(item.osm.tags.name ?? item.osm.tags.official_name ?? item.key)}</strong><small>${item.osm.type}/${item.osm.id} · ${escapeHtml(formatAddress(item.osm.tags))}</small></td><td><span class="rule-chip">${escapeHtml(item.stage)}</span></td><td>${Object.keys(item.merged.changed).length + item.merged.removed.length ? `<details class="tag-diff"><summary><span class="change-chip">${Object.keys(item.merged.changed).length} ustaw · ${item.merged.removed.length} usuń</span></summary>${renderTagDiff(item.merged)}</details>` : '<span class="muted">bez zmian</span>'}</td><td><button class="tiny-button danger-button" data-action="unlink" data-gov="${item.gov.id}" title="Odłącz dopasowanie">↶</button></td></tr>`).join("")}</tbody></table></div>` : '<div class="empty-rule">Nie znaleziono dopasowanych par.</div>'}
    </div>
    <div class="review-columns"><section class="review-section"><div class="section-title"><div><span class="section-index">B</span><h2>Niedopasowane GOV</h2></div><span class="section-meta">DO RĘCZNEJ DECYZJI</span></div>
      ${results.unmatchedGov.slice(0, 40).map((gov) => `<div class="manual-row"><div><strong>${escapeHtml(govKey({ gov }))}</strong><small>${escapeHtml(formatAddress(gov.tags))}</small></div><select data-manual-select="${gov.id}"><option value="">Pozostaw bez dopasowania</option>${results.unmatchedOsm.map((osm) => `<option value="${osm.type}/${osm.id}" ${state.manual[gov.id] === `${osm.type}/${osm.id}` ? "selected" : ""}>${escapeHtml(osm.tags.name ?? osm.tags.official_name ?? `${osm.type}/${osm.id}`)}</option>`).join("")}</select><button class="tiny-button" data-action="save-manual" data-gov="${gov.id}" title="Zapisz ręczne dopasowanie">↵</button></div>`).join("") || '<div class="empty-rule">Wszystkie rekordy GOV mają przypisanie.</div>'}
      ${results.unmatchedGov.length > 40 ? `<small class="table-caption">Widoczne pierwsze 40 z ${results.unmatchedGov.length} rekordów.</small>` : ""}
    </section><section class="review-section"><div class="section-title"><div><span class="section-index">C</span><h2>Wieloznaczne</h2></div><span class="section-meta">NIE DOPASOWANO AUTOMATYCZNIE</span></div>
      ${results.ambiguous.slice(0, 20).map((item) => `<div class="ambiguous-row"><span class="ambiguous-mark">!</span><div><strong>${escapeHtml(item.gov.tags.name ?? item.gov.tags.official_name ?? `Wiersz ${item.gov.sourceRow}`)}</strong><small>${item.reason === "multiple-osm" ? `${item.candidates.length} kandydatów OSM` : "Kilka rekordów GOV wskazuje ten sam obiekt"} · ${escapeHtml(item.stage)}</small></div></div>`).join("") || '<div class="empty-rule">Brak niejednoznacznych trafień.</div>'}
    </section></div>
    <div class="page-footer"><button class="button button-secondary" data-page="rules">← Reguły</button><span class="step-caption">ETAP 4 Z 5</span><button class="button button-primary" data-page="export">Przejdź do eksportu <span>→</span></button></div>`;
}

function formatAddress(tags = {}) {
  return [tags["addr:street"], tags["addr:housenumber"], tags["addr:place"], tags["addr:city"]].filter(Boolean).join(" ") || "Brak adresu";
}

function renderTagDiff(delta) {
  const changed = Object.entries(delta.changed).map(([key, value]) => `<div><code>${escapeHtml(key)}</code><span>${escapeHtml(value)}</span></div>`);
  const removed = delta.removed.map((key) => `<div class="diff-removed"><code>${escapeHtml(key)}</code><span>usuń</span></div>`);
  return `<div class="diff-list">${[...changed, ...removed].join("")}</div>`;
}

function buildOutput() {
  const results = currentResults();
  if (!results) return null;
  const changes = [];
  for (const match of results.matches) {
    const merged = mergeTags(match.osm.tags, match.gov.tags, state.config.merge);
    if (Object.keys(merged.changed).length || merged.removed.length) changes.push({ ...match.osm, tags: merged.tags, change: merged });
  }
  const toAdd = results.unmatchedGov.flatMap((gov) => {
    if (!Number.isFinite(gov.lat) || !Number.isFinite(gov.lon)) return [];
    const merged = mergeTags({}, gov.tags, { ...state.config.merge, updateAddress: true });
    return [{ type: "node", id: gov.id, version: 1, lat: gov.lat, lon: gov.lon, geometry: { type: "Point", coordinates: [gov.lon, gov.lat] }, tags: merged.tags }];
  });
  return {
    results,
    changes,
    toAdd,
    changeXml: osmXml(changes, "modify"),
    addXml: osmXml(toAdd, "create"),
    noLocation: results.unmatchedGov.filter((gov) => !Number.isFinite(gov.lat) || !Number.isFinite(gov.lon)),
  };
}

function renderExportPage() {
  const output = buildOutput();
  if (!output) return `${pageHeading("05 / PLIKI", "Pobierz wyniki", "Po sprawdzeniu wyników wygeneruj pliki do dalszej pracy.")}<div class="empty-state"><span>05</span><h2>Eksport jeszcze niegotowy</h2><p>Uruchom dopasowanie, żeby zobaczyć pliki wynikowe.</p><button class="button button-primary" data-page="rules">Przejdź do reguł →</button></div>`;
  const noCoordCsv = govNoCoordCsv(output.noLocation, parseCsv(state.csvText, state.config.csv));
  const files = [
    ["to_change.osm", "OSM XML · zmodyfikowane obiekty", output.changes.length],
    ["to_add.osm", "OSM XML · nowe punkty GOV", output.toAdd.length],
    ["gov_no_coord.csv", "Rekordy bez współrzędnych · adres i debug Nominatim", output.noLocation.length],
  ];
  const noCoordPreview = output.noLocation.length ? `<section class="no-coord-section"><div class="section-title"><div><span class="section-index">!</span><h2>Bez współrzędnych</h2></div><span class="section-meta">${output.noLocation.length} rekordów</span></div><p class="section-hint">Podgląd danych i dokładnego zapytania wysłanego do Nominatim. Link otwiera wyszukiwanie do ręcznej diagnostyki.</p><div class="table-wrap preview-table no-coord-table"><table><thead><tr><th>Wiersz</th><th>Nazwa</th><th>Adres / query Nominatim</th><th>Debug</th></tr></thead><tbody>${output.noLocation.slice(0, 100).map((gov) => { const query = nominatimQueryForRow(gov); return `<tr><td>${escapeHtml(gov.sourceRow ?? "")}</td><td>${escapeHtml(gov.tags.name ?? gov.tags.official_name ?? "")}</td><td>${escapeHtml(query || formatAddress(gov.tags))}</td><td>${query ? `<a class="nominatim-debug-link" href="${escapeHtml(nominatimDebugUrl(query))}" target="_blank" rel="noreferrer" title="Debuguj zapytanie w Nominatim">Otwórz ↗</a>` : "Brak adresu"}</td></tr>`; }).join("")}</tbody></table></div>${output.noLocation.length > 100 ? `<p class="section-hint">Pokazano 100 z ${output.noLocation.length} rekordów. Pełna lista znajduje się w CSV.</p>` : ""}</section>` : "";
  return `${pageHeading("05 / PLIKI WYNIKOWE", "Eksportuj wyniki", "Dwa pliki OSM oraz raport GOV bez współrzędnych.")}
    <div class="export-summary"><div><span class="export-number">${String(output.changes.length).padStart(2, "0")}</span><span>obiektów zmodyfikowanych</span></div><div><span class="export-number">${String(output.toAdd.length).padStart(2, "0")}</span><span>nowych punktów gotowych do dodania</span></div></div>
    ${output.noLocation.length ? `<div class="notice notice-warning"><span>!</span><div><strong>${output.noLocation.length} rekordów GOV bez współrzędnych</strong><p>Nie trafią do ` + "`to_add.osm`" + `. Sprawdź zapytania poniżej albo pobierz raport CSV.</p></div></div>` : ""}
    <div class="export-list">${files.map(([name, description, count], index) => `<div class="export-file"><span class="file-number">0${index + 1}</span><div><strong>${name}</strong><small>${description}</small></div><span class="file-count">${count} obiektów</span><button class="download-button" data-download="${name}" title="Pobierz ${name}" aria-label="Pobierz ${name}">↓</button></div>`).join("")}</div>
    ${noCoordPreview}
    <div class="export-actions"><button class="button button-primary" data-action="download-all">Pobierz trzy pliki <span>↓</span></button><button class="button button-secondary" data-action="save-zip">Zapisz pakiet sesji</button></div>
    <div class="page-footer"><button class="button button-secondary" data-page="review">← Wróć do kontroli</button><span class="step-caption">GOTOWE DO POBRANIA</span><span></span></div>`;
}

function wireEvents() {
  app.querySelectorAll("[data-page]").forEach((element) => element.addEventListener("click", (event) => {
    state.page = event.currentTarget.dataset.page;
    render();
  }));
  app.querySelectorAll("[data-action]").forEach((element) => element.addEventListener("click", handleAction));
  app.querySelector("#project-name")?.addEventListener("input", (event) => {
    state.config.name = event.target.value;
    persist();
  });
  app.querySelector("#csv-input")?.addEventListener("change", handleCsvFile);
  app.querySelector("#osm-input")?.addEventListener("change", handleOsmFile);
  app.querySelector("#zip-input")?.addEventListener("change", handleZipFile);
  app.querySelector("#csv-delimiter")?.addEventListener("change", (event) => {
    state.config.csv.delimiter = event.target.value === "\\t" ? "\t" : event.target.value;
    prepareCsv();
  });
  app.querySelector("#csv-quote")?.addEventListener("input", (event) => { state.config.csv.quote = event.target.value || '"'; scheduleGovPreviewRefresh(); });
  app.querySelectorAll("[data-map-source]").forEach((select) => select.addEventListener("change", () => {
    const key = select.dataset.mapSource;
    const current = state.config.csv.mapping[key];
    if (select.multiple) {
      state.config.csv.mapping[key] = { type: "concat", columns: [...select.selectedOptions].map((option) => option.value), separator: current?.separator ?? " " };
    } else if (!select.value) delete state.config.csv.mapping[key];
    else state.config.csv.mapping[key] = select.value;
    prepareCsv();
  }));
  app.querySelectorAll("[data-map-mode]").forEach((select) => select.addEventListener("change", () => {
    const key = select.dataset.mapMode;
    const current = state.config.csv.mapping[key];
    if (select.value === "concat") {
      state.config.csv.mapping[key] = { type: "concat", columns: typeof current === "string" && current ? [current] : current?.columns ?? [], separator: current?.separator ?? " " };
    } else if (select.value === "address") {
      state.config.csv.mapping[key] = {
        type: "address",
        city: normalizeAddressField(current?.city),
        street: normalizeAddressField(current?.street),
        housenumber: normalizeAddressField(current?.housenumber),
        postcode: normalizeAddressField(current?.postcode),
        place: normalizeAddressField(current?.place),
      };
    } else {
      const sources = current?.type === "concat" ? current.columns : [];
      state.config.csv.mapping[key] = sources[0] ?? "";
    }
    prepareCsv();
  }));
  app.querySelectorAll("[data-address-source]").forEach((select) => select.addEventListener("change", () => {
    const key = select.dataset.mapAddress;
    const current = state.config.csv.mapping[key];
    if (!current || current.type !== "address") return;
    const normalized = normalizeAddressField(current[select.dataset.addressSource]);
    normalized.column = select.value || "";
    current[select.dataset.addressSource] = normalized;
    prepareCsv();
  }));
  app.querySelectorAll("[data-address-regex-in]").forEach((input) => input.addEventListener("input", () => {
    const key = input.dataset.mapAddress;
    const current = state.config.csv.mapping[key];
    if (!current || current.type !== "address") return;
    const normalized = normalizeAddressField(current[input.dataset.addressRegexIn]);
    normalized.regexIn = input.value.trim();
    current[input.dataset.addressRegexIn] = normalized;
    scheduleGovPreviewRefresh();
  }));
  app.querySelectorAll("[data-address-regex-out]").forEach((input) => input.addEventListener("input", () => {
    const key = input.dataset.mapAddress;
    const current = state.config.csv.mapping[key];
    if (!current || current.type !== "address") return;
    const normalized = normalizeAddressField(current[input.dataset.addressRegexOut]);
    normalized.regexOut = input.value.trim();
    current[input.dataset.addressRegexOut] = normalized;
    scheduleGovPreviewRefresh();
  }));
  app.querySelectorAll("[data-map-separator]").forEach((input) => input.addEventListener("change", () => {
    const rule = state.config.csv.mapping[input.dataset.mapSeparator];
    if (rule?.type === "concat") rule.separator = input.value;
    prepareCsv();
  }));
  app.querySelectorAll("[data-map-tag]").forEach((input) => input.addEventListener("change", () => {
    const oldKey = input.dataset.mapTag;
    const newKey = input.value.trim();
    if (!newKey || newKey === oldKey) return;
    if (Object.hasOwn(state.config.csv.mapping, newKey)) return notify("Taki tag jest już zmapowany.", true);
    state.config.csv.mapping[newKey] = state.config.csv.mapping[oldKey] ?? "";
    delete state.config.csv.mapping[oldKey];
    state.config.csv.transforms = state.config.csv.transforms.map((transform) => transform.key === oldKey ? { ...transform, key: newKey } : transform);
    prepareCsv();
  }));
  app.querySelectorAll("[data-transform-type], [data-transform-key], [data-regex-flags]").forEach((input) => input.addEventListener("change", handleTransformChange));
  app.querySelectorAll("[data-transform-value], [data-regex-pattern], [data-regex-template]").forEach((input) => input.addEventListener("input", (event) => handleTransformChange(event, true)));
  app.querySelectorAll("[data-stage-enabled]").forEach((input) => input.addEventListener("change", () => {
    state.config.matching.stages[Number(input.dataset.stageEnabled)].enabled = input.checked;
    persist(); render();
  }));
  app.querySelectorAll("[data-stage-radius]").forEach((input) => input.addEventListener("change", () => {
    state.config.matching.stages[Number(input.dataset.stageRadius)].toleranceM = Math.max(1, Number(input.value)); persist();
  }));
  app.querySelectorAll("[data-stage-fields]").forEach((input) => input.addEventListener("change", () => {
    state.config.matching.stages[Number(input.dataset.stageFields)].fields = input.value.split(",").map((item) => item.trim()).filter(Boolean); persist(); render();
  }));
  app.querySelectorAll("[data-stage-type]").forEach((select) => select.addEventListener("change", () => {
    const stage = state.config.matching.stages[Number(select.dataset.stageType)];
    stage.type = select.value;
    if (stage.type === "address") {
      stage.fields = ["addr:city"];
      stage.label = "Adres — miasto";
    } else if (stage.type === "tags") {
      stage.fields = ["amenity"];
      stage.label = "Tagi";
    } else if (stage.type === "location") {
      stage.toleranceM ??= 100;
      stage.label = "Odległość";
    } else {
      delete stage.fields;
      stage.label = "Nazwa";
    }
    persist(); render();
  }));
  app.querySelectorAll("[data-op-type], [data-op-key], [data-op-value]").forEach((input) => input.addEventListener("change", handleOperationChange));
  app.querySelectorAll("[data-manual-select]").forEach((select) => select.addEventListener("change", () => { select.dataset.selectedValue = select.value; }));
  app.querySelectorAll("[data-download]").forEach((button) => button.addEventListener("click", () => downloadOutput(button.dataset.download)));
  app.querySelector("#merge-policy")?.addEventListener("change", (event) => { state.config.merge.conflict = event.target.value; persist(); });
  app.querySelector("#update-address")?.addEventListener("change", (event) => { state.config.merge.updateAddress = event.target.checked; persist(); });
  app.querySelector("#add-address-when-missing")?.addEventListener("change", (event) => { state.config.merge.addAddressWhenMissing = event.target.checked; persist(); });
  app.querySelector("#nominatim-enabled")?.addEventListener("change", (event) => { state.config.nominatim.enabled = event.target.checked; persist(); });
  app.querySelector("#source-description")?.addEventListener("change", (event) => {
    state.config.merge.source = event.target.value.trim();
    persist();
  });
  app.querySelector("#source-key")?.addEventListener("change", (event) => {
    const key = event.target.value.trim();
    if (/[\s=]/.test(key)) {
      event.target.value = state.config.merge.sourceKey || "source:office";
      return notify("Klucz OSM nie może zawierać spacji ani znaku =.", true);
    }
    state.config.merge.sourceKey = key || "source:office";
    persist();
  });
  app.querySelector("#overpass-endpoint")?.addEventListener("change", (event) => { state.config.overpass.endpoint = event.target.value; persist(); });
  app.querySelector("#overpass-query")?.addEventListener("change", (event) => { state.config.overpass.query = event.target.value; persist(); });
  app.querySelector("#filter-column")?.addEventListener("change", () => {});
}

async function handleAction(event) {
  const button = event.currentTarget;
  const { action } = button.dataset;
  if (action === "open-zip") app.querySelector("#zip-input")?.click();
  else if (action === "save-zip") await downloadZip();
  else if (action === "prepare-csv") prepareCsv();
  else if (action === "add-map") addMapping();
  else if (action === "remove-map") { delete state.config.csv.mapping[button.dataset.key]; persist(); render(); }
  else if (action === "add-filter") addFilter();
  else if (action === "remove-filter") { state.config.csv.filters.splice(Number(button.dataset.index), 1); prepareCsv(); }
  else if (action === "remove-osm") removeOsmData();
  else if (action === "add-transform") addTransform();
  else if (action === "remove-transform") { state.config.csv.transforms.splice(Number(button.dataset.index), 1); prepareCsv(); }
  else if (action === "fetch-overpass") await fetchOverpass();
  else if (action === "cancel-request") state.abortController?.abort();
  else if (action === "move-stage") moveStage(Number(button.dataset.index), Number(button.dataset.delta));
  else if (action === "add-stage-address") addAddressStage();
  else if (action === "add-stage") addMatchingStage();
  else if (action === "remove-stage") { state.config.matching.stages.splice(Number(button.dataset.index), 1); state.results = null; persist(); render(); }
  else if (action === "add-operation") addOperation(button.dataset.type);
  else if (action === "remove-operation") { state.config.merge.operations.splice(Number(button.dataset.index), 1); persist(); render(); }
  else if (action === "run-match") await runMatch();
  else if (action === "unlink") { state.manual[button.dataset.gov] = ""; persist(); render(); }
  else if (action === "save-manual") {
    const select = app.querySelector(`[data-manual-select="${CSS.escape(button.dataset.gov)}"]`);
    const selected = select?.value ?? "";
    if (selected && Object.entries(state.manual).some(([id, osmKey]) => id !== button.dataset.gov && osmKey === selected)) return notify("Ten obiekt OSM jest już przypisany ręcznie.", true);
    state.manual[button.dataset.gov] = selected;
    persist(); render();
  } else if (action === "download-all") await downloadAll();
}

function handleOperationChange(event) {
  const operation = state.config.merge.operations[Number(event.target.dataset.opType ?? event.target.dataset.opKey ?? event.target.dataset.opValue)];
  if (!operation) return;
  if (event.target.dataset.opType !== undefined) operation.type = event.target.value;
  if (event.target.dataset.opKey !== undefined) operation.key = event.target.value;
  if (event.target.dataset.opValue !== undefined) {
    if (operation.type === "replace") {
      const [find, ...replace] = event.target.value.split("→");
      operation.find = find.trim(); operation.replace = replace.join("→").trim();
    } else operation.value = event.target.value;
  }
  persist();
}

function handleTransformChange(event, previewOnly = false) {
  const index = Number(event.target.dataset.transformType ?? event.target.dataset.transformKey ?? event.target.dataset.transformValue ?? event.target.dataset.regexPattern ?? event.target.dataset.regexFlags ?? event.target.dataset.regexTemplate);
  const transform = state.config.csv.transforms[index];
  if (!transform) return;
  if (event.target.dataset.transformType !== undefined) {
    const nextType = event.target.value;
    if (nextType === "regex") {
      Object.assign(transform, { type: "regex", key: transform.key || Object.keys(state.config.csv.mapping)[0] || "", pattern: "", flags: "", template: "$1" });
      delete transform.find;
      delete transform.replace;
      delete transform.value;
    } else if (transform.type === "regex") {
      Object.assign(transform, { type: nextType, key: transform.key || Object.keys(state.config.csv.mapping)[0] || "", value: "" });
      delete transform.pattern;
      delete transform.flags;
      delete transform.template;
    } else {
      transform.type = nextType;
    }
    persist();
    render();
    return;
  }
  if (event.target.dataset.transformKey !== undefined) transform.key = event.target.value;
  if (event.target.dataset.regexPattern !== undefined) transform.pattern = event.target.value;
  if (event.target.dataset.regexFlags !== undefined) transform.flags = event.target.value;
  if (event.target.dataset.regexTemplate !== undefined) transform.template = event.target.value;
  if (event.target.dataset.transformValue !== undefined) {
    if (transform.type === "replace") {
      const [find, ...replace] = event.target.value.split("→");
      transform.find = find.trim();
      transform.replace = replace.join("→").trim();
    } else {
      transform.value = event.target.value;
    }
  }
  if (previewOnly) scheduleGovPreviewRefresh();
  else prepareCsv();
}

function addMapping() {
  const existing = new Set(Object.keys(state.config.csv.mapping));
  let index = 1;
  while (existing.has(`tag:${index}`)) index += 1;
  state.config.csv.mapping[`tag:${index}`] = "";
  persist(); render();
}

function addFilter() {
  const column = app.querySelector("#filter-column")?.value;
  if (!column) return notify("Wybierz kolumnę do filtrowania.", true);
  const operator = app.querySelector("#filter-operator").value;
  const value = app.querySelector("#filter-value").value;
  state.config.csv.filters.push({ column, operator, value });
  prepareCsv();
}

function addTransform() {
  const key = Object.keys(state.config.csv.mapping)[0] ?? "";
  state.config.csv.transforms.push({ type: "trim", key });
  persist(); render();
}

function addOperation(type) {
  state.config.merge.operations.push(type === "replace" ? { type, key: "", find: "", replace: "" } : { type, key: "", value: type === "delete" ? "*" : "" });
  persist(); render();
}

function moveStage(index, delta) {
  const next = index + delta;
  if (next < 0 || next >= state.config.matching.stages.length) return;
  const [stage] = state.config.matching.stages.splice(index, 1);
  state.config.matching.stages.splice(next, 0, stage);
  persist(); render();
}

async function handleCsvFile(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  state.csvText = await file.text();
  state.csvFileName = file.name;
  try {
    const records = parseCsv(state.csvText, state.config.csv);
    const headers = Object.keys(records[0] ?? {}).filter((key) => key !== "__row");
    for (const tag of ["name", "addr:street", "addr:housenumber", "addr:city", "addr:place", "addr:postcode", "email", "phone", "website", "__lat", "__lon"]) {
      if (state.config.csv.mapping[tag]) continue;
      const suggestion = suggestHeader(headers, tag);
      if (suggestion) state.config.csv.mapping[tag] = suggestion;
    }
    prepareCsv();
  } catch (error) { notify(error.message, true); render(); }
}

function suggestHeader(headers, tag) {
  const tokens = {
    name: ["name", "nazwa", "obiekt"], "addr:street": ["street", "ulica", "ul."],
    "addr:housenumber": ["number", "numer", "nr domu", "budynku"], "addr:city": ["city", "miasto", "miejscowość", "miejscowosc"],
    "addr:place": ["place"], "addr:postcode": ["postcode", "kod pocztowy", "kod"],
    email: ["email", "e-mail"], phone: ["phone", "telefon"], website: ["website", "strona", "www"],
    __lat: ["lat", "latitude", "szerokość", "szerokosc"], __lon: ["lon", "lng", "longitude", "długość", "dlugosc"],
  }[tag] ?? [];
  return headers.find((header) => tokens.some((token) => header.toLocaleLowerCase("pl-PL").includes(token)));
}

function prepareCsv() {
  if (!state.csvText) return;
  try {
    const records = parseCsv(state.csvText, state.config.csv);
    const prepared = prepareGovRows(records, state.config);
    state.govRows = prepared.rows;
    state.csvErrors = prepared.errors;
    state.results = null;
    persist(); render();
    notify(`Przygotowano ${state.govRows.length} rekordów GOV.`);
  } catch (error) { notify(error.message, true); }
}

function scheduleGovPreviewRefresh() {
  clearTimeout(previewRefreshTimer);
  previewRefreshTimer = setTimeout(() => {
    try {
      const sourceRows = parseCsv(state.csvText, state.config.csv);
      const prepared = prepareGovRows(sourceRows, state.config);
      state.govRows = prepared.rows;
      state.csvErrors = prepared.errors;
      state.results = null;
      const preview = document.querySelector("[data-gov-preview]");
      const errors = document.querySelector("[data-gov-errors]");
      if (preview) preview.innerHTML = renderGovPreview();
      if (errors) errors.innerHTML = renderErrors();
      clearTimeout(previewSaveTimer);
      previewSaveTimer = setTimeout(() => persist(), 500);
    } catch (error) {
      notify(error.message, true);
    }
  }, 250);
}

async function handleOsmFile(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  state.osmText = await file.text();
  state.osmFileName = file.name;
  try {
    state.osmRows = parseOverpass(state.osmText);
    state.results = null;
    persist(); render();
    notify(`Wczytano ${state.osmRows.length} obiektów OSM.`);
  } catch (error) { notify(`Błędny plik OSM: ${error.message}`, true); }
}

function removeOsmData() {
  state.abortController?.abort();
  state.osmText = "";
  state.osmFileName = "";
  state.osmRows = [];
  state.results = null;
  state.manual = {};
  persist();
  render();
  notify("Usunięto plik OSM i wyczyszczono wyniki dopasowania.");
}

function addAddressStage() {
  const stages = state.config.matching.stages;
  const addressCount = stages.filter((stage) => stage.type === "address").length;
  stages.push({
    type: "address",
    enabled: true,
    label: addressCount === 0 ? "Adres — miasto" : `Adres ${addressCount + 1}`,
    fields: ["addr:city"],
  });
  state.results = null;
  persist();
  render();
}

function addMatchingStage() {
  state.config.matching.stages.push({ type: "name", enabled: true, label: "Nazwa" });
  state.results = null;
  persist();
  render();
}

async function fetchOverpass() {
  const query = app.querySelector("#overpass-query").value.trim();
  const endpoint = app.querySelector("#overpass-endpoint").value.trim();
  if (!query) return notify("Wpisz zapytanie Overpass QL.", true);
  if (query.includes("{{") || query.includes("}}")) return notify("Zapytanie zawiera nierozwinięty placeholder. Użyj konkretnego obszaru lub importuj JSON.", true);
  state.config.overpass = { endpoint, query };
  state.busy = true;
  state.abortController = new AbortController();
  render();
  const timeout = setTimeout(() => state.abortController?.abort(), 120000);
  try {
    const response = await fetch(endpoint, {
      method: "POST", body: new URLSearchParams({ data: query }), signal: state.abortController.signal,
      headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8", Accept: "application/json" },
    });
    if (!response.ok) throw new Error(`Overpass zwrócił HTTP ${response.status}.`);
    state.osmText = await response.text();
    state.osmRows = parseOverpass(state.osmText);
    state.osmFileName = "overpass-response.json";
    state.results = null;
    persist();
    notify(`Pobrano ${state.osmRows.length} obiektów OSM.`);
  } catch (error) {
    notify(error.name === "AbortError" ? "Zapytanie anulowano lub upłynął limit czasu." : `Nie udało się pobrać OSM: ${error.message} Możliwe, że endpoint blokuje CORS; wczytaj plik JSON.`, true);
  } finally {
    clearTimeout(timeout); state.busy = false; state.abortController = null; render();
  }
}

async function runMatch() {
  if (!state.govRows.length || !state.osmRows.length) return notify("Wczytaj zarówno dane GOV, jak i OSM.", true);
  state.busy = true;
  state.status = "Trwa dopasowanie rekordów — to może chwilę potrwać…";
  state.abortController = new AbortController();
  render();
  try {
    state.govRows = await geocodeUnmatchedAfterStages(
      state.govRows,
      state.osmRows,
      state.config.matching.stages,
      state.config.nominatim,
      {
        signal: state.abortController.signal,
        onProgress: ({ done, total }) => notify(`Nominatim: ${done}/${total}`),
      },
    );
    state.results = matchRecords(state.govRows, state.osmRows, state.config.matching.stages);
    state.manual = {};
    persist();
    state.page = "review";
    notify(`Dopasowano ${state.results.matches.length} par. Niejednoznaczne: ${state.results.ambiguous.length}.`);
  } catch (error) { notify(`Dopasowanie przerwane: ${error.message}`, true); }
  finally { state.busy = false; state.abortController = null; render(); }
}

async function handleZipFile(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const { config, csvText, osmText } = await readSessionZip(file);
    const importedConfig = normalizeConfig(config);
    const parsedOsm = parseOverpass(osmText);
    const preparedGov = prepareGovRows(parseCsv(csvText, importedConfig.csv), importedConfig);
    state.config = importedConfig;
    state.csvText = csvText; state.osmText = osmText;
    state.csvFileName = file.name;
    state.osmFileName = "osm.json";
    state.govRows = preparedGov.rows; state.csvErrors = preparedGov.errors; state.osmRows = parsedOsm;
    state.results = null; state.manual = {};
    persist(); state.page = "csv";
    notify(`Załadowano sesję: ${state.govRows.length} GOV, ${state.osmRows.length} OSM.`);
  } catch (error) { notify(`Nie można otworzyć ZIP: ${error.message}`, true); }
  finally { render(); event.target.value = ""; }
}

async function downloadZip() {
  if (!state.csvText || !state.osmText) return notify("ZIP sesji wymaga plików gov.csv i osm.json.", true);
  try {
    const bytes = await createSessionZip(state.config, state.csvText, state.osmText);
    const blob = new Blob([bytes], { type: "application/zip" });
    triggerDownload(blob, `pakiet-sesji-${safeFilename(state.config.name || "gov-osm")}.zip`);
    notify("Pobrano pakiet sesji.");
  } catch (error) { notify(`Nie udało się przygotować ZIP: ${error.message}`, true); }
}

function downloadOutput(name) {
  const output = buildOutput();
  if (!output) return notify("Najpierw uruchom dopasowanie.", true);
  const noCoordCsv = govNoCoordCsv(output.noLocation, parseCsv(state.csvText, state.config.csv));
  const files = {
    "to_change.osm": [output.changeXml, "application/xml;charset=utf-8"],
    "to_add.osm": [output.addXml, "application/xml;charset=utf-8"],
    "gov_no_coord.csv": [noCoordCsv, "text/csv;charset=utf-8"],
  };
  if (!files[name]) return;
  triggerDownload(new Blob([files[name][0]], { type: files[name][1] }), name);
  notify(`Pobrano ${name}.`);
}

async function downloadAll() {
  for (const name of ["to_change.osm", "to_add.osm", "gov_no_coord.csv"]) {
    downloadOutput(name);
    await new Promise((resolve) => setTimeout(resolve, 180));
  }
  notify("Przygotowano trzy pliki wynikowe.");
}

function triggerDownload(blob, name) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = name; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function safeFilename(value) { return String(value).normalize("NFKD").replace(/[^\w-]+/g, "-").replace(/^-|-$/g, "").toLowerCase() || "gov-osm-session"; }

async function boot() {
  try {
    const saved = await loadSession();
    if (saved?.config) {
      state.config = normalizeConfig(saved.config);
      state.csvText = saved.csvText ?? ""; state.osmText = saved.osmText ?? "";
      state.csvFileName = saved.csvFileName ?? ""; state.osmFileName = saved.osmFileName ?? "";
      state.manual = saved.manual ?? {};
      if (state.csvText) {
        const prepared = prepareGovRows(parseCsv(state.csvText, state.config.csv), state.config);
        state.govRows = prepared.rows; state.csvErrors = prepared.errors;
      }
      if (state.osmText) state.osmRows = parseOverpass(state.osmText);
    }
  } catch { /* A fresh session remains usable when browser storage is unavailable. */ }
  render();
}

boot();