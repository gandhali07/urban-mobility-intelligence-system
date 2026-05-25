import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("C:/Users/nithi/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/");
const pptxgen = require("pptxgenjs");

const ROOT = "D:/BDA_Final_Project";
const OUT = path.join(ROOT, "Urban_Mobility_Intelligence_WPI_Insights_Deck.pptx");
const INSIGHTS = path.join(ROOT, "outputs/analytics/insights");
const FIGURES = path.join(ROOT, "outputs/figures");
const MAPS = path.join(ROOT, "outputs/maps");
const WPI_MEDIA = path.join(ROOT, "_tmp_wpi_template_extract/ppt/media");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "Urban Mobility Intelligence";
pptx.company = "Worcester Polytechnic Institute";
pptx.subject = "NYC Taxi Mobility Analytics with Weather and Events";
pptx.title = "Urban Mobility Intelligence - NYC";
pptx.lang = "en-US";
pptx.theme = {
  headFontFace: "Aptos Display",
  bodyFontFace: "Aptos",
  lang: "en-US",
};
pptx.defineLayout({ name: "CUSTOM_WIDE", width: 13.333, height: 7.5 });
pptx.layout = "CUSTOM_WIDE";

const W = 13.333;
const H = 7.5;
const maroon = "A6192E";
const maroonDark = "6F1020";
const ink = "18181B";
const muted = "666666";
const paper = "F7F5F1";
const light = "EFEAE3";
const gold = "C99700";
const blue = "2F80ED";
const green = "27AE60";
const orange = "F2994A";

const assets = {
  texture: path.join(WPI_MEDIA, "image1.jpeg"),
  sealWhite: path.join(WPI_MEDIA, "image5.png"),
  sealGray: path.join(WPI_MEDIA, "image2.png"),
  map: path.join(MAPS, "urban_mobility_map_screenshot.png"),
  shapBar: path.join(FIGURES, "shap_summary_bar.png"),
  shapBeeswarm: path.join(FIGURES, "shap_summary_beeswarm.png"),
  event: path.join(INSIGHTS, "event_impact_duration.png"),
  weather: path.join(INSIGHTS, "weather_impact_duration.png"),
  hourly: path.join(INSIGHTS, "hourly_mobility.png"),
  zones: path.join(INSIGHTS, "top_zone_pairs.png"),
  airport: path.join(INSIGHTS, "airport_vs_non_airport.png"),
};

function exists(p) {
  return fs.existsSync(p) && fs.statSync(p).size > 0;
}

function addBase(slide, opts = {}) {
  const bg = opts.dark ? maroonDark : paper;
  slide.background = { color: bg };
  if (!opts.dark && exists(assets.texture)) {
    slide.addImage({ path: assets.texture, x: 0, y: 0, w: W, h: H, transparency: 88 });
  }
  if (opts.dark && exists(assets.sealWhite)) {
    slide.addImage({ path: assets.sealWhite, x: 10.85, y: 4.85, w: 2.7, h: 2.7, transparency: 78 });
  } else if (exists(assets.sealGray)) {
    slide.addImage({ path: assets.sealGray, x: 11.1, y: 5.15, w: 2.15, h: 2.15, transparency: 88 });
  }
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 0.16,
    h: H,
    fill: { color: maroon },
    line: { color: maroon },
  });
}

function kicker(slide, text, opts = {}) {
  const color = opts.dark ? "FFFFFF" : maroon;
  slide.addShape(pptx.ShapeType.rect, {
    x: 0.55,
    y: 0.42,
    w: 0.1,
    h: 0.1,
    fill: { color },
    line: { color },
  });
  slide.addText(text.toUpperCase(), {
    x: 0.75,
    y: 0.28,
    w: 5.8,
    h: 0.34,
    fontFace: "Aptos",
    fontSize: 9,
    bold: true,
    color,
    charSpace: 1.8,
    margin: 0,
    breakLine: false,
    fit: "shrink",
  });
}

