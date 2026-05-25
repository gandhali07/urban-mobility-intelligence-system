import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("C:/Users/nithi/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/");
const pptxgen = require("pptxgenjs");

const ROOT = "D:/BDA_Final_Project";
const OUT = path.join(ROOT, "Urban_Mobility_Intelligence_Final_Bold_Presentation.pptx");
const INSIGHTS = path.join(ROOT, "outputs/analytics/insights");
const FIGURES = path.join(ROOT, "outputs/figures");
const MAPS = path.join(ROOT, "outputs/maps");
const WPI_MEDIA = path.join(ROOT, "_tmp_wpi_template_extract/ppt/media");

const pptx = new pptxgen();
pptx.defineLayout({ name: "WIDE", width: 13.333, height: 7.5 });
pptx.layout = "WIDE";
pptx.author = "Urban Mobility Intelligence Team";
pptx.company = "Worcester Polytechnic Institute";
pptx.subject = "Big Data Analytics Final Presentation";
pptx.title = "Urban Mobility Intelligence System";
pptx.lang = "en-US";
pptx.theme = {
  headFontFace: "Aptos Display",
  bodyFontFace: "Aptos",
  lang: "en-US",
};

const W = 13.333;
const H = 7.5;
const maroon = "A6192E";
const maroonDark = "5E0B18";
const gold = "C99700";
const ink = "1F1F23";
const muted = "5E5E66";
const paper = "F7F4EF";
const blue = "2563EB";
const green = "148A43";
const orange = "EA580C";
const purple = "4C1D95";
const navy = "173B57";

const assets = {
  texture: path.join(WPI_MEDIA, "image1.jpeg"),
  sealWhite: path.join(WPI_MEDIA, "image5.png"),
  sealGray: path.join(WPI_MEDIA, "image2.png"),
  map: path.join(MAPS, "urban_mobility_map_screenshot.png"),
  shap: path.join(FIGURES, "shap_summary_bar.png"),
  hourly: path.join(INSIGHTS, "hourly_mobility.png"),
  airport: path.join(INSIGHTS, "airport_vs_non_airport.png"),
  zones: path.join(INSIGHTS, "top_zone_pairs.png"),
};

function exists(p) {
  return fs.existsSync(p) && fs.statSync(p).size > 0;
}

function base(slide, opts = {}) {
  const dark = opts.dark ?? false;
  slide.background = { color: dark ? maroonDark : paper };
  if (!dark && exists(assets.texture)) {
    slide.addImage({ path: assets.texture, x: 0, y: 0, w: W, h: H, transparency: 90 });
  }
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 0.18,
    h: H,
    fill: { color: dark ? gold : maroon },
    line: { color: dark ? gold : maroon },
  });
  if (dark && exists(assets.sealWhite)) {
    slide.addImage({ path: assets.sealWhite, x: 10.9, y: 4.9, w: 2.65, h: 2.65, transparency: 78 });
  } else if (!dark && exists(assets.sealGray)) {
    slide.addImage({ path: assets.sealGray, x: 11.15, y: 5.15, w: 2.05, h: 2.05, transparency: 90 });
  }
}

function footer(slide, n, dark = false) {
  slide.addText("Urban Mobility Intelligence System | Big Data Analytics | WPI", {
    x: 0.55,
    y: 7.14,
    w: 7.1,
    h: 0.22,
    fontFace: "Aptos",
    fontSize: 7.8,
    color: dark ? "F5ECEE" : muted,
    margin: 0,
  });
  slide.addText(String(n).padStart(2, "0"), {
    x: 12.23,
    y: 7.11,
    w: 0.42,
    h: 0.24,
    fontFace: "Aptos",
    fontSize: 8.5,
    bold: true,
    color: dark ? gold : maroon,
    align: "right",
    margin: 0,
  });
}

function kicker(slide, text, color = maroon) {
  slide.addShape(pptx.ShapeType.rect, { x: 0.58, y: 0.42, w: 0.12, h: 0.12, fill: { color }, line: { color } });
  slide.addText(text.toUpperCase(), {
    x: 0.82,
    y: 0.28,
    w: 5.9,
    h: 0.34,
    fontFace: "Aptos",
    fontSize: 9.2,
    bold: true,
    color,
    charSpace: 1.5,
    margin: 0,
    fit: "shrink",
  });
}

function title(slide, text, opts = {}) {
  slide.addText(text, {
    x: opts.x ?? 0.62,
    y: opts.y ?? 0.78,
    w: opts.w ?? 8.9,
    h: opts.h ?? 0.95,
    fontFace: "Aptos Display",
    fontSize: opts.size ?? 31,
    bold: true,
    color: opts.dark ? "FFFFFF" : ink,
    margin: 0,
    fit: "shrink",
  });
}

