export const DEFAULT_CONFIG = {
  version: 1,
  name: "",
  csv: { delimiter: ";", quote: '"', mapping: {}, filters: [], transforms: [] },
  overpass: {
    endpoint: "https://gov-osm-overpass.kuba-medrek.workers.dev/api/overpass",
    query: "",
  },
  matching: {
    stages: [
      { type: "name", enabled: true, label: "Nazwa" },
      { type: "address", enabled: true, label: "Adres", fields: ["addr:street", "addr:housenumber", "addr:city"] },
      { type: "tags", enabled: false, label: "Wymagane tagi", fields: ["amenity"] },
      { type: "location", enabled: false, label: "Odległość", toleranceM: 100 },
    ],
  },
  merge: {
    conflict: "keep-osm",
    operations: [],
    source: "",
    sourceKey: "source:office",
    updateAddress: false,
    addAddressWhenMissing: false,
  },
  nominatim: { enabled: false, endpoint: "https://nominatim.openstreetmap.org/search" },
};

export function normalizeConfig(config = {}) {
  const normalized = {
    ...structuredClone(DEFAULT_CONFIG),
    ...config,
    csv: { ...structuredClone(DEFAULT_CONFIG.csv), ...(config.csv ?? {}) },
    overpass: { ...structuredClone(DEFAULT_CONFIG.overpass), ...(config.overpass ?? {}) },
    matching: { ...structuredClone(DEFAULT_CONFIG.matching), ...(config.matching ?? {}) },
    merge: { ...structuredClone(DEFAULT_CONFIG.merge), ...(config.merge ?? {}) },
    nominatim: { ...structuredClone(DEFAULT_CONFIG.nominatim), ...(config.nominatim ?? {}) },
  };
  const legacySource = Object.entries(normalized.merge.sourceTags ?? {}).find(([key]) => key.startsWith("source:"));
  if (config.merge?.source === undefined) normalized.merge.source = legacySource?.[1] ?? "";
  if (config.merge?.sourceKey === undefined) normalized.merge.sourceKey = legacySource?.[0] ?? "source:office";
  normalized.csv.transforms ??= [];
  normalized.csv.address ??= {};
  const addressTransforms = [];
  migrateAddressMapping(normalized.csv.address, normalized.csv.mapping, addressTransforms);
  for (const [tag, rule] of Object.entries(normalized.csv.mapping)) {
    if (rule?.type !== "address") continue;
    delete normalized.csv.mapping[tag];
    migrateAddressMapping(rule, normalized.csv.mapping, addressTransforms);
  }
  normalized.csv.address = {};
  for (const [tag, rule] of Object.entries(normalized.csv.mapping)) {
    if (rule?.type !== "regex") continue;
    normalized.csv.transforms.push({
      type: "regex",
      key: tag,
      pattern: rule.pattern ?? "",
      flags: rule.flags ?? "",
      template: rule.template ?? "$1",
    });
    normalized.csv.mapping[tag] = rule.column ?? "";
  }
  for (const rule of normalized.csv.regexRules ?? []) {
    normalized.csv.transforms.push({
      type: "regex",
      key: Object.keys(normalized.csv.mapping).find((tag) => normalized.csv.mapping[tag] === rule.column) ?? "",
      pattern: rule.pattern ?? "",
      flags: rule.flags ?? "",
      template: rule.template ?? rule.outputs?.[0]?.template ?? "$1",
    });
  }
  normalized.csv.transforms = [...addressTransforms, ...normalized.csv.transforms].map((transform) => {
    if (transform.type === "regex" && transform.outputs?.length) {
      return { ...transform, template: transform.template ?? transform.outputs[0].template ?? "$1", key: transform.key ?? "" };
    }
    if (transform.column && !transform.key) {
      const key = Object.keys(normalized.csv.mapping).find((tag) => {
        const rule = normalized.csv.mapping[tag];
        return rule === transform.column || rule?.column === transform.column || rule?.columns?.includes(transform.column);
      });
      return { ...transform, key: key ?? "" };
    }
    return transform;
  });
  delete normalized.csv.regexRules;
  return normalized;
}