function title(slide, text, opts = {}) {
  slide.addText(text, {
    x: opts.x ?? 0.55,
    y: opts.y ?? 0.72,
    w: opts.w ?? 8.8,
    h: opts.h ?? 0.9,
    fontFace: "Aptos Display",
    fontSize: opts.size ?? 28,
    bold: true,
    color: opts.dark ? "FFFFFF" : ink,
    margin: 0,
    fit: "shrink",
    breakLine: false,
  });
}

function subtitle(slide, text, opts = {}) {
  slide.addText(text, {
    x: opts.x ?? 0.58,
    y: opts.y ?? 1.68,
    w: opts.w ?? 8.6,
    h: opts.h ?? 0.55,
    fontFace: "Aptos",
    fontSize: opts.size ?? 12,
    color: opts.dark ? "F3F0EA" : muted,
    margin: 0,
    fit: "shrink",
    breakLine: false,
  });
}

function footer(slide, n, dark = false) {
  slide.addShape(pptx.ShapeType.line, {
    x: 0.55,
    y: 7.05,
    w: 12.1,
    h: 0,
    line: { color: dark ? "D6C8BE" : "D8D1C8", transparency: dark ? 55 : 15, width: 0.6 },
  });
  slide.addText("Urban Mobility Intelligence | NYC TLC + Weather + Events", {
    x: 0.55,
    y: 7.13,
    w: 7.6,
    h: 0.22,
    fontSize: 7.5,
    color: dark ? "EADFE0" : muted,
    margin: 0,
  });
  slide.addText(String(n).padStart(2, "0"), {
    x: 12.25,
    y: 7.1,
    w: 0.42,
    h: 0.25,
    fontSize: 8,
    bold: true,
    color: dark ? "FFFFFF" : maroon,
    align: "right",
    margin: 0,
  });
}

function metric(slide, value, label, x, y, w, color = maroon, dark = false) {
  slide.addText(value, {
    x,
    y,
    w,
    h: 0.48,
    fontFace: "Aptos Display",
    fontSize: 26,
    bold: true,
    color: dark ? "FFFFFF" : color,
    margin: 0,
  });
  slide.addText(label, {
    x,
    y: y + 0.5,
    w,
    h: 0.42,
    fontSize: 8.8,
    bold: true,
    color: dark ? "F3F0EA" : muted,
    margin: 0,
    fit: "shrink",
  });
}

function note(slide, text, x, y, w, h, opts = {}) {
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w,
    h,
    fill: { color: opts.fill ?? "FFFFFF", transparency: opts.transparency ?? 4 },
    line: { color: opts.line ?? "D7D0C7", transparency: 10, width: 0.8 },
    radius: 0.06,
  });
  slide.addText(text, {
    x: x + 0.16,
    y: y + 0.15,
    w: w - 0.32,
    h: h - 0.3,
    fontSize: opts.size ?? 11,
    color: opts.color ?? ink,
    margin: 0.02,
    fit: "shrink",
    valign: "mid",
    breakLine: false,
  });
}

function imagePanel(slide, imagePath, x, y, w, h, opts = {}) {
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w,
    h,
    fill: { color: "FFFFFF", transparency: opts.transparency ?? 0 },
    line: { color: "D7D0C7", transparency: 12, width: 0.8 },
  });
  if (exists(imagePath)) {
    slide.addImage({ path: imagePath, x: x + 0.04, y: y + 0.04, w: w - 0.08, h: h - 0.08, sizingCrop: true });
  } else {
    slide.addText("Missing image", { x, y: y + h / 2 - 0.2, w, h: 0.4, align: "center", color: muted });
  }
}

function bulletList(slide, items, x, y, w, h, opts = {}) {
  const runs = [];
  for (const item of items) {
    runs.push({ text: item, options: { bullet: { indent: 12 }, hanging: 4, breakLine: true } });
  }
  slide.addText(runs, {
    x,
    y,
    w,
    h,
    fontSize: opts.size ?? 12,
    color: opts.color ?? ink,
    breakLine: false,
    fit: "shrink",
    margin: 0.02,
    paraSpaceAfterPt: 7,
  });
}