function subtitle(slide, text, opts = {}) {
  slide.addText(text, {
    x: opts.x ?? 0.65,
    y: opts.y ?? 1.72,
    w: opts.w ?? 8.5,
    h: opts.h ?? 0.55,
    fontFace: "Aptos",
    fontSize: opts.size ?? 13.3,
    color: opts.dark ? "F5ECEE" : muted,
    margin: 0,
    fit: "shrink",
  });
}

function bigNeed(slide, text, x, y, w, h, color) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color },
    line: { color },
  });
  slide.addText(text, {
    x: x + 0.22,
    y: y + 0.14,
    w: w - 0.44,
    h: h - 0.28,
    fontFace: "Aptos",
    fontSize: 15,
    bold: true,
    color: "FFFFFF",
    valign: "mid",
    margin: 0,
    fit: "shrink",
  });
}

function bullets(slide, items, x, y, w, h, opts = {}) {
  const runs = [];
  for (const item of items) runs.push({ text: item, options: { bullet: { indent: 14 }, hanging: 5, breakLine: true } });
  slide.addText(runs, {
    x,
    y,
    w,
    h,
    fontFace: "Aptos",
    fontSize: opts.size ?? 18,
    color: opts.dark ? "FFFFFF" : ink,
    paraSpaceAfterPt: opts.space ?? 12,
    breakLine: false,
    fit: "shrink",
    margin: 0.02,
  });
}

function metric(slide, value, label, x, y, w, color = maroon, dark = false) {
  slide.addText(value, {
    x,
    y,
    w,
    h: 0.52,
    fontFace: "Aptos Display",
    fontSize: 30,
    bold: true,
    color: dark ? "FFFFFF" : color,
    margin: 0,
  });
  slide.addText(label, {
    x,
    y: y + 0.57,
    w,
    h: 0.45,
    fontFace: "Aptos",
    fontSize: 9.6,
    bold: true,
    color: dark ? "F5ECEE" : muted,
    margin: 0,
    fit: "shrink",
  });
}

function image(slide, p, x, y, w, h, opts = {}) {
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w,
    h,
    fill: { color: "FFFFFF", transparency: opts.fillTrans ?? 0 },
    line: { color: opts.line ?? "D8D2CA", transparency: 8, width: 0.8 },
  });
  if (exists(p)) slide.addImage({ path: p, x: x + 0.04, y: y + 0.04, w: w - 0.08, h: h - 0.08, sizingCrop: true });
}

function note(slide, text, x, y, w, h, opts = {}) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: opts.fill ?? "FFFFFF", transparency: opts.transparency ?? 0 },
    line: { color: opts.line ?? "D7D0C7", width: 0.8 },
  });
  slide.addText(text, {
    x: x + 0.2,
    y: y + 0.15,
    w: w - 0.4,
    h: h - 0.3,
    fontFace: "Aptos",
    fontSize: opts.size ?? 14,
    bold: opts.bold,
    color: opts.color ?? ink,
    margin: 0,
    fit: "shrink",
    valign: "mid",
  });
}

function step(slide, n, label, x, y, color) {
  slide.addShape(pptx.ShapeType.ellipse, { x, y, w: 0.46, h: 0.46, fill: { color }, line: { color } });
  slide.addText(String(n), { x, y: y + 0.1, w: 0.46, h: 0.2, fontSize: 10, bold: true, color: "FFFFFF", align: "center", margin: 0 });
  slide.addText(label, { x: x + 0.62, y: y - 0.02, w: 3.2, h: 0.35, fontSize: 16, bold: true, color: ink, margin: 0, fit: "shrink" });
}

// Slide 1
{
  const s = pptx.addSlide();
  base(s, { dark: true });
  kicker(s, "Final Project Presentation", gold);
  s.addText("Urban Mobility\nIntelligence System", {
    x: 0.72,
    y: 1.18,
    w: 7.1,
    h: 1.55,
    fontFace: "Aptos Display",
    fontSize: 43,
    bold: true,
    color: "FFFFFF",
    margin: 0,
    fit: "shrink",
  });
  subtitle(s, "Traffic Analysis and Prediction using Big Data and Explainable AI", { x: 0.75, y: 3.0, w: 7.6, dark: true, size: 15 });
  s.addText("Presented by", { x: 0.78, y: 4.04, w: 1.7, h: 0.28, fontSize: 11, bold: true, color: gold, margin: 0 });
  bullets(s, ["Gandhali Sheth", "Nithish Kumar Bhupathi", "Aditya Pavan Sattenapalli", "Raghav Reddy"], 0.95, 4.45, 5.6, 1.2, { dark: true, size: 14, space: 4 });
  note(s, "Course: Big Data Analytics\nInstitution: Worcester Polytechnic Institute", 8.35, 1.55, 3.75, 1.3, { fill: "FFFFFF", size: 15, bold: true });
  if (exists(assets.map)) image(s, assets.map, 7.85, 3.42, 4.65, 2.55, { fillTrans: 8, line: gold });
  footer(s, 1, true);
}

