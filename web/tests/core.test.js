import test from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_CONFIG, normalizeConfig, parseCsv, prepareGovRows, mappedTagKeys, buildGovPreview, selectGovPreviewSample, parseOverpass, normalize, distanceMeters,
  matchRecords, mergeTags, osmXml, govNoCoordCsv, nominatimQueryForRow, nominatimDebugUrl,
  geocodeMissingCoordinates, geocodeUnmatchedAfterStages,
} from "../src/core.js";
import { createSessionZip, readSessionZip } from "../src/session.js";

test("CSV parser respects quoted delimiters, escaped quotes and Polish text", () => {
  const rows = parseCsv('Nazwa;Miasto;Uwagi\r\n"Ośrodek; ""A""";Łódź;tekst\r\n', { delimiter: ";" });
  assert.equal(rows[0].Nazwa, 'Ośrodek; "A"');
  assert.equal(rows[0].Miasto, "Łódź");
});

test("default Overpass endpoint uses the configured CORS Worker", () => {
  assert.equal(DEFAULT_CONFIG.overpass.endpoint, "https://gov-osm-overpass.kuba-medrek.workers.dev/api/overpass");
});

test("legacy address unit mapping migrates to addr:place and regex defaults to im", () => {
  const config = normalizeConfig({ csv: { mapping: { address: { type: "address", unit: "Miejsce", city: { column: "Miasto", regex: "^.{6}(.+)$" } } } } });
  assert.equal(config.csv.mapping["addr:place"], "Miejsce");
  assert.equal(config.csv.mapping["addr:city"], "Miasto");
  assert.equal(config.csv.mapping.address, undefined);
  assert.ok(config.csv.transforms.some((transform) => transform.key === "addr:city" && transform.pattern === "^.{6}(.+)$" && transform.flags === "im"));
  const prepared = prepareGovRows([{ __row: 2, Miasto: "90-001 Łódź", Miejsce: "Centrum" }], config);
  assert.equal(prepared.rows[0].tags["addr:city"], "Łódź");
  assert.equal(prepared.rows[0].tags["addr:place"], "Centrum");
});

test("CSV preparation applies safe mapping, filters, transforms and stable IDs", () => {
  const rows = parseCsv("Name,City,Street,Number,Lat,Lon,Active\nUrząd A,Łódź,Piotrkowska,1,51.77,19.45,yes\nUrząd B,Łódź,,,bad,,no");
  const result = prepareGovRows(rows, {
    csv: {
      filters: [{ column: "Active", operator: "equals", value: "yes" }],
      mapping: {
        name: "Name", "addr:city": "City", "addr:street": "Street",
        "addr:housenumber": "Number", __lat: "Lat", __lon: "Lon",
      },
      transforms: [{ type: "prefix", key: "addr:street", value: "ul. " }],
    },
  });
  assert.equal(result.rows.length, 1);
  assert.equal(result.rows[0].id, -1000001);
  assert.equal(result.rows[0].tags["addr:street"], "ul. Piotrkowska");
  assert.equal(result.rows[0].lat, 51.77);
  assert.equal(result.rows[0].lon, 19.45);
  assert.equal(rows[0].Street, "Piotrkowska");
});

test("CSV mapping concatenates multiple source columns into one tag", () => {
  const rows = [{ __row: 2, Street: "Leśna", Number: "12A", City: "Łódź" }];
  const result = prepareGovRows(rows, {
    csv: {
      mapping: {
        address: { type: "concat", columns: ["Street", "Number", "City"], separator: ", " },
      },
    },
  });
  assert.equal(result.rows[0].tags.address, "Leśna, 12A, Łódź");
});

test("address builder fills addr tags from dedicated source columns", () => {
  const rows = [{ __row: 2, Miasto: "90-001 Łódź", Ulica: "ul. Piotrkowska 12A", Numer: "12A", Kod: "90-001", Miejsce: "Centrum" }];
  const result = prepareGovRows(rows, {
    csv: {
      address: {
        city: { column: "Miasto", regexIn: "^.{6}(.+)$", regexOut: "$1", flags: "im" },
        street: { column: "Ulica", regexIn: "^ul\\.\\s*(.+?)\\s+\\d+[A-Za-z]?$", regexOut: "$1", flags: "im" },
        housenumber: { column: "Numer", regexIn: "^(\\d+[A-Za-z]?)$", regexOut: "$1", flags: "im" },
        postcode: "Kod",
        place: "Miejsce",
      },
    },
  });
  assert.equal(result.rows[0].tags["addr:city"], "Łódź");
  assert.equal(result.rows[0].tags["addr:street"], "Piotrkowska");
  assert.equal(result.rows[0].tags["addr:housenumber"], "12A");
  assert.equal(result.rows[0].tags["addr:postcode"], "90-001");
  assert.equal(result.rows[0].tags["addr:place"], "Centrum");
  assert.equal(result.rows[0].tags["addr:unit"], undefined);
});