function migrateAddressMapping(definition, mapping, transforms) {
  if (!definition || typeof definition !== "object") return;
  if (!definition.place && definition.unit) definition.place = definition.unit;
  delete definition.unit;
  for (const fieldName of ["city", "street", "housenumber", "postcode", "place"]) {
    const value = definition[fieldName];
    if (typeof value === "string") {
      definition[fieldName] = { column: value, regexIn: "", regexOut: "$1", flags: "im" };
    } else if (value && typeof value === "object") {
      definition[fieldName] = {
        ...value,
        regexIn: value.regexIn ?? value.regex ?? "",
        regexOut: value.regexOut ?? "$1",
        flags: value.flags ?? value.regexFlags ?? "im",
      };
      delete definition[fieldName].regex;
      delete definition[fieldName].regexFlags;
    }
    const field = definition[fieldName];
    const tag = `addr:${fieldName}`;
    if (!field?.column || Object.hasOwn(mapping, tag)) continue;
    mapping[tag] = field.column;
    if (field.regexIn) {
      transforms.push({
        type: "regex",
        key: tag,
        pattern: field.regexIn,
        flags: field.flags ?? "im",
        template: field.regexOut ?? "$1",
      });
    }
  }
}

const ADDRESS_KEYS = new Set([
  "addr:city", "addr:place", "addr:street", "addr:housenumber", "addr:postcode",
]);

export function parseCsv(text, { delimiter = ",", quote = '"' } = {}) {
  if (!delimiter || delimiter.length !== 1) throw new Error("Separator CSV musi być pojedynczym znakiem.");
  const rows = [];
  let row = [];
  let value = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quoted) {
      if (char === quote && text[index + 1] === quote) {
        value += quote;
        index += 1;
      } else if (char === quote) {
        quoted = false;
      } else {
        value += char;
      }
    } else if (char === quote && value.length === 0) {
      quoted = true;
    } else if (char === delimiter) {
      row.push(value);
      value = "";
    } else if (char === "\n" || char === "\r") {
      if (char === "\r" && text[index + 1] === "\n") index += 1;
      row.push(value);
      rows.push(row);
      row = [];
      value = "";
    } else {
      value += char;
    }
  }
  if (quoted) throw new Error("Plik CSV zawiera niedomknięty cudzysłów.");
  if (value.length || row.length) {
    row.push(value);
    rows.push(row);
  }
  while (rows.length && rows.at(-1).every((cell) => cell.trim() === "")) rows.pop();
  if (rows.length < 2) throw new Error("CSV musi zawierać nagłówek i co najmniej jeden wiersz.");
  const headers = rows.shift().map((header) => header.replace(/^\uFEFF/, "").trim());
  if (headers.some((header) => !header)) throw new Error("Nagłówki CSV nie mogą być puste.");
  if (new Set(headers).size !== headers.length) throw new Error("Nagłówki CSV muszą być unikalne.");
  const records = rows.map((cells, index) => ({
    __row: index + 2,
    ...Object.fromEntries(headers.map((header, column) => [header, (cells[column] ?? "").trim()])),
  }));
  records.headers = headers;
  return records;
}

export function prepareGovRows(rows, config) {
  const mapping = config.csv?.mapping ?? {};
  const filters = config.csv?.filters ?? [];
  const transforms = config.csv?.transforms ?? [];
  const addressConfig = config.csv?.address ?? {};
  const errors = [];
  const prepared = [];
  rows.forEach((row, index) => {
    try {
      const tags = {};
      if (Object.keys(addressConfig).length) applyAddressMapping(row, tags, addressConfig);
      for (const [tag, rule] of Object.entries(mapping)) {
        if (rule?.type === "address") {
          applyAddressMapping(row, tags, rule);
          continue;
        }
        const result = resolveField(row, rule);
        if (result !== "") tags[tag] = result;
      }
      for (const transform of transforms) applyTransform(tags, transform);
      if (filters.some((filter) => !passesFilter({ ...row, ...tags }, filter))) return;
      const lat = parseCoordinate(tags["__lat"] ?? tags["lat"]);
      const lon = parseCoordinate(tags["__lon"] ?? tags["lon"]);
      delete tags.__lat;
      delete tags.__lon;
      delete tags.lat;
      delete tags.lon;
      prepared.push({
        id: -(1000000 + index + 1),
        tags,
        lat,
        lon,
        sourceRow: row.__row ?? index + 2,
      });
    } catch (error) {
      errors.push({ row: row.__row ?? index + 2, message: error.message });
    }
  });
  return { rows: prepared, errors };
}