function processStep(slide, idx, label, detail, x, y, color) {
  slide.addShape(pptx.ShapeType.ellipse, {
    x,
    y,
    w: 0.5,
    h: 0.5,
    fill: { color },
    line: { color },
  });
  slide.addText(String(idx), { x, y: y + 0.11, w: 0.5, h: 0.2, fontSize: 10, color: "FFFFFF", bold: true, align: "center", margin: 0 });
  slide.addText(label, { x: x + 0.65, y: y - 0.02, w: 1.45, h: 0.26, fontSize: 10.5, bold: true, color: ink, margin: 0 });
  slide.addText(detail, { x: x + 0.65, y: y + 0.28, w: 1.72, h: 0.5, fontSize: 7.7, color: muted, margin: 0, fit: "shrink" });
}

// 1 Cover
{
  const s = pptx.addSlide();
  addBase(s, { dark: true });
  kicker(s, "Big Data Analytics Final Project", { dark: true });
  s.addText("Urban Mobility\nIntelligence", {
    x: 0.65,
    y: 1.42,
    w: 6.8,
    h: 1.45,
    fontFace: "Aptos Display",
    fontSize: 42,
    bold: true,
    color: "FFFFFF",
    margin: 0,
    breakLine: false,
    fit: "shrink",
  });
  subtitle(s, "NYC taxi trip prediction, mobility analytics, event context, and explainable ML", { x: 0.68, y: 3.1, w: 7.2, dark: true, size: 13 });
  metric(s, "2.9M", "TLC taxi rows loaded with Spark", 0.7, 4.35, 2.2, gold, true);
  metric(s, "13.6K", "NYC event records aligned to February 2023", 3.15, 4.35, 2.5, gold, true);
  metric(s, "R² 0.843", "Trip duration model performance", 6.0, 4.35, 2.2, gold, true);
  if (exists(assets.map)) s.addImage({ path: assets.map, x: 8.2, y: 0.9, w: 4.5, h: 4.7, transparency: 7, sizingCrop: true });
  footer(s, 1, true);
}

// 2 Summary
{
  const s = pptx.addSlide();
  addBase(s);
  kicker(s, "Executive Summary");
  title(s, "The project turns raw taxi trips into planning-grade mobility intelligence.");
  subtitle(s, "Three datasets are joined into analytics, a prediction model, explainability plots, and a working route demo.");
  metric(s, "176 sec", "Mean absolute prediction error", 0.7, 2.65, 2.1, maroon);
  metric(s, "84%", "Variation explained on test split", 3.0, 2.65, 2.1, maroon);
  metric(s, "5", "Business insight areas generated", 5.3, 2.65, 2.1, maroon);
  note(s, "Core finding: trip distance, time of day, and pickup/dropoff zones explain most trip duration. Events and weather add context, while airport trips behave as a distinct mobility pattern.", 8.05, 2.1, 4.15, 1.7, { fill: "FFF8EA", line: "D7B15B", size: 12 });
  bulletList(s, [
    "Spark handles the large TLC taxi dataset and collects a controlled modeling sample.",
    "Analytics converts technical tables into slide-ready business insights.",
    "SHAP explains which features influence the model most.",
    "A CLI prediction demo estimates duration and congestion from two user-selected locations.",
  ], 0.72, 4.3, 11.0, 1.5);
  footer(s, 2);
}