// Slide 2
{
  const s = pptx.addSlide();
  base(s);
  kicker(s, "Problem Statement");
  title(s, "City mobility decisions are difficult when trip data is big, scattered, and unexplained.", { w: 10.7 });
  subtitle(s, "NYC taxi movement depends on distance, time, zones, weather, and events. Looking at one dataset alone does not show the full traffic story.", { w: 10.4 });
  note(s, "What makes the problem hard?\n\nTaxi data is very large\nWeather and event data are separate\nTraffic changes by hour and location\nPredictions need explanation, not only numbers", 0.82, 2.15, 3.85, 3.1, { fill: "FFFFFF", line: maroon, size: 14.8, bold: true });
  note(s, "Why it matters\n\nTravelers want expected trip time\nTaxi services need demand patterns\nPlanners need congestion insight\nProfessors/stakeholders need interpretable evidence", 4.86, 2.15, 3.85, 3.1, { fill: "FFFFFF", line: orange, size: 14.8, bold: true });
  note(s, "Gap in traditional approach\n\nBasic models can predict, but often do not explain why.\n\nStatic charts can show history, but do not support route-level prediction or interactive exploration.", 8.9, 2.15, 3.85, 3.1, { fill: "FFFFFF", line: navy, size: 14.2, bold: true });
  note(s, "Need: an end-to-end system that predicts travel time, explains the important factors, and visualizes urban mobility patterns.", 1.05, 5.85, 11.35, 0.85, { fill: "FFF4E6", line: gold, size: 17.5, bold: true, color: maroonDark });
  footer(s, 2);
}

// Slide 3
{
  const s = pptx.addSlide();
  base(s, { dark: true });
  kicker(s, "Project Goal", gold);
  title(s, "Combine data, AI, and visualization to understand urban mobility.", { dark: true, w: 10.3 });
  bullets(s, ["Predict taxi trip duration", "Explain predictions using SHAP", "Identify congestion patterns", "Visualize traffic using an interactive map"], 0.92, 2.3, 6.4, 2.2, { dark: true, size: 21, space: 13 });
  note(s, "Core idea\n\nCombine data + AI + visualization to understand urban mobility.", 8.1, 2.35, 3.95, 2.05, { fill: "FFFFFF", size: 18, bold: true });
  footer(s, 3, true);
}

// Slide 4
{
  const s = pptx.addSlide();
  base(s);
  kicker(s, "Data Sources");
  title(s, "Three datasets are aligned by trip time and context.");
  note(s, "Taxi Data\n\n2.9M trips\nTime, distance, zones", 0.85, 2.15, 3.45, 2.05, { fill: "FFFFFF", line: maroon, size: 17, bold: true });
  note(s, "Weather Data\n\nTemperature\nHumidity\nWind", 4.95, 2.15, 3.45, 2.05, { fill: "FFFFFF", line: blue, size: 17, bold: true });
  note(s, "Events Data\n\nDate\nLocation\nEvent count", 9.05, 2.15, 3.45, 2.05, { fill: "FFFFFF", line: green, size: 17, bold: true });
  note(s, "All datasets are merged using pickup hour, pickup date, and contextual features.", 1.55, 5.15, 10.2, 0.8, { fill: "FFF8EA", line: gold, size: 18, bold: true, color: maroonDark });
  footer(s, 4);
}

// Slide 5
{
  const s = pptx.addSlide();
  base(s);
  kicker(s, "System Workflow");
  title(s, "A modular Spark + Python pipeline runs the full solution.");
  const labels = ["Taxi + Weather + Events", "Preprocessing & Cleaning", "Feature Engineering", "XGBoost Model", "SHAP Explainability", "Interactive Map + Demo"];
  const colors = [maroon, orange, green, blue, purple, navy];
  for (let i = 0; i < labels.length; i++) {
    step(s, i + 1, labels[i], 1.0 + (i % 2) * 5.9, 2.0 + Math.floor(i / 2) * 1.32, colors[i]);
  }
  for (const y of [2.46, 3.78]) {
    s.addShape(pptx.ShapeType.line, { x: 3.95, y, w: 1.95, h: 0, line: { color: "9E9287", width: 1.3, endArrowType: "triangle" } });
  }
  footer(s, 5);
}