test("address mapping keeps populated addr tags when its row key is itself addr:city", () => {
  const result = prepareGovRows([{ __row: 2, City: "Łódź", Place: "Centrum" }], {
    csv: { mapping: { "addr:city": { type: "address", city: "City", place: "Place" } } },
  });
  assert.equal(result.rows[0].tags["addr:city"], "Łódź");
  assert.equal(result.rows[0].tags["addr:place"], "Centrum");
});

test("preprocessing target keys expand address mappings and sort OSM keys", () => {
  const tags = mappedTagKeys({ mapping: {
    website: "URL",
    address: { type: "address", city: { column: "Miasto" }, housenumber: { column: "Numer" } },
    name: "Nazwa",
  } });
  assert.deepEqual(tags, ["addr:city", "addr:housenumber", "name", "website"]);
  assert.ok(!tags.includes("address"));
});

test("GOV preview sampling is repeatable, pages are disjoint, and page indexes wrap", () => {
  const rows = Array.from({ length: 23 }, (_, index) => ({ id: index }));
  const first = selectGovPreviewSample(rows, 0);
  const second = selectGovPreviewSample(rows, 1);
  assert.deepEqual(first, selectGovPreviewSample(rows, 0));
  assert.equal(first.length, 10);
  assert.equal(second.length, 10);
  assert.ok(second.every((row) => !first.includes(row)));
  assert.deepEqual(selectGovPreviewSample(rows, 3), selectGovPreviewSample(rows, 0));
  assert.deepEqual(selectGovPreviewSample(rows.slice(0, 8), 9), rows.slice(0, 8));
});

test("GOV preview includes all CSV columns and prepared address/tag values", () => {
  const source = parseCsv("Name,Full address,Raw note\nPoint,90-001 Łódź,keep me");
  const config = { csv: { mapping: {
    name: "Name",
    address: { type: "address", city: { column: "Full address", regexIn: "^.{6}(.+)$", regexOut: "$1" } },
  } } };
  const prepared = prepareGovRows(source, config).rows;
  const preview = buildGovPreview(source, prepared, config);
  assert.deepEqual(preview.sourceColumns, ["Name", "Full address", "Raw note"]);
  assert.ok(preview.tagColumns.includes("name"));
  assert.ok(preview.tagColumns.includes("addr:city"));
  assert.equal(preview.rows[0].source["Raw note"], "keep me");
  assert.equal(preview.rows[0].prepared.tags["addr:city"], "Łódź");
});

test("address regex replaces matching text with a template and uses multiline/case-insensitive flags", () => {
  const rows = [{ __row: 2, City: "90-001 Łódź" }];
  const result = prepareGovRows(rows, { csv: { address: {
    city: { column: "City", regexIn: "^.{6}(.+)$", regexOut: "$1", flags: "im" },
  } } });
  assert.equal(result.rows[0].tags["addr:city"], "Łódź");
});

test("Nominatim caches by full addr tag query and reuses the cached coordinates", async () => {
  let calls = 0;
  const rows = [
    { id: -1, lat: null, lon: null, tags: { "addr:postcode": "90-001", "addr:city": "Łódź", "addr:street": "Piotrkowska", "addr:housenumber": "1" } },
    { id: -2, lat: null, lon: null, tags: { "addr:postcode": "90-001", "addr:city": "Łódź", "addr:street": "Piotrkowska", "addr:housenumber": "1" } },
  ];
  const config = { enabled: true, endpoint: "https://nominatim.test/search" };
  const fetchImpl = async (url) => {
    calls += 1;
    assert.equal(new URL(url).searchParams.get("q"), "90-001 Łódź Piotrkowska 1");
    return new Response(JSON.stringify([{ lat: "51.77", lon: "19.45" }]), { status: 200 });
  };
  const result = await geocodeMissingCoordinates(rows, config, { fetchImpl });
  assert.equal(calls, 1);
  assert.deepEqual(result.map(({ lat, lon }) => [lat, lon]), [[51.77, 19.45], [51.77, 19.45]]);
  assert.ok(Object.keys(config.cache).some((key) => key.startsWith("addr:")));
});

