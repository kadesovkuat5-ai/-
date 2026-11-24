// Project Natural Earth country shapes (world-atlas 110m) to SVG paths for the film's maps.
// Usage: node tools/maps.mjs <node_modules dir>   ->  tools/maps.json
import { createRequire } from "module";
import fs from "fs";
import path from "path";

const nm = process.argv[2];
const require = createRequire(path.join(nm, "x.js"));
const topo = require("topojson-client");
const d3 = require("d3-geo");
const load = (f) => { const w = JSON.parse(fs.readFileSync(path.join(nm, "world-atlas/" + f), "utf8")); return topo.feature(w, w.objects.countries).features; };
const sets = { eu: load("countries-50m.json"), world: load("countries-110m.json") };

const W = 1920, H = 1080;
const views = {
  // Europe, Anatolia and Kazakhstan
  eu: { proj: d3.geoConicConformal().rotate([-35, 0]).parallels([40, 62]), box: [[-11, 33], [86, 66]], pad: 40, bottom: 170 },
  // most of the world, for the Second World War
  world: { proj: d3.geoNaturalEarth1(), box: [[-170, -48], [178, 78]], pad: 70, bottom: 150 },
};

const labels = {
  eu: {
    RU: [44, 58], DE: [10.4, 51.2], FR: [2.4, 46.6], GB: [-2.2, 53.2], IT: [12.6, 42.6], AH: [17.5, 48.6],
    OT: [34, 39], RS: [21.2, 43.6], BG: [26.2, 42.4], KZ: [67, 48.2], PL: [19.4, 52.2],
  },
  world: {
    DE: [10.4, 51.2], IT: [12.6, 42.6], JP: [138, 36.5], SU: [90, 61], US: [-100, 39.5], GB: [-2.2, 53.2],
    CN: [104, 34], FR: [2.4, 46.6], KZ: [67, 48.2],
  },
};
// The Western and Eastern fronts of 1914–1917 (approximate)
const lines = {
  west: [[2.6, 51.15], [2.9, 50.6], [2.8, 49.9], [3.6, 49.4], [4.9, 49.2], [5.6, 48.9], [6.9, 48.3], [7.25, 47.55]],
  east: [[24.1, 56.95], [26.2, 55.0], [25.8, 53.4], [25.4, 51.6], [25.3, 50.2], [26.0, 48.4], [27.8, 46.6]],
  paris: [[2.35, 48.86]],
  sarajevo: [[18.41, 43.86]],
  moscow: [[37.62, 55.75]],
  almaty: [[76.9, 43.24]],
  pacific: [[160, 12]],
  africa: [[24, 31]],
  atlantic: [[-38, 45]],
  europe: [[22, 52]],
  china: [[112, 32]],
};

const out = {};
for (const [name, v] of Object.entries(views)) {
  const box = { type: "Feature", geometry: { type: "MultiPoint", coordinates: [v.box[0], [v.box[0][0], v.box[1][1]], v.box[1], [v.box[1][0], v.box[0][1]]] } };
  v.proj.fitExtent([[v.pad, v.pad * 0.5], [W - v.pad, H - v.bottom]], box);
  v.proj.clipExtent([[-30, -30], [W + 30, H + 30]]);
  const gen = d3.geoPath(v.proj);
  const shapes = {};
  for (const f of sets[name]) {
    const d = gen(f);
    if (!d || d.length < 20) continue;
    // keep shapes that touch the frame
    const [[x0, y0], [x1, y1]] = gen.bounds(f);
    if (x1 < -50 || x0 > W + 50 || y1 < -50 || y0 > H + 50) continue;
    shapes[f.id] = d.replace(/(\d+)\.\d+/g, "$1");
  }
  const lab = {};
  for (const [k, ll] of Object.entries(labels[name])) lab[k] = v.proj(ll).map((n) => Math.round(n));
  const ln = {};
  for (const [k, pts] of Object.entries(lines)) ln[k] = pts.map((p) => v.proj(p).map((n) => Math.round(n)));
  out[name] = { shapes, labels: lab, lines: ln };
  console.log(name, Object.keys(shapes).length, "shapes");
}
fs.writeFileSync(new URL("./maps.json", import.meta.url), JSON.stringify(out));