// Slide 6
{
  const s = pptx.addSlide();
  base(s, { dark: true });
  kicker(s, "Model & Performance", gold);
  title(s, "XGBoost regression captures most trip-duration variation.", { dark: true, w: 10.2 });
  subtitle(s, "The model uses pre-trip features only, so payment-after-trip fields are not required.", { dark: true, w: 8.7 });
  metric(s, "R² = 0.843", "Captures about 84% of trip variation", 0.95, 2.8, 3.1, gold, true);
  metric(s, "MAE ≈ 175 sec", "About 2.9 minutes average error", 4.55, 2.8, 3.2, gold, true);
  metric(s, "23", "Final model features", 8.35, 2.8, 2.2, gold, true);
  note(s, "Main message\n\nThe model is accurate enough for a class demo and useful enough to support route-level travel-time estimation.", 1.05, 4.85, 10.65, 1.05, { fill: "FFFFFF", size: 17, bold: true });
  footer(s, 6, true);
}

// Slide 7
{
  const s = pptx.addSlide();
  base(s);
  kicker(s, "Explainable AI");
  title(s, "SHAP makes the model transparent and trustworthy.");
  image(s, assets.shap, 0.75, 2.05, 5.95, 4.45);
  bullets(s, ["Trip distance is the strongest factor", "Time of day has major impact", "Pickup/dropoff zones are important", "Weather has a smaller supporting effect"], 7.18, 2.35, 5.1, 2.4, { size: 18, space: 11 });
  note(s, "Why it matters: users can see why predictions happen, not just the final number.", 7.35, 5.25, 4.75, 0.88, { fill: "FFF8EA", line: gold, size: 15.5, bold: true });
  footer(s, 7);
}

// Slide 8
{
  const s = pptx.addSlide();
  base(s);
  kicker(s, "Key Insights");
  title(s, "The analytics convert raw trips into actionable mobility insights.");
  image(s, assets.hourly, 0.72, 1.85, 6.4, 3.25);
  image(s, assets.airport, 7.45, 1.85, 5.05, 3.25);
  bullets(s, ["Peak demand: 6 PM", "Slowest average duration: 2 PM", "Airport trips have longer distance and duration", "Weather is a secondary factor", "Events show weak global impact"], 1.0, 5.55, 11.1, 1.0, { size: 15, space: 5 });
  footer(s, 8);
}

// Slide 9
{
  const s = pptx.addSlide();
  base(s, { dark: true });
  kicker(s, "Interactive Map & Demo", gold);
  title(s, "The final system supports map exploration and route testing.", { dark: true, w: 10.4 });
  image(s, assets.map, 0.78, 2.0, 6.65, 4.25, { line: gold });
  note(s, "Map features\n\nTraffic density visualization\nCongestion hotspots\nEvent overlays", 7.85, 2.0, 3.9, 1.65, { fill: "FFFFFF", size: 15.5, bold: true });
  note(s, "Demo example\n\nTimes Square -> JFK\nDistance: 18.26 miles\nDuration: ~49.7 min", 7.85, 4.1, 3.9, 1.55, { fill: "FFF8EA", line: gold, size: 15.2, bold: true });
  footer(s, 9, true);
}

// Slide 10
{
  const s = pptx.addSlide();
  base(s);
  kicker(s, "Conclusion & Future Work");
  title(s, "AI + Big Data can support smarter urban mobility decisions.");
  note(s, "Achievements\n\nBuilt end-to-end pipeline\nIntegrated multiple datasets\nDeveloped accurate model\nAdded explainability + visualization", 0.8, 2.0, 5.55, 2.55, { fill: "FFFFFF", line: green, size: 16.5, bold: true });
  note(s, "Limitations\n\nNo exact GPS coordinates in current TLC file\nCitywide events are too broad for local congestion", 7.0, 2.0, 5.15, 1.55, { fill: "FFFFFF", line: orange, size: 16.5, bold: true });
  note(s, "Future work\n\nTaxi-zone shapefiles\nLocalized event impact\nReal-time traffic feeds", 7.0, 4.0, 5.15, 1.6, { fill: "FFF8EA", line: gold, size: 16.5, bold: true });
  footer(s, 10);
}

await pptx.writeFile({ fileName: OUT });
console.log(OUT);