test("Nominatim is not queried for records matched in earlier stages", async () => {
  let calls = 0;
  const gov = [{ id: -1, lat: null, lon: null, tags: { name: "Punkt", "addr:city": "Łódź" } }];
  const osm = [{ type: "node", id: 2, lat: 51.77, lon: 19.45, tags: { name: "Punkt", "addr:city": "Łódź" } }];
  const result = await geocodeUnmatchedAfterStages(gov, osm, [
    { type: "name", enabled: true },
    { type: "location", enabled: true, toleranceM: 100 },
  ], { enabled: true, endpoint: "https://nominatim.test/search" }, {
    fetchImpl: async () => { calls += 1; throw new Error("Should not fetch matched row"); },
  });
  assert.equal(calls, 0);
  assert.equal(result[0].lat, null);
});

test("Nominatim sends all available addr tags in its lookup query", async () => {
  const rows = [{ id: -3, lat: null, lon: null, tags: {
    "addr:postcode": "90-001", "addr:city": "Łódź", "addr:place": "Śródmieście",
    "addr:street": "Piotrkowska", "addr:housenumber": "1", "addr:place": "Centrum", "addr:district": "Śródmieście",
  } }];
  let query;
  await geocodeMissingCoordinates(rows, { enabled: true, endpoint: "https://nominatim.test/search" }, {
    fetchImpl: async (url) => {
      query = new URL(url).searchParams.get("q");
      return new Response(JSON.stringify([]), { status: 200 });
    },
  });
  assert.equal(query, "90-001 Łódź Centrum Piotrkowska 1 Śródmieście");
});

test("gov_no_coord CSV preserves source and prepared data with a Nominatim debug link", () => {
  const sourceRows = parseCsv('Nazwa;Miasto;Notatka\n"Urząd, A";Łódź;"tekst; cytowany"', { delimiter: ";" });
  const govRows = [{ id: -1, sourceRow: 2, tags: {
    name: "Urząd, A", "addr:postcode": "90-001", "addr:city": "Łódź", "addr:street": "Piotrkowska", "addr:housenumber": "1",
  } }];
  const csv = govNoCoordCsv(govRows, sourceRows);
  assert.match(csv, /Nazwa,Miasto,Notatka/);
  assert.match(csv, /"Urząd, A",Łódź,tekst; cytowany/);
  assert.match(csv, /90-001 Łódź Piotrkowska 1/);
  assert.match(csv, /https:\/\/nominatim\.openstreetmap\.org\/ui\/search\.html\?q=/);
  assert.equal(nominatimQueryForRow(govRows[0]), "90-001 Łódź Piotrkowska 1");
  assert.equal(new URL(nominatimDebugUrl("Łódź Piotrkowska 1")).searchParams.get("q"), "Łódź Piotrkowska 1");
});

test("preprocessing runs in order on the mapped tag value", () => {
  const rows = [{ __row: 2, Address: "  UL.  Polna   8 " }];
  const result = prepareGovRows(rows, {
    csv: {
      mapping: { address: "Address" },
      transforms: [
        { type: "trim", key: "address" },
        { type: "replace", key: "address", find: "UL.", replace: "ul." },
      ],
      filters: [{ column: "address", operator: "equals", value: "ul. Polna 8" }],
    },
  });
  assert.equal(result.rows.length, 1);
  assert.equal(result.rows[0].tags.address, "ul. Polna 8");
  assert.equal(rows[0].Address, "  UL.  Polna   8 ");
});

test("space cleanup trims edges and collapses repeated whitespace in place", () => {
  const rows = [{ __row: 2, Name: "  Aa  bb\t cc  " }];
  const result = prepareGovRows(rows, {
    csv: { mapping: { name: "Name" }, transforms: [{ type: "trim", key: "name" }] },
  });
  assert.equal(result.rows[0].tags.name, "Aa bb cc");
  assert.equal(rows[0].Name, "  Aa  bb\t cc  ");
});