export function mappedTagKeys(csv = {}) {
  const mapping = csv.mapping ?? {};
  const tags = new Set(Object.keys(mapping));
  const addressFields = ["city", "street", "housenumber", "postcode", "place"];
  const hasSource = (field) => typeof field === "string" ? Boolean(field) : Boolean(field?.column);
  for (const [tag, rule] of Object.entries(mapping)) {
    if (rule?.type !== "address") continue;
    tags.delete(tag);
    for (const field of addressFields) {
      if (hasSource(rule[field] ?? rule[`addr:${field}`])) tags.add(`addr:${field}`);
    }
  }
  for (const field of addressFields) {
    if (hasSource(csv.address?.[field] ?? csv.address?.[`addr:${field}`])) tags.add(`addr:${field}`);
  }
  return [...tags].sort((left, right) => left.localeCompare(right, "pl", { sensitivity: "base" }));
}

export function buildGovPreview(sourceRows, preparedRows, config) {
  const sourceColumns = sourceRows.headers ?? Object.keys(sourceRows[0] ?? {}).filter((key) => key !== "__row");
  const tagColumns = new Set(Object.keys(config.csv?.mapping ?? {}));
  for (const [tag, rule] of Object.entries(config.csv?.mapping ?? {})) {
    if (rule?.type !== "address") continue;
    tagColumns.delete(tag);
    for (const fieldName of ["city", "street", "housenumber", "postcode", "place"]) {
      if (rule[fieldName]?.column || typeof rule[fieldName] === "string") tagColumns.add(`addr:${fieldName}`);
    }
  }

  for (const row of preparedRows) Object.keys(row.tags).forEach((tag) => tagColumns.add(tag));
  const preparedBySourceRow = new Map(preparedRows.map((row) => [row.sourceRow, row]));
  return {
    sourceColumns,
    tagColumns: [...tagColumns].sort((left, right) => left.localeCompare(right, "pl", { sensitivity: "base" })),
    rows: sourceRows.map((source) => ({
      sourceRow: source.__row,
      source,
      prepared: preparedBySourceRow.get(source.__row) ?? null,
    })),
  };
}

export function selectGovPreviewSample(rows, page = 0, sampleSize = 10) {
  if (rows.length <= sampleSize) return rows;
  const order = rows.map((_, index) => index);
  let seed = 0x4c4f4d42;
  const random = () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let value = seed;
    value = Math.imul(value ^ value >>> 15, value | 1);
    value ^= value + Math.imul(value ^ value >>> 7, value | 61);
    return ((value ^ value >>> 14) >>> 0) / 4294967296;
  };
  for (let index = order.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1));
    [order[index], order[swapIndex]] = [order[swapIndex], order[index]];
  }
  const pageCount = Math.ceil(rows.length / sampleSize);
  const normalizedPage = ((page % pageCount) + pageCount) % pageCount;
  return order.slice(normalizedPage * sampleSize, (normalizedPage + 1) * sampleSize).map((index) => rows[index]);
}

function applyAddressMapping(row, tags, definition) {
  const entries = ["city", "street", "housenumber", "postcode", "place"];
  for (const fieldName of entries) {
    const rawConfig = definition?.[fieldName] ?? definition?.[`addr:${fieldName}`] ?? "";
    const config = typeof rawConfig === "string" ? { column: rawConfig, regexIn: "", regexOut: "", flags: "im" } : rawConfig ?? {};
    const column = config.column ?? "";
    if (!column) continue;
    const raw = String(row[column] ?? "").trim();
    if (!raw) continue;
    const cleaned = applyFieldRegex(raw, config.regexIn ?? config.regex ?? "", config.regexOut, config.flags ?? config.regexFlags ?? "im");
    if (!cleaned) continue;
    const osmKey = `addr:${fieldName}`;
    tags[osmKey] = cleaned;
  }
}

function applyFieldRegex(value, regexPattern = "", replacement = "$1", flags = "im") {
  const text = String(value ?? "").trim();
  if (!text || !regexPattern) return text;
  if (regexPattern.length > 256 || text.length > 2048) throw new Error("Regex adresu przekracza dozwolony rozmiar.");
  const safeFlags = [...new Set(String(flags || "im"))].join("");
  if (!/^[im]*$/.test(safeFlags)) throw new Error("Regex adresu obsługuje tylko flagi i oraz m.");
  assertSafeRegex(regexPattern);
  try {
    const expression = new RegExp(regexPattern, safeFlags);
    return text.replace(expression, String(replacement || "$1")).trim();
  } catch {
    throw new Error("Niepoprawny regex adresu.");
  }
}