// 3 Architecture
{
  const s = pptx.addSlide();
  addBase(s);
  kicker(s, "Pipeline Architecture");
  title(s, "The workflow moves from raw data to maps, insights, model, and demo.");
  subtitle(s, "The project is modular: each `src` file owns one stage, while `main.py` runs the full pipeline.");
  const y = 2.35;
  const xs = [0.72, 2.55, 4.55, 6.55, 8.55, 10.55];
  const labels = ["Load", "Clean", "Merge", "Features", "Model", "Explain"];
  const details = ["Taxi, weather, events", "timestamps, trips", "hour + date context", "time, airport, weather", "XGBoost duration", "SHAP + map"];
  const colors = [maroon, blue, green, orange, gold, maroonDark];
  for (let i = 0; i < xs.length; i++) {
    processStep(s, i + 1, labels[i], details[i], xs[i], y, colors[i]);
    if (i < xs.length - 1) {
      s.addShape(pptx.ShapeType.line, {
        x: xs[i] + 1.35,
        y: y + 0.25,
        w: 0.75,
        h: 0,
        line: { color: "9E9287", width: 1.2, beginArrowType: "none", endArrowType: "triangle" },
      });
    }
  }
  note(s, "`main.py` is the full production run. `src.analytics` creates presentation-ready CSV/PNG/Markdown insight artifacts. `predict_trip.py` is the user-facing route prediction demo.", 0.85, 4.3, 11.4, 1.15, { fill: "FFFFFF", size: 12 });
  footer(s, 3);
}

// 4 Map
{
  const s = pptx.addSlide();
  addBase(s, { dark: true });
  kicker(s, "Map Layer", { dark: true });
  title(s, "The map shows event context and mobility intensity, with one caveat.", { dark: true });
  subtitle(s, "TLC yellow taxi data provides pickup/dropoff zone IDs, not exact GPS coordinates, so street-level taxi density is visualized through available zone/context layers.", { dark: true, w: 8.4 });
  imagePanel(s, assets.map, 0.75, 2.2, 7.8, 4.55, { transparency: 0 });
  note(s, "How to present it:\n\nThe map is an interactive visual layer for NYC mobility patterns. It helps stakeholders see where event context and taxi activity concentrate. For future work, taxi-zone shapefiles can convert zone IDs into precise zone polygons and centroids.", 9.0, 2.45, 3.35, 2.65, { fill: "FFFFFF", size: 11 });
  footer(s, 4, true);
}

// 5 Model + SHAP
{
  const s = pptx.addSlide();
  addBase(s);
  kicker(s, "Predictive Model");
  title(s, "The cleaned model predicts trip duration with strong explanatory power.");
  subtitle(s, "XGBoost regression trained on pre-trip features: distance, time, location zones, weather, event count, and airport-trip flag.");
  metric(s, "0.843", "R² on test split", 0.75, 2.15, 1.8, maroon);
  metric(s, "175.7s", "Mean absolute error", 2.85, 2.15, 1.8, maroon);
  metric(s, "23", "Model features", 4.95, 2.15, 1.6, maroon);
  imagePanel(s, assets.shapBar, 0.75, 3.38, 5.75, 2.9);
  imagePanel(s, assets.shapBeeswarm, 6.85, 2.15, 5.75, 4.15);
  note(s, "SHAP confirms the business story: distance dominates, then time and pickup/dropoff zones. Weather features matter, but less than core mobility variables.", 6.85, 6.45, 5.75, 0.55, { fill: "FFF8EA", line: "D7B15B", size: 9.6 });
  footer(s, 5);
}

// 6 Time
{
  const s = pptx.addSlide();
  addBase(s);
  kicker(s, "Time-Based Mobility");
  title(s, "Trips slow down most in the afternoon while demand peaks around evening.");
  subtitle(s, "Time of day is a strong operational signal for both expected delay and trip volume.");
  imagePanel(s, assets.hourly, 0.75, 2.0, 8.1, 4.85);
  note(s, "Business insight\n\nSlowest hour: 14:00, averaging about 18.7 minutes.\n\nBusiest hour: 18:00, with the highest sample trip count.\n\nUse case: help travelers and dispatchers plan around slower windows.", 9.25, 2.25, 3.0, 3.5, { fill: "FFFFFF", size: 11.5 });
  footer(s, 6);
}

// 7 Events
{
  const s = pptx.addSlide();
  addBase(s);
  kicker(s, "Event Impact");
  title(s, "Citywide event volume adds context, but does not fully explain delay.");
  subtitle(s, "This is an honest analytical result: event count should be localized by borough or zone in future work.");
  imagePanel(s, assets.event, 0.75, 2.0, 7.55, 4.65);
  note(s, "Business insight\n\nHigh-event days average 16.2 minutes versus no-event days at 16.4 minutes.\n\nThis means total NYC event count is too broad. The next improvement should measure nearby events around pickup/dropoff zones.", 8.8, 2.25, 3.55, 3.35, { fill: "FFFFFF", size: 11.4 });
  footer(s, 7);
}