test("replace transform preserves and replaces literal spaces", () => {
  const result = prepareGovRows([{ __row: 2, Name: "Jana  Pawła II" }], {
    csv: { mapping: { name: "Name" }, transforms: [{ type: "replace", key: "name", find: " ", replace: "_" }] },
  });
  assert.equal(result.rows[0].tags.name, "Jana__Pawła_II");
});

test("CSV preprocessing regex composes groups into the mapped tag after mapping", () => {
  const rows = parseCsv('Nazwa,Adres\nPunkt,"ul. Leśna 12A, lokal 4"');
  const result = prepareGovRows(rows, {
    csv: {
      mapping: { name: "Nazwa", address: "Adres" },
      transforms: [{ type: "regex", key: "address", pattern: "^ul\\.\\s+(.+?)\\s+(\\d+[A-Za-z]?)", template: "$1 / $2" }],
    },
  });
  assert.equal(result.errors.length, 0);
  assert.equal(result.rows[0].tags.address, "Leśna / 12A");
  assert.equal(rows[0].Adres, "ul. Leśna 12A, lokal 4");
});

test("preprocessing regex supports case-insensitive matching and leaves unmatched values unchanged", () => {
  const rows = [{ __row: 2, Address: "UL. Polna 8" }, { __row: 3, Address: "bez adresu" }];
  const result = prepareGovRows(rows, {
    csv: { mapping: { street: "Address" }, transforms: [{ type: "regex", key: "street", pattern: "^ul\\.\\s+(.+?)\\s+\\d+$", flags: "i", template: "$1" }] },
  });
  assert.equal(result.rows[0].tags.street, "Polna");
  assert.equal(result.rows[1].tags.street, "bez adresu");
  assert.equal(rows[0].Address, "UL. Polna 8");
});

test("preprocessing regex always uses case-insensitive multiline flags", () => {
  const result = prepareGovRows([{ __row: 2, Address: "not an address\nUL. Polna 8" }], {
    csv: { mapping: { street: "Address" }, transforms: [{
      type: "regex", key: "street", pattern: "^ul\\.\\s+(Polna\\s+8)$", flags: "g", template: "$1",
    }] },
  });
  assert.equal(result.errors.length, 0);
  assert.equal(result.rows[0].tags.street, "Polna 8");
});

test("Overpass parser preserves node and closed way geometry", () => {
  const objects = parseOverpass({ elements: [
    { type: "node", id: 7, lat: 52, lon: 21, version: 2, timestamp: "2023-08-25T07:20:18Z", changeset: 140356235, uid: 5060085, user: "Mapper", tags: { name: "Punkt" } },
    { type: "way", id: 8, nodes: [1, 2, 3, 1], geometry: [
      { lat: 52, lon: 21 }, { lat: 52, lon: 21.001 }, { lat: 52.001, lon: 21.001 }, { lat: 52, lon: 21 },
    ], tags: { name: "Budynek" } },
  ] });
  assert.equal(objects[0].geometry.type, "Point");
  assert.equal(objects[0].version, 2);
  assert.equal(objects[0].timestamp, "2023-08-25T07:20:18Z");
  assert.equal(objects[0].changeset, 140356235);
  assert.equal(objects[0].uid, 5060085);
  assert.equal(objects[0].user, "Mapper");
  assert.equal(objects[1].geometry.type, "Polygon");
  assert.deepEqual(objects[1].nodes, [1, 2, 3, 1]);
  assert.deepEqual(objects[1].nodeCoordinates, [
    { lon: 21, lat: 52 }, { lon: 21.001, lat: 52 }, { lon: 21.001, lat: 52.001 }, { lon: 21, lat: 52 },
  ]);
});

test("way modify export includes referenced geometry nodes for JOSM", () => {
  const way = {
    type: "way", id: 8, version: 3, nodes: [101, 102, 101],
    nodeCoordinates: [{ lon: 21, lat: 52 }, { lon: 21.001, lat: 52.001 }, { lon: 21, lat: 52 }],
    tags: { name: "Budynek" },
  };
  const xml = osmXml([way], "modify");
  assert.match(xml, /<node id="101"[^>]*lat="52" lon="21"/);
  assert.match(xml, /<node id="102"[^>]*lat="52\.001" lon="21\.001"/);
  assert.match(xml, /<way id="8"[^>]*action="modify"/);
  assert.match(xml, /<nd ref="101"\/>[\s\S]*<nd ref="102"\/>[\s\S]*<nd ref="101"\/>/);
  assert.equal((xml.match(/<node id="101"/g) ?? []).length, 1);
  assert.doesNotMatch(xml, /<node id="101"[^>]*action="modify"/);
});