function resolveField(row, rule) {
  if (typeof rule === "string") return String(row[rule] ?? "").trim();
  if (!rule || typeof rule !== "object") return "";
  if (rule.type === "constant") return String(rule.value ?? "").trim();
  if (rule.type === "lookup") return String(rule.values?.[row[rule.column]] ?? rule.fallback ?? "").trim();
  if (rule.type === "concat") return (rule.columns ?? []).map((column) => row[column] ?? "").filter(Boolean).join(rule.separator ?? " ").trim();
  if (rule.type === "replace") return String(row[rule.column] ?? "").replaceAll(rule.find ?? "", rule.replace ?? "").trim();
  if (rule.type === "case") {
    const value = String(row[rule.column] ?? "").trim();
    return rule.mode === "upper" ? value.toLocaleUpperCase() : rule.mode === "lower" ? value.toLocaleLowerCase() : value;
  }
  if (rule.type === "address") return "";
  throw new Error(`Nieobsługiwane mapowanie pola: ${rule.type ?? "brak typu"}`);
}

function matchRegex(value, rule) {
  const pattern = String(rule.pattern ?? "");
  const flags = String(rule.flags ?? "");
  if (!pattern || pattern.length > 256) throw new Error("Regex musi mieć od 1 do 256 znaków.");
  if (!/^[im]*$/.test(flags)) throw new Error("Dozwolone flagi regex to i oraz m.");
  assertSafeRegex(pattern);
  const input = String(value ?? "");
  if (input.length > 2048) throw new Error("Wartość dla regex przekracza 2048 znaków.");
  let expression;
  try {
    expression = new RegExp(pattern, flags);
  } catch {
    throw new Error("Niepoprawny wzorzec regex.");
  }
  const match = input.match(expression);
  return match;
}

