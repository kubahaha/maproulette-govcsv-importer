import JSZip from "jszip";

const REQUIRED_FILES = ["config.json", "gov.csv", "osm.json"];
const MAX_ARCHIVE_BYTES = 100 * 1024 * 1024;
const MAX_UNCOMPRESSED_BYTES = 250 * 1024 * 1024;

export async function createSessionZip(config, csvText, osmText) {
  if (!csvText || !osmText) throw new Error("Sesja wymaga gov.csv i osm.json.");
  const zip = new JSZip();
  zip.file("config.json", JSON.stringify(config, null, 2));
  zip.file("gov.csv", csvText);
  zip.file("osm.json", osmText);
  zip.file("session-meta.json", JSON.stringify({
    name: config.name ?? "",
    exportedAt: new Date().toISOString(),
    format: "gov-osm-merger-session",
  }, null, 2));
  return zip.generateAsync({ type: "uint8array", compression: "DEFLATE", compressionOptions: { level: 6 } });
}

export async function readSessionZip(input) {
  const compressedSize = input?.size ?? input?.byteLength ?? 0;
  if (compressedSize > MAX_ARCHIVE_BYTES) throw new Error("ZIP przekracza limit 100 MB.");
  const zip = await JSZip.loadAsync(input);
  const entries = Object.values(zip.files).filter((entry) => !entry.dir);
  const totalSize = entries.reduce((sum, entry) => sum + (entry._data?.uncompressedSize ?? 0), 0);
  if (totalSize > MAX_UNCOMPRESSED_BYTES) throw new Error("Rozpakowana sesja przekracza limit 250 MB.");
  const files = Object.fromEntries(REQUIRED_FILES.map((name) => [name, zip.file(name)]));
  const missing = Object.entries(files).filter(([, entry]) => !entry).map(([name]) => name);
  if (missing.length) throw new Error(`Brak wymaganych plików: ${missing.join(", ")}.`);
  const [configText, csvText, osmText] = await Promise.all(REQUIRED_FILES.map((name) => files[name].async("text")));
  let config;
  try { config = JSON.parse(configText); }
  catch { throw new Error("config.json nie zawiera poprawnego JSON."); }
  if (config.version !== 1) throw new Error("Nieobsługiwana wersja konfiguracji ZIP.");
  return { config, csvText, osmText };
}