test("name normalization and Haversine distance use locale-insensitive comparisons", () => {
  assert.equal(normalize("  Łódź, Śródmieście! "), "lodz srodmiescie");
  assert.ok(Math.abs(distanceMeters({ lat: 0, lon: 0 }, { lat: 0, lon: 1 }) - 111195) < 100);
});

test("matching uses ordered stages, rejects multiple candidates and prevents OSM reuse", () => {
  const gov = [
    { id: -1, tags: { name: "Dom kultury" } },
    { id: -2, tags: { name: "Dom kultury" } },
    { id: -3, tags: { name: "Szkoła" } },
  ];
  const osm = [
    { type: "node", id: 1, tags: { name: "Dom kultury" } },
    { type: "node", id: 2, tags: { name: "Dom kultury" } },
    { type: "node", id: 3, tags: { name: "Szkoła" } },
  ];
  const result = matchRecords(gov, osm, [{ type: "name", enabled: true }]);
  assert.deepEqual(result.matches.map(({ gov: item }) => item.id), [-3]);
  assert.equal(result.matches[0].osm.id, 3);
  assert.equal(result.ambiguous.length, 2);
  assert.equal(result.unmatchedOsm.length, 2);
});

test("matching rejects two GOV records claiming the same OSM object", () => {
  const gov = [{ id: -1, tags: { name: "Punkt" } }, { id: -2, tags: { name: "Punkt" } }];
  const osm = [{ type: "node", id: 1, tags: { name: "Punkt" } }];
  const result = matchRecords(gov, osm, [{ type: "name", enabled: true }]);
  assert.equal(result.matches.length, 0);
  assert.equal(result.ambiguous.length, 2);
});

test("ordered address stages can first match city and then city plus street", () => {
  const gov = [
    { id: -1, tags: { "addr:city": "Łódź", "addr:street": "Piotrkowska" } },
    { id: -2, tags: { "addr:city": "Łódź", "addr:street": "Zielona" } },
  ];
  const osm = [
    { type: "node", id: 11, tags: { "addr:city": "Łódź", "addr:street": "Piotrkowska" } },
    { type: "node", id: 12, tags: { "addr:city": "Łódź", "addr:street": "Zielona" } },
  ];
  const results = matchRecords(gov, osm, [
    { type: "address", enabled: true, label: "Miasto", fields: ["addr:city"] },
    { type: "address", enabled: true, label: "Miasto i ulica", fields: ["addr:city", "addr:street"] },
  ]);
  assert.equal(results.matches.length, 2);
  assert.equal(results.ambiguous.length, 0);
  assert.ok(results.matches.every((match) => match.stage === "Miasto i ulica"));
});

test("tag operations keep existing OSM address and expose explicit edits", () => {
  const result = mergeTags(
    { name: "Wartość OSM", "addr:city": "Łódź", amenity: "library", website: "http://x" },
    { name: "Wartość GOV", "addr:city": "Pabianice", phone: "123" },
    { conflict: "keep-gov", operations: [
      { type: "delete", key: "amenity", value: "*" },
      { type: "replace", key: "website", find: "http:", replace: "https:" },
      { type: "set", key: "office", value: "government" },
    ],
    },
  );
  assert.equal(result.tags["addr:city"], "Łódź");
  assert.equal(result.tags.name, "Wartość GOV");
  assert.equal(result.tags.website, "https://x");
  assert.deepEqual(result.removed, ["amenity"]);
  assert.equal(result.changed.phone, "123");
});

test("address tags are not added to address-less OSM by default", () => {
  const result = mergeTags({ name: "Punkt" }, {
    "addr:city": "Łódź", "addr:street": "Piotrkowska", "addr:housenumber": "1",
  }, { conflict: "keep-osm" });
  assert.deepEqual(Object.keys(result.tags).filter((key) => key.startsWith("addr:")), []);
});

test("address toggle adds all GOV address tags when OSM has no address", () => {
  const result = mergeTags({ name: "Punkt" }, {
    "addr:city": "Łódź", "addr:street": "Piotrkowska", "addr:housenumber": "1",
  }, { conflict: "keep-osm", addAddressWhenMissing: true });
  assert.equal(result.tags["addr:city"], "Łódź");
  assert.equal(result.tags["addr:street"], "Piotrkowska");
  assert.equal(result.tags["addr:housenumber"], "1");
});