function assertSafeRegex(pattern) {
  return;
  if (/\\[1-9]|\(\?/.test(pattern)) {
    throw new Error("Regex nie obsługuje backreference ani lookaround; użyj prostego wzorca z grupami.");
  }
  const groups = [];
  let inCharacterClass = false;
  let escaped = false;
  let previousClosedGroup = null;
  for (let index = 0; index < pattern.length; index += 1) {
    const char = pattern[index];
    if (escaped) {
      escaped = false;
      if (groups.length && /[dDsSwWbB]/.test(char)) groups.at(-1).hasVariableToken = true;
      previousClosedGroup = null;
      continue;
    }
    if (char === "\\") { escaped = true; previousClosedGroup = null; continue; }
    if (char === "[") { inCharacterClass = true; previousClosedGroup = null; continue; }
    if (char === "]") { inCharacterClass = false; previousClosedGroup = null; continue; }
    if (inCharacterClass) continue;
    if (char === "(") { groups.push({ hasQuantifier: false, hasAlternation: false, hasVariableToken: false }); previousClosedGroup = null; continue; }
    if (char === "|") { if (groups.length) groups.at(-1).hasAlternation = true; previousClosedGroup = null; continue; }
    if (char === ")") {
      previousClosedGroup = groups.pop() ?? null;
      if (previousClosedGroup && groups.length) {
        const parent = groups.at(-1);
        parent.hasQuantifier ||= previousClosedGroup.hasQuantifier;
        parent.hasAlternation ||= previousClosedGroup.hasAlternation;
        parent.hasVariableToken ||= previousClosedGroup.hasVariableToken;
      }
      continue;
    }
    if (char === "*" || char === "+" || char === "?" || char === "{") {
      if (groups.length) groups.at(-1).hasQuantifier = true;
      if (previousClosedGroup && (previousClosedGroup.hasQuantifier || previousClosedGroup.hasAlternation || previousClosedGroup.hasVariableToken)) {
        throw new Error("Regex zawiera powtarzaną grupę o nieprzewidywalnym czasie; uprość wzorzec.");
      }
      previousClosedGroup = null;
      continue;
    }
    previousClosedGroup = null;
  }
}

function passesFilter(row, filter) {
  const actual = String(row[filter.column] ?? "");
  const expected = String(filter.value ?? "");
  switch (filter.operator) {
    case "equals": return actual === expected;
    case "not-equals": return actual !== expected;
    case "contains": return actual.toLocaleLowerCase().includes(expected.toLocaleLowerCase());
    case "not-empty": return actual.trim() !== "";
    default: throw new Error(`Nieobsługiwany filtr: ${filter.operator}`);
  }
}

function applyTransform(tags, transform) {
  const key = transform.key;
  if (!key) throw new Error("W preprocessingu wybierz zmapowany tag.");
  const value = String(tags[key] ?? "");
  if (transform.type === "regex") {
    const match = matchRegex(value, { ...transform, flags: "mi" });
    if (!match) return;
    tags[key] = String(transform.template ?? "").replace(/\$(\d+)|\$&/g, (_, groupIndex) =>
      groupIndex === undefined ? match[0] : (match[Number(groupIndex)] ?? "")).trim();
    return;
  }
  if (transform.type === "trim") tags[key] = value.trim().replace(/\s+/g, " ");
  else if (transform.type === "replace") tags[key] = value.replaceAll(transform.find ?? "", transform.replace ?? "");
  else if (transform.type === "upper") tags[key] = value.toLocaleUpperCase();
  else if (transform.type === "lower") tags[key] = value.toLocaleLowerCase();
  else if (transform.type === "capitalize-words") {
    tags[key] = value.toLocaleLowerCase("pl-PL").replace(/(^|[^\p{L}\p{N}]+)(\p{L})/gu, (_, separator, letter) => `${separator}${letter.toLocaleUpperCase("pl-PL")}`);
  } else if (transform.type === "capitalize-first") {
    tags[key] = value.toLocaleLowerCase("pl-PL").replace(/\p{L}/u, (letter) => letter.toLocaleUpperCase("pl-PL"));
  }
  else if (transform.type === "prefix") tags[key] = `${transform.value ?? ""}${value}`;
  else if (transform.type === "suffix") tags[key] = `${value}${transform.value ?? ""}`;
  else throw new Error(`Nieobsługiwana transformacja: ${transform.type}`);
  if (tags[key] === "") delete tags[key];
}

function parseCoordinate(value) {
  if (value === undefined || value === null || value === "") return null;
  const parsed = Number(String(value).replace(",", ".").trim());
  if (!Number.isFinite(parsed)) return null;
  return parsed;
}

export function parseOverpass(data) {
  const elements = typeof data === "string" ? JSON.parse(data).elements : data?.elements;
  if (!Array.isArray(elements)) throw new Error("Odpowiedź OSM nie zawiera tablicy elements.");
  const nodeLocations = new Map(elements.filter((item) => item.type === "node")
    .map((item) => [item.id, [Number(item.lon), Number(item.lat)]]));
    return elements.flatMap((element) => {
      if (element.type === "node") {
        return [{
          type: "node", id: Number(element.id), tags: { ...(element.tags ?? {}) }, lat: Number(element.lat), lon: Number(element.lon),
          geometry: { type: "Point", coordinates: [Number(element.lon), Number(element.lat)] }, version: element.version ?? 1,
          timestamp: element.timestamp, changeset: element.changeset, uid: element.uid, user: element.user, visible: element.visible ?? true,
        }];
    }
    if (element.type !== "way") return [];
    const points = (element.geometry ?? element.nodes?.map((id) => nodeLocations.get(id)).filter(Boolean) ?? [])
      .map((point) => Array.isArray(point) ? [Number(point[0]), Number(point[1])] : [Number(point.lon), Number(point.lat)]);
    const polygon = points.length >= 4 && samePoint(points[0], points.at(-1));
    const geometry = points.length ? {
      type: polygon ? "Polygon" : "LineString",
      coordinates: polygon ? [points] : points,
    } : element.center ? { type: "Point", coordinates: [Number(element.center.lon), Number(element.center.lat)] } : null;
    const center = element.center ?? (points.length ? { lon: points[0][0], lat: points[0][1] } : null);
    return [{
      type: "way", id: Number(element.id), tags: { ...(element.tags ?? {}) },
      lat: center ? Number(center.lat) : null, lon: center ? Number(center.lon) : null,
      geometry, nodes: [...(element.nodes ?? [])], version: element.version ?? 1,
      nodeCoordinates: (element.nodes?.length === points.length ? points : []).map(([lon, lat]) => ({ lon, lat })),
        timestamp: element.timestamp, changeset: element.changeset, uid: element.uid, user: element.user, visible: element.visible ?? true,
    }];
  });
}

function samePoint(a, b) { return a?.[0] === b?.[0] && a?.[1] === b?.[1]; }

export function normalize(value) {
  return String(value ?? "").replace(/[Łł]/g, (char) => char === "Ł" ? "L" : "l").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pl-PL").replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

export function distanceMeters(a, b) {
  if (![a?.lat, a?.lon, b?.lat, b?.lon].every(Number.isFinite)) return Infinity;
  const radians = (degrees) => degrees * Math.PI / 180;
  const latDelta = radians(b.lat - a.lat);
  const lonDelta = radians(b.lon - a.lon);
  const arc = Math.sin(latDelta / 2) ** 2 + Math.cos(radians(a.lat)) * Math.cos(radians(b.lat)) * Math.sin(lonDelta / 2) ** 2;
  return 6371000 * 2 * Math.atan2(Math.sqrt(arc), Math.sqrt(1 - arc));
}

export function matchRecords(govRows, osmRows, stages) {
  const unmatchedGov = new Set(govRows.map((item) => item.id));
  const unmatchedOsm = new Set(osmRows.map((item) => osmKey(item)));
  const matches = [];
  const ambiguous = new Map();
  const stageCounts = [];
  for (const stage of stages.filter((item) => item.enabled)) {
    const candidates = new Map();
    for (const gov of govRows) {
      if (!unmatchedGov.has(gov.id)) continue;
      const found = osmRows.filter((osm) => unmatchedOsm.has(osmKey(osm)) && stageMatches(gov, osm, stage));
      if (found.length) candidates.set(gov.id, found);
    }
    const claims = new Map();
    for (const [govId, found] of candidates) {
      if (found.length > 1) ambiguous.set(govId, { stage: stage.label ?? stage.type, candidates: found.map(osmKey), reason: "multiple-osm" });
      for (const osm of found) {
        const key = osmKey(osm);
        claims.set(key, [...(claims.get(key) ?? []), govId]);
      }
    }
    let count = 0;
    for (const [govId, found] of candidates) {
      if (found.length !== 1) continue;
      const osm = found[0];
      const key = osmKey(osm);
      if (claims.get(key)?.length !== 1) {
        ambiguous.set(govId, { stage: stage.label ?? stage.type, candidates: [key], reason: "multiple-gov" });
        continue;
      }
      matches.push({ gov: govRows.find((item) => item.id === govId), osm, stage: stage.label ?? stage.type });
      unmatchedGov.delete(govId);
      unmatchedOsm.delete(key);
      ambiguous.delete(govId);
      count += 1;
    }
    stageCounts.push({ stage: stage.label ?? stage.type, matches: count });
  }
  return {
    matches,
    unmatchedGov: govRows.filter((item) => unmatchedGov.has(item.id)),
    unmatchedOsm: osmRows.filter((item) => unmatchedOsm.has(osmKey(item))),
    ambiguous: govRows.filter((item) => ambiguous.has(item.id)).map((gov) => ({ gov, ...ambiguous.get(gov.id) })),
    stageCounts,
  };
}

function stageMatches(gov, osm, stage) {
  if (stage.type === "name") {
    const names = ["name", "official_name", "short_name"].map((key) => normalize(gov.tags?.[key])).filter(Boolean);
    const osmNames = ["name", "official_name", "short_name", "alt_name"].map((key) => normalize(osm.tags?.[key])).filter(Boolean);
    return names.some((name) => osmNames.includes(name));
  }
  if (stage.type === "address") {
    const fields = stage.fields ?? [];
    return fields.length > 0 && fields.every((key) => normalize(gov.tags?.[key]) && normalize(gov.tags[key]) === normalize(osm.tags?.[key]));
  }
  if (stage.type === "tags") {
    const fields = stage.fields ?? [];
    return fields.length > 0 && fields.every((key) => gov.tags?.[key] && normalize(gov.tags[key]) === normalize(osm.tags?.[key]));
  }
  if (stage.type === "location") return distanceMeters(gov, osm) <= Number(stage.toleranceM ?? 100);
  return false;
}

function osmKey(item) { return `${item.type}/${item.id}`; }

export function mergeTags(osmTags, govTags, mergeConfig = {}) {
  const original = osmTags ?? {};
  const result = { ...original };
  const osmHasAddress = Object.entries(original).some(([key, value]) => key.startsWith("addr:") && value);
  for (const [key, value] of Object.entries(govTags ?? {})) {
    if (!value) continue;
    const isAddress = key.startsWith("addr:");
    if (isAddress && !osmHasAddress && !mergeConfig.addAddressWhenMissing && !mergeConfig.updateAddress) continue;
    if (!mergeConfig.updateAddress && ADDRESS_KEYS.has(key) && result[key]) continue;
    if ((mergeConfig.conflict === "keep-osm" || mergeConfig.conflict === "fill-empty") && result[key]) continue;
    if (mergeConfig.conflict === "keep-gov" || mergeConfig.conflict === "overwrite" || !result[key]) result[key] = String(value);
  }
  for (const operation of mergeConfig.operations ?? []) {
    if (operation.type === "delete") {
      if (Object.hasOwn(result, operation.key) && (operation.value === "*" || result[operation.key] === operation.value)) {
        delete result[operation.key];
      }
    } else if (operation.type === "set" && operation.key) {
      if (operation.value !== "") result[operation.key] = String(operation.value ?? "");
      else delete result[operation.key];
    } else if (operation.type === "replace" && operation.key && Object.hasOwn(result, operation.key)) {
      result[operation.key] = String(result[operation.key]).replaceAll(operation.find ?? "", operation.replace ?? "");
    }
  }
  Object.assign(result, mergeConfig.sourceTags ?? {});
  if (mergeConfig.source) result[mergeConfig.sourceKey || "source:office"] = String(mergeConfig.source);
  const changed = Object.fromEntries(Object.entries(result).filter(([key, value]) => value !== original[key]));
  const removed = Object.keys(original).filter((key) => !Object.hasOwn(result, key));
  return { tags: result, changed, removed };
}

export function osmXml(objects, action) {
  const objectAction = action === "modify" ? "modify" : null;
  const serializedNodes = new Map(objects.filter((object) => object.type === "node")
    .map((object) => [object.id, { object, action: objectAction }]));
  for (const way of objects.filter((object) => object.type === "way")) {
    (way.nodes ?? []).forEach((id, index) => {
      if (serializedNodes.has(id)) return;
      const location = way.nodeCoordinates?.[index];
      if (!location || !Number.isFinite(location.lat) || !Number.isFinite(location.lon)) return;
      serializedNodes.set(id, { object: {
        type: "node", id, version: 1, lat: location.lat, lon: location.lon,
        tags: {}, visible: true,
      }, action: null });
    });
  }
  const nodes = [...serializedNodes.values()].map(({ object, action }) => serializeObject(object, action));
  const ways = objects.filter((object) => object.type === "way").map((object) => serializeObject(object, objectAction));
  const body = [...nodes, ...ways].join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>\n<osm version="0.6" generator="gov-osm-merger">\n<note>The data included in this document is from www.openstreetmap.org. The data is made available under ODbL.</note>\n${body}\n</osm>\n`;
}

function serializeObject(object, action = null) {
  const metadata = [
    ["id", object.id], ["action", action], ["timestamp", object.timestamp ?? "1970-01-01T00:00:00Z"],
    ["uid", object.uid ?? 0], ["user", object.user ?? ""], ["visible", object.visible ?? true],
    ["version", Number(object.version ?? 1)], ["changeset", object.changeset ?? 0],
  ].filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value]) => `${key}="${xmlEscape(value)}"`).join(" ");
  const attrs = object.type === "node"
    ? `${metadata} lat="${xmlEscape(object.lat ?? object.geometry?.coordinates?.[1])}" lon="${xmlEscape(object.lon ?? object.geometry?.coordinates?.[0])}"`
    : metadata;
  const tags = Object.entries(object.tags ?? {}).filter(([, value]) => value !== "" && value !== null && value !== undefined)
    .map(([key, value]) => `      <tag k="${xmlEscape(key)}" v="${xmlEscape(value)}"/>`).join("\n");
  if (object.type === "way") {
    const nodes = (object.nodes ?? []).map((id) => `      <nd ref="${xmlEscape(id)}"/>`).join("\n");
    return `    <way ${attrs}>\n${[nodes, tags].filter(Boolean).join("\n")}\n    </way>`;
  }
  const location = object.geometry?.coordinates ?? [object.lon, object.lat];
  const [lon, lat] = location;
  return `    <node ${attrs}>\n${tags}\n    </node>`;
}

function xmlEscape(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&apos;");
}

export function nominatimQueryForRow(row) {
  const addressOrder = ["addr:postcode", "addr:city", "addr:place", "addr:street", "addr:housenumber"];
  const addressParts = addressOrder.map((key) => row.tags?.[key]).filter(Boolean);
  const remainingAddressParts = Object.entries(row.tags ?? {})
    .filter(([key, value]) => key.startsWith("addr:") && value && !addressOrder.includes(key))
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([, value]) => value);
  return [...addressParts, ...remainingAddressParts].join(" ");
}

export function nominatimDebugUrl(query) {
  const url = new URL("https://nominatim.openstreetmap.org/ui/search.html");
  url.searchParams.set("q", query);
  return url.toString();
}

export function govNoCoordCsv(govRows, sourceRows = []) {
  const sourceByRow = new Map(sourceRows.map((row) => [row.__row, row]));
  const sourceColumns = sourceRows.headers ?? Object.keys(sourceRows[0] ?? {}).filter((key) => key !== "__row");
  const tagColumns = [...new Set(govRows.flatMap((row) => Object.keys(row.tags ?? {})))].map((key) => `tag:${key}`);
  const headers = [];
  const used = new Set();
  for (const header of [...sourceColumns, ...tagColumns, "gov_source_row", "nominatim_query", "nominatim_url"]) {
    let uniqueHeader = header;
    while (used.has(uniqueHeader)) uniqueHeader = `_${uniqueHeader}`;
    used.add(uniqueHeader);
    headers.push(uniqueHeader);
  }
  const quote = (value) => {
    const text = String(value ?? "");
    return /[\",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };
  const lines = [headers.map(quote).join(",")];
  for (const gov of govRows) {
    const source = sourceByRow.get(gov.sourceRow) ?? {};
    const query = nominatimQueryForRow(gov);
    const values = [
      ...sourceColumns.map((column) => source[column] ?? ""),
      ...tagColumns.map((column) => gov.tags?.[column.slice(4)] ?? ""),
      gov.sourceRow ?? "",
      query,
      query ? nominatimDebugUrl(query) : "",
    ];
    lines.push(values.map(quote).join(","));
  }
  return `${lines.join("\r\n")}\r\n`;
}

export async function geocodeMissingCoordinates(govRows, config, { fetchImpl = fetch, onProgress = () => {}, signal } = {}) {
  if (!config.enabled) return govRows;
  const result = govRows.map((row) => ({ ...row }));
  const cache = config.cache ??= {};
  const missing = result.filter((row) => !Number.isFinite(row.lat) || !Number.isFinite(row.lon));
  let lastRequestAt = 0;
  for (let index = 0; index < missing.length; index += 1) {
    const row = missing[index];
    const query = nominatimQueryForRow(row);
    const cacheKey = `addr:${normalize(query)}`;
    const cached = cache[row.id] ?? (query ? cache[cacheKey] : null);
    if (cached) {
      if (!cached.notFound) {
        row.lat = Number(cached.lat);
        row.lon = Number(cached.lon);
      }
    } else if (query) {
      const waitMs = lastRequestAt ? Math.max(0, 1100 - (Date.now() - lastRequestAt)) : 0;
      if (waitMs) await new Promise((resolve) => setTimeout(resolve, waitMs));
      const url = new URL(config.endpoint || DEFAULT_CONFIG.nominatim.endpoint);
      url.searchParams.set("q", query);
      url.searchParams.set("format", "jsonv2");
      url.searchParams.set("limit", "1");
      const response = await fetchImpl(url, { signal, headers: { Accept: "application/json" } });
      lastRequestAt = Date.now();
      if (!response.ok) throw new Error(`Nominatim zwrócił HTTP ${response.status}.`);
      const hits = await response.json();
      if (hits[0]) {
        row.lat = Number(hits[0].lat);
        row.lon = Number(hits[0].lon);
        const coordinates = { lat: row.lat, lon: row.lon };
        cache[cacheKey] = coordinates;
        cache[row.id] = coordinates;
      } else {
        const miss = { notFound: true };
        cache[cacheKey] = miss;
        cache[row.id] = miss;
      }
    }
    onProgress({ done: index + 1, total: missing.length, row });
  }
  config.cache = cache;
  return result;
}

export async function geocodeUnmatchedAfterStages(govRows, osmRows, stages, config, options = {}) {
  if (!config.enabled || !stages.some((stage) => stage.enabled && stage.type === "location")) return govRows;
  const locationIndex = stages.findIndex((stage) => stage.enabled && stage.type === "location");
  const earlierStages = stages.slice(0, locationIndex).filter((stage) => stage.enabled);
  const unmatched = matchRecords(govRows, osmRows, earlierStages).unmatchedGov;
  if (!unmatched.length) return govRows;
  const geocoded = await geocodeMissingCoordinates(unmatched, config, options);
  const byId = new Map(geocoded.map((row) => [row.id, row]));
  return govRows.map((row) => byId.get(row.id) ?? row);
}