// 8 Weather
{
  const s = pptx.addSlide();
  addBase(s);
  kicker(s, "Weather Impact");
  title(s, "Weather affects travel time, but it is secondary to route and time.");
  subtitle(s, "Temperature, wind, humidity, pressure, and precipitation are useful support features rather than the main driver.");
  imagePanel(s, assets.weather, 0.75, 2.0, 7.55, 4.65);
  note(s, "Business insight\n\nMild-temperature trips were slowest in the sample at about 17.6 minutes.\n\nBut SHAP shows weather features rank below distance, hour, pickup zone, and dropoff zone.", 8.8, 2.25, 3.55, 3.2, { fill: "FFFFFF", size: 11.4 });
  footer(s, 8);
}

// 9 Corridors
{
  const s = pptx.addSlide();
  addBase(s);
  kicker(s, "Travel Corridors");
  title(s, "Demand concentrates in repeated pickup-dropoff corridors.");
  subtitle(s, "Zone names make the analytics easier to explain than raw TLC location IDs.");
  imagePanel(s, assets.zones, 0.7, 1.95, 8.25, 4.95);
  note(s, "Business insight\n\nTop route: Upper East Side South to Upper East Side North with 701 trips in the sample.\n\nUse case: fleet positioning, route planning, and map storytelling.", 9.25, 2.35, 3.0, 3.15, { fill: "FFFFFF", size: 11.5 });
  footer(s, 9);
}

// 10 Airport + Prediction
{
  const s = pptx.addSlide();
  addBase(s);
  kicker(s, "User-Facing Prediction");
  title(s, "Airport trips behave differently, and the demo turns the model into a tool.");
  subtitle(s, "The prediction interface estimates duration and congestion from two locations and a timestamp.");
  imagePanel(s, assets.airport, 0.75, 2.0, 6.45, 4.65);
  note(s, "Example demo output\n\nTimes Square -> JFK Airport\nDate/time: 2023-02-10 17:30\nDistance used: 18.26 miles\nEvents that day: 511\nEstimated duration: 49.7 minutes\nEstimated congestion: Low", 7.65, 2.0, 4.75, 2.35, { fill: "FFF8EA", line: "D7B15B", size: 11 });
  note(s, "Why it matters\n\nThe project is not only descriptive. A user can test route scenarios and get an explainable travel-time estimate.", 7.65, 4.7, 4.75, 1.45, { fill: "FFFFFF", size: 11.3 });
  footer(s, 10);
}

// 11 Close
{
  const s = pptx.addSlide();
  addBase(s, { dark: true });
  kicker(s, "Conclusion", { dark: true });
  title(s, "The project is complete as an analytics pipeline and ready for sharper geospatial refinement.", { dark: true, w: 10.6 });
  subtitle(s, "Final outputs include a trained model, SHAP explainability, interactive map, analytics insight charts, and a prediction demo.", { dark: true, w: 9.7 });
  bulletList(s, [
    "Solved: joined taxi, weather, and event data into one mobility intelligence system.",
    "Proved: distance, hour, and zones are the strongest drivers of trip duration.",
    "Delivered: model performance improved to R² 0.843 with MAE around 2.9 minutes.",
    "Next: use taxi-zone shapefiles and localized event proximity for more exact map analytics.",
  ], 0.82, 2.75, 7.25, 2.25, { color: "FFFFFF", size: 14 });
  note(s, "Recommended future work\n\n1. Zone polygon map using TLC shapefile\n2. Events near pickup/dropoff zone\n3. Streamlit dashboard polish\n4. Larger production training run", 8.55, 2.75, 3.5, 2.45, { fill: "FFFFFF", size: 11.5 });
  footer(s, 11, true);
}

await pptx.writeFile({ fileName: OUT });
console.log(OUT);