test("address toggle does not overwrite a partially mapped OSM address", () => {
  const result = mergeTags({ "addr:city": "Łódź" }, {
    "addr:city": "Pabianice", "addr:street": "Piotrkowska",
  }, { conflict: "keep-osm", addAddressWhenMissing: true });
  assert.equal(result.tags["addr:city"], "Łódź");
  assert.equal(result.tags["addr:street"], "Piotrkowska");
});

test("merge reports no changes when operations leave original OSM tags intact", () => {
  const original = { name: "Punkt", amenity: "office" };
  const result = mergeTags(original, {}, { operations: [
    { type: "delete", key: "amenity", value: "*" },
    { type: "set", key: "amenity", value: "office" },
    { type: "set", key: "name", value: "Punkt" },
  ] });
  assert.deepEqual(result.tags, original);
  assert.deepEqual(result.changed, {});
  assert.deepEqual(result.removed, []);
});

test("source description fills its configurable source tag", () => {
  const result = mergeTags({}, { name: "Punkt" }, { source: "Baza GOV", sourceKey: "source:website" });
  assert.equal(result.tags["source:website"], "Baza GOV");
});

test("source description defaults to source:office", () => {
  const result = mergeTags({}, { name: "Punkt" }, { source: "Baza GOV" });
  assert.equal(result.tags["source:office"], "Baza GOV");
});

test("legacy sourceTags migrate their key and value to source fields", () => {
  const config = normalizeConfig({ merge: { sourceTags: { "source:website": "Rejestr WWW" } } });
  assert.equal(config.merge.sourceKey, "source:website");
  assert.equal(config.merge.source, "Rejestr WWW");
});

test("OSM XML escapes tag content", () => {
  const object = { type: "node", id: -7, lat: 52, lon: 21, tags: { name: "Urząd & <miejsce>" } };
  const xml = osmXml([object], "create");
  assert.match(xml, /<osm version="0.6"/);
  assert.match(xml, /Urząd &amp; &lt;miejsce&gt;/);
});

test("modify export preserves OSM metadata and base version", () => {
  const object = {
    type: "node", id: 42, version: 2, timestamp: "2023-08-25T07:20:18Z", uid: 5060085,
    user: "Piotr Strębski", visible: true, changeset: 140356235, lat: 52.5926759, lon: 21.4509884,
    tags: { name: "Punkt" },
  };
  const modifyXml = osmXml([object], "modify");
  const createXml = osmXml([object], "create");
  assert.match(modifyXml, /id="42" action="modify" timestamp="2023-08-25T07:20:18Z" uid="5060085" user="Piotr Strębski" visible="true" version="2" changeset="140356235" lat="52\.5926759" lon="21\.4509884"/);
  assert.match(createXml, /id="42" timestamp="2023-08-25T07:20:18Z" uid="5060085" user="Piotr Strębski" visible="true" version="2" changeset="140356235" lat="52\.5926759" lon="21\.4509884"/);
  assert.doesNotMatch(createXml, /action="modify"/);
  assert.equal((modifyXml.match(/ lat=/g) ?? []).length, 1);
});

test("session ZIP round-trips config and both input files", async () => {
  const config = { version: 1, name: "Próba", csv: { delimiter: ";" } };
  const csv = "Nazwa;Miasto\nUrząd;Łódź\n";
  const osm = JSON.stringify({ elements: [{ type: "node", id: 1, lat: 52, lon: 21 }] });
  const archive = await createSessionZip(config, csv, osm);
  const session = await readSessionZip(archive);
  assert.deepEqual(session.config, config);
  assert.equal(session.csvText, csv);
  assert.equal(session.osmText, osm);
});

test("session ZIP rejects missing members and unsupported config versions", async () => {
  const zip = await createSessionZip({ version: 1 }, "a\nb", "{\"elements\":[]}");
  const JSZip = (await import("jszip")).default;
  const archive = await JSZip.loadAsync(zip);
  archive.remove("osm.json");
  await assert.rejects(readSessionZip(await archive.generateAsync({ type: "uint8array" })), /Brak wymaganych plików/);
  const unsupported = await createSessionZip({ version: 99 }, "a\nb", "{}");
  await assert.rejects(readSessionZip(unsupported), /wersja konfiguracji/);
});
