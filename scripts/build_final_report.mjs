import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("C:/Users/nithi/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/");
const {
  AlignmentType,
  BorderStyle,
  Document,
  Footer,
  Header,
  HeadingLevel,
  ImageRun,
  LevelFormat,
  Packer,
  PageBreak,
  PageNumber,
  Paragraph,
  Table,
  TableCell,
  TableRow,
  TextRun,
  WidthType,
} = require("docx");

const ROOT = "D:/BDA_Final_Project";
const OUT_DIR = path.join(ROOT, "Project Report");
const OUT = path.join(OUT_DIR, "Urban_Mobility_Intelligence_Final_Project_Report.docx");
const INSIGHTS = path.join(ROOT, "outputs/analytics/insights");
const FIGURES = path.join(ROOT, "outputs/figures");
const MAPS = path.join(ROOT, "outputs/maps");
const MODELS = path.join(ROOT, "outputs/models");

const modelMeta = JSON.parse(fs.readFileSync(path.join(MODELS, "xgboost_model_meta.json"), "utf8"));
const insights = JSON.parse(fs.readFileSync(path.join(INSIGHTS, "business_insights.json"), "utf8"));

const img = {
  map: path.join(MAPS, "urban_mobility_map_screenshot.png"),
  shapBar: path.join(FIGURES, "shap_summary_bar.png"),
  shapBeeswarm: path.join(FIGURES, "shap_summary_beeswarm.png"),
  event: path.join(INSIGHTS, "event_impact_duration.png"),
  weather: path.join(INSIGHTS, "weather_impact_duration.png"),
  hourly: path.join(INSIGHTS, "hourly_mobility.png"),
  zones: path.join(INSIGHTS, "top_zone_pairs.png"),
  airport: path.join(INSIGHTS, "airport_vs_non_airport.png"),
};

function text(t, opts = {}) {
  return new TextRun({
    text: t,
    bold: opts.bold,
    italics: opts.italics,
    color: opts.color || "111111",
    size: opts.size || 22,
    font: opts.font || "Times New Roman",
    break: opts.break,
  });
}

function p(t, opts = {}) {
  return new Paragraph({
    children: Array.isArray(t) ? t : [text(t, opts.run || {})],
    spacing: { before: opts.before ?? 0, after: opts.after ?? 120, line: opts.line ?? 276 },
    alignment: opts.alignment || AlignmentType.JUSTIFIED,
    style: opts.style,
    heading: opts.heading,
    keepNext: opts.keepNext,
  });
}

function h1(t) {
  return new Paragraph({
    text: t,
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 240, after: 120 },
    keepNext: true,
  });
}

function h2(t) {
  return new Paragraph({
    text: t,
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 180, after: 80 },
    keepNext: true,
  });
}

function caption(t) {
  return new Paragraph({
    children: [text(t, { italics: true, size: 18, color: "555555" })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 60, after: 180 },
  });
}

function bullet(t) {
  return new Paragraph({
    children: [text(t)],
    bullet: { level: 0 },
    spacing: { before: 0, after: 90, line: 276 },
  });
}

function numbered(t) {
  return new Paragraph({
    children: [text(t)],
    numbering: { reference: "section-numbering", level: 0 },
    spacing: { before: 0, after: 90, line: 276 },
  });
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

function cell(content, opts = {}) {
  const paragraphs = Array.isArray(content)
    ? content.map((item) => (item instanceof Paragraph ? item : p(String(item), { alignment: AlignmentType.LEFT, after: 40 })))
    : [p(String(content), { alignment: AlignmentType.LEFT, after: 40 })];
  return new TableCell({
    children: paragraphs,
    shading: opts.shading ? { fill: opts.shading } : undefined,
    width: opts.width ? { size: opts.width, type: WidthType.DXA } : undefined,
    margins: { top: 100, bottom: 100, left: 120, right: 120 },
    verticalAlign: "center",
  });
}

function table(headers, rows, widths) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: widths,
    borders: {
      top: { style: BorderStyle.SINGLE, size: 1, color: "B8B8B8" },
      bottom: { style: BorderStyle.SINGLE, size: 1, color: "B8B8B8" },
      left: { style: BorderStyle.SINGLE, size: 1, color: "B8B8B8" },
      right: { style: BorderStyle.SINGLE, size: 1, color: "B8B8B8" },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 1, color: "D0D0D0" },
      insideVertical: { style: BorderStyle.SINGLE, size: 1, color: "D0D0D0" },
    },
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) =>
          cell([new Paragraph({ children: [text(h, { bold: true, color: "FFFFFF" })], alignment: AlignmentType.LEFT })], {
            shading: "A6192E",
            width: widths[i],
          }),
        ),
      }),
      ...rows.map(
        (r) =>
          new TableRow({
            children: r.map((c, i) => cell(c, { width: widths[i] })),
          }),
      ),
    ],
  });
}

function figure(imagePath, width, height, alt, cap) {
  const parts = [];
  if (fs.existsSync(imagePath)) {
    parts.push(
      new Paragraph({
        children: [
          new ImageRun({
            type: "png",
            data: fs.readFileSync(imagePath),
            transformation: { width, height },
            altText: { title: alt, description: alt, name: alt },
          }),
        ],
        alignment: AlignmentType.CENTER,
        spacing: { before: 80, after: 60 },
      }),
    );
  } else {
    parts.push(p(`[Missing figure: ${imagePath}]`, { alignment: AlignmentType.CENTER }));
  }
  parts.push(caption(cap));
  return parts;
}

function insightText(title) {
  return insights.find((x) => x.slide_title === title);
}

const metricRows = [
  ["Taxi trips loaded", "2,913,955 rows", "NYC TLC yellow taxi trip records in Parquet format"],
  ["Modeling sample", "48,305 valid rows", "Rows after feature engineering and filtering obvious outliers"],
  ["Weather records", "672 hourly rows", "Hourly February 2023 NYC weather variables"],
  ["Event records", "13,576 events", "NYC Open Data event records aligned by trip date"],
  ["Model result", `R2 = ${modelMeta.metrics.r2.toFixed(3)}, MAE = ${modelMeta.metrics.mae.toFixed(1)} sec`, "XGBoost regression for taxi trip duration"],
];

const featureRows = [
  ["Temporal", "hour, day of week, month, weekend flag, rush-hour flag", "Captures regular daily and weekly mobility patterns."],
  ["Trip structure", "trip_distance, distance_bucket, pickup/dropoff TLC zones", "Represents the physical and zone-based shape of the trip."],
  ["Context", "event_count, event_level, temperature, wind, humidity, pressure, precipitation", "Adds external conditions aligned to the pickup time/date."],
  ["Special route type", "is_airport_trip", "Separates JFK, LaGuardia, and Newark airport trips from normal city trips."],
];

const techRows = [
  ["Apache Spark / PySpark", "Distributed loading, preprocessing, and merging of the large taxi dataset."],
  ["Pandas", "Final analytical tables, feature summaries, and presentation-ready CSV outputs."],
  ["XGBoost", "Gradient-boosted tree model used for trip-duration prediction."],
  ["SHAP", "Explains feature importance and direction of model influence."],
  ["Folium / Leaflet", "Interactive map visualization with layers for mobility density, hotspots, and events."],
  ["Streamlit and CLI", "Dashboard and route-prediction demo interfaces for presentation."],
];

const children = [];

children.push(
  new Paragraph({
    children: [text("Urban Mobility Intelligence System with Explainable AI and Event-Aware Analysis", { bold: true, size: 32 })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 180, after: 180 },
  }),
  new Paragraph({
    children: [text("Final Project Report", { bold: true, size: 26, color: "A6192E" })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 180 },
  }),
  new Paragraph({
    children: [text("Big Data Analytics", { size: 22 })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 80 },
  }),
  new Paragraph({
    children: [text("Team Members: Gandhali Sheth, Nithish Kumar Bhupathi, Aditya Pavan Sattenapalli, Raghavandhara Reddy Janammagari", { size: 22 })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 220 },
  }),
  h1("Abstract"),
  p("This project presents an Urban Mobility Intelligence System for New York City taxi movement analysis. The system integrates NYC TLC yellow taxi trip records, historical hourly weather, and NYC public event data to analyze mobility patterns, predict taxi trip duration, and explain model behavior using SHAP. The final implementation uses Spark for scalable taxi-data processing, pandas for analytics summaries, XGBoost for predictive modeling, Folium for interactive map visualization, and a command-line prediction interface for route-level demonstration. The completed pipeline processes approximately 2.9 million taxi trips and generates a trained model, SHAP plots, business insight charts, interactive maps, and sample user predictions. In the final experiment, the trip-duration model achieved an R2 of 0.843 and a mean absolute error of approximately 175.7 seconds on the test split. The results show that trip distance, time of day, and pickup/dropoff taxi zones are the strongest drivers of trip duration, while weather and citywide event context provide useful secondary signals."),
  h2("Keywords"),
  p("Urban mobility; NYC taxi; big data analytics; PySpark; XGBoost; SHAP; geospatial visualization; event-aware analysis; weather-aware prediction."),
  pageBreak(),
);

children.push(
  h1("1. Introduction and Motivation"),
  p("Urban transportation systems generate large volumes of operational data that can be used to understand traffic behavior, travel-time uncertainty, and mobility demand. In a dense city such as New York, taxi trips are influenced by distance, location, time of day, airports, weather conditions, and public events. For travelers, dispatchers, and city planners, a useful system should not only predict travel time but also explain why a prediction was made."),
  p("The motivation for this project is to build a practical mobility-intelligence pipeline that moves beyond static reporting. The system reads large taxi data, enriches it with external context, creates interpretable features, trains a prediction model, generates interactive geospatial outputs, and produces business-style insights suitable for a professor, stakeholder, or nontechnical audience. The project therefore combines big-data processing, machine learning, explainability, and visualization into one end-to-end solution."),
  h2("Project goals"),
  bullet("Integrate heterogeneous datasets: taxi trips, weather, and public events."),
  bullet("Create a scalable processing pipeline using Spark and pandas."),
  bullet("Engineer useful mobility features such as rush hour, airport trip flag, event level, and distance bucket."),
  bullet("Train and evaluate an XGBoost model to predict taxi trip duration."),
  bullet("Use SHAP explainability to identify which factors drive predictions."),
  bullet("Generate map, chart, and prediction-demo outputs for final presentation."),
  h1("2. Dataset Description"),
  p("The final project uses three aligned datasets. Taxi data is the primary mobility source. Weather and events provide external context. A taxi-zone lookup file is also used to translate pickup/dropoff zone IDs into readable zone names for analytics and reporting."),
  table(
    ["Dataset", "Final data used", "Role in project"],
    [
      ["NYC TLC Yellow Taxi Trip Records", "February 2023 Parquet file with 2,913,955 loaded rows", "Primary trip-level dataset containing timestamps, trip distance, fare/rate fields, pickup zone ID, dropoff zone ID, and trip duration after preprocessing."],
      ["Historical NYC Weather", "672 hourly observations for February 2023", "Adds hourly temperature, humidity, pressure, wind, and precipitation context aligned to trip pickup hour."],
      ["NYC Public Events", "13,576 event records for February 2023", "Adds citywide daily event counts and event-context features aligned to trip date."],
      ["TLC Taxi Zone Lookup", "265 zone records", "Maps numeric pickup/dropoff location IDs to readable borough and zone names for analytics outputs."],
    ],
    [2400, 2550, 4410],
  ),
  p("A key data limitation is that the current TLC yellow taxi file provides pickup and dropoff location IDs rather than exact pickup/dropoff latitude and longitude. This means exact street-level route reconstruction is not possible from this dataset alone. However, the location IDs still provide valuable zone-level geography and can be mapped more precisely in future work using TLC taxi-zone polygon shapefiles."),
  pageBreak(),
);

children.push(
  h1("3. System Architecture"),
  p("The system is organized as a modular analytics pipeline. Each source module owns one processing stage, while main.py orchestrates the full execution. The design makes the project easier to debug, test, explain, and extend."),
  table(
    ["File / module", "Purpose"],
    [
      ["main.py", "Runs the full Spark-based pipeline: load, preprocess, merge, feature engineering, clustering fallback, model training, SHAP, and map generation."],
      ["src/data_loading.py", "Loads taxi, weather, and event data from the raw data folder."],
      ["src/preprocessing.py", "Normalizes columns, parses dates, cleans event and weather data, and prepares taxi records."],
      ["src/merging.py", "Joins taxi trips to hourly weather and daily event counts."],
      ["src/feature_engineering.py", "Creates model features such as hour, rush hour, distance bucket, airport trip flag, event level, and weather bands."],
      ["src/modeling.py", "Trains and evaluates the XGBoost regression model."],
      ["src/shap_explainability.py", "Generates SHAP summary bar and beeswarm plots for model interpretation."],
      ["src/map_visualization.py", "Creates the Folium interactive map output."],
      ["src/analytics.py", "Generates final business-insight CSVs, Markdown summaries, and chart images."],
      ["predict_trip.py", "User-facing route prediction demo that accepts two locations and a timestamp."],
    ],
    [2600, 6760],
  ),
  h2("Pipeline flow"),
  numbered("Load raw taxi, weather, event, and taxi-zone files."),
  numbered("Clean timestamps, trip duration, distance, weather fields, and event fields."),
  numbered("Merge taxi trips with hourly weather using pickup hour and with event counts using pickup date."),
  numbered("Engineer predictive and analytical features."),
  numbered("Train XGBoost regression model for trip-duration prediction."),
  numbered("Generate SHAP explanations, interactive map, analytics charts, and route-prediction demo outputs."),
  h1("4. Key Technologies Used"),
  table(["Technology", "Use in the project"], techRows, [2700, 6660]),
  pageBreak(),
);

children.push(
  h1("5. Data Preprocessing and Feature Engineering"),
  p("The preprocessing stage standardizes inconsistent column names, converts pickup and dropoff timestamps, computes trip duration, removes invalid rows, and aligns external context. The feature-engineering stage converts raw values into model-ready variables that better represent real mobility conditions."),
  h2("Engineered features"),
  table(["Feature family", "Examples", "Why it matters"], featureRows, [1800, 3700, 3860]),
  h2("Explanation of two important engineered features"),
  p([text("distance_bucket", { bold: true }), text(" groups exact trip distance into interpretable categories such as very short, short/medium, long city trip, and very long trip. The model still uses the exact trip_distance feature, but the bucket gives an additional trip-type signal. This helps separate short neighborhood trips from long airport-style trips.")]),
  p([text("is_airport_trip", { bold: true }), text(" is a binary feature. It equals 1 when the pickup or dropoff zone corresponds to JFK, LaGuardia, or Newark airport. Airport trips are different because they are longer, often use highways, and follow different traffic and fare patterns compared with normal city trips.")]),
  h2("Outlier handling"),
  p("The final feature pipeline removes obviously invalid or noisy records before model training. It filters very short or extreme-duration trips, zero or unrealistic distances, impossible speeds, and unknown TLC zones. This step improved model quality substantially because the model learned from normal taxi behavior rather than data-entry or recording errors."),
  h1("6. Analytical Insights"),
  p("In addition to the model, the project generates business-insight outputs in outputs/analytics/insights. These insights translate technical summaries into presentation-ready findings: time-based mobility, event impact, weather impact, common corridors, and airport-trip behavior."),
  ...figure(img.hourly, 560, 300, "Hourly taxi duration and demand chart", "Figure 1. Hourly mobility analysis shows average duration and trip volume by hour."),
  pageBreak(),
);

const timeInsight = insightText("Time-Based Mobility");
const eventInsight = insightText("Event Impact");
const weatherInsight = insightText("Weather Impact");
const corridorInsight = insightText("Common Travel Corridors");
const airportInsight = insightText("Airport Trip Behavior");

children.push(
  h2("6.1 Time-based mobility"),
  p(timeInsight.key_metric + " " + timeInsight.insight + " " + timeInsight.why_it_matters),
  h2("6.2 Event impact"),
  p(eventInsight.key_metric + " " + eventInsight.insight + " " + eventInsight.why_it_matters),
  ...figure(img.event, 520, 292, "Event impact chart", "Figure 2. Average trip duration by event level."),
  h2("6.3 Weather impact"),
  p(weatherInsight.key_metric + " " + weatherInsight.insight + " " + weatherInsight.why_it_matters),
  ...figure(img.weather, 520, 292, "Weather impact chart", "Figure 3. Average trip duration by temperature band."),
  pageBreak(),
);

children.push(
  h2("6.4 Common travel corridors"),
  p(corridorInsight.key_metric + " " + corridorInsight.insight + " " + corridorInsight.why_it_matters),
  ...figure(img.zones, 560, 300, "Top pickup and dropoff zone pairs", "Figure 4. Most frequent pickup-dropoff zone pairs after filtering unknown zones."),
  h2("6.5 Airport trip behavior"),
  p(airportInsight.key_metric + " " + airportInsight.insight + " " + airportInsight.why_it_matters),
  ...figure(img.airport, 520, 292, "Airport versus non-airport trips", "Figure 5. Airport trips are longer and behave differently from normal city trips."),
  pageBreak(),
);

children.push(
  h1("7. Predictive Modeling and Evaluation"),
  p("The project uses XGBoost regression to predict trip_duration_sec. XGBoost was selected because it performs well on tabular data, handles nonlinear relationships, supports mixed feature scales, and integrates well with SHAP explainability. The model uses pre-trip features rather than payment-after-trip fields such as total_amount or tip_amount. This is important because a realistic prediction system should not depend on information that is only known after the trip is completed."),
  table(["Metric", "Final value", "Interpretation"], metricRows, [2100, 2200, 5060]),
  p("The final model performance is substantially stronger than the early baseline. After feature refinement and outlier filtering, the model achieved R2 = 0.843 and MAE = 175.7 seconds. This means the model explains approximately 84 percent of the test-set variation in trip duration and is typically within about 2.9 minutes of the actual trip duration."),
  h2("Model features"),
  p("The final model uses 23 features, including hour, day of week, month, weekend flag, rush-hour flag, trip distance, distance bucket, event count, event level, airport-trip flag, precipitation flag, temperature band, wind band, VendorID, RatecodeID, pickup and dropoff location IDs, temperature, humidity, precipitation, pressure, wind speed, and wind direction."),
  h1("8. Explainable AI with SHAP"),
  p("SHAP was used to interpret the XGBoost model. SHAP assigns each feature a contribution value for each prediction, allowing us to understand both global importance and directional impact."),
  ...figure(img.shapBar, 520, 389, "SHAP summary bar plot", "Figure 6. SHAP bar plot ranking the average impact of each feature."),
  pageBreak(),
);

children.push(
  p("The SHAP bar plot shows that trip_distance is the strongest driver by far. This is expected and supports the validity of the model: longer trips generally require more time. The next most influential features are hour, pickup location ID, distance bucket, dropoff location ID, and is_airport_trip. Weather variables such as pressure, wind speed, temperature, and humidity appear, but their effects are smaller than the core mobility features."),
  ...figure(img.shapBeeswarm, 520, 403, "SHAP beeswarm plot", "Figure 7. SHAP beeswarm plot showing how high and low feature values push predictions up or down."),
  p("The beeswarm plot gives a more detailed explanation. High trip_distance values push predictions to the right, increasing predicted trip time, while low distances push predictions lower. Hour also affects predictions, showing that time of day changes expected travel time. The airport-trip feature affects predictions because airport routes follow a different travel pattern. This aligns with the analytics finding that airport trips have much longer average duration and distance than non-airport trips."),
  pageBreak(),
);

children.push(
  h1("9. Interactive Map and Demonstration"),
  p("The interactive map is generated as urban_mobility_map.html. It visualizes mobility intensity, hotspot layers, event markers, and a congestion-severity legend. The map can be opened directly in a browser and used during the class demonstration. Because the TLC dataset uses pickup/dropoff zone IDs instead of exact coordinates, the map should be presented as a mobility-context and zone-level visualization rather than exact GPS route tracking."),
  ...figure(img.map, 560, 315, "Urban mobility map screenshot", "Figure 8. Interactive map output showing NYC mobility density, hotspots, event markers, and layer controls."),
  h2("Prediction demo"),
  p("The project also includes a user-facing command-line prediction interface. A user can provide two locations and a date/time, and the system estimates trip duration and congestion level. For example, the command below predicts a Times Square to JFK Airport trip at 5:30 PM on February 10, 2023:"),
  p("python predict_trip.py --pickup \"Times Square\" --dropoff \"JFK Airport\" --datetime \"2023-02-10 17:30\"", { alignment: AlignmentType.LEFT, run: { font: "Courier New", size: 20 } }),
  p("The resulting prediction estimated a distance of 18.26 miles, 511 events on that date, a trip duration of 49.7 minutes, and low congestion. Additional tests such as Grand Central to Wall Street and Penn Station to LaGuardia also produced distinct predictions, demonstrating that the system responds to route and time inputs rather than returning fixed values."),
  pageBreak(),
);

children.push(
  h1("10. Effectiveness of the Solution"),
  p("The solution is effective because it completes the full path from raw data to usable insight. It processes a large taxi dataset, integrates external weather and event context, generates a trained model, explains the model, and provides visual outputs for stakeholders. The model performance improved significantly after refined feature engineering and outlier handling, indicating that the final system is not only functional but also analytically meaningful."),
  h2("Strengths"),
  bullet("End-to-end pipeline that can be rerun from main.py."),
  bullet("Uses real-world datasets aligned by time and date."),
  bullet("Strong final model performance with R2 = 0.843 and MAE = 175.7 seconds."),
  bullet("SHAP plots provide transparent explanation of model behavior."),
  bullet("Business-insight charts make technical results understandable to nontechnical audiences."),
  bullet("Prediction interface turns the model into a usable demonstration tool."),
  h2("Limitations"),
  bullet("The TLC file does not contain exact pickup/dropoff latitude and longitude, so exact street-level taxi routes cannot be reconstructed."),
  bullet("Event impact is currently measured using citywide daily event counts, which are useful but too broad to fully explain local congestion."),
  bullet("Zone IDs are treated as numeric features; future work could encode zones more carefully or use geospatial embeddings."),
  bullet("The map can be improved by adding TLC taxi-zone polygon shapefiles and zone centroid mapping."),
  h1("11. Future Work"),
  p("The most valuable future improvement is to add taxi-zone shapefiles. This would allow the system to map pickup and dropoff zones as real polygons rather than relying on simplified visual layers. A second improvement is localized event analysis: instead of counting all NYC events on a date, the system should measure events near the pickup/dropoff zone or route area. Other improvements include Streamlit dashboard refinement, larger training runs, hyperparameter tuning, classification for congestion severity, and route-level comparison between two user-selected points."),
  h1("12. Conclusion"),
  p("The final project successfully delivers an Urban Mobility Intelligence System that integrates taxi, weather, and event data for analysis, prediction, explainability, and visualization. Compared with the progress-report stage, the project now includes aligned February 2023 datasets, improved feature engineering, a stronger predictive model, final SHAP outputs, business-insight analytics, a WPI-style presentation deck, and a working route prediction demo. The completed system shows that distance, time of day, pickup/dropoff zones, and airport-trip behavior are the most important drivers of NYC taxi trip duration, while weather and event context provide supporting insight. The result is a complete technical solution suitable for final presentation and demonstration."),
  pageBreak(),
);

children.push(
  h1("References"),
  p("[1] New York City Taxi and Limousine Commission. TLC Trip Record Data. https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page", { alignment: AlignmentType.LEFT }),
  p("[2] NYC Open Data. Public event and permitted event datasets. https://data.cityofnewyork.us/", { alignment: AlignmentType.LEFT }),
  p("[3] Open-Meteo. Historical weather API and archive data. https://open-meteo.com/", { alignment: AlignmentType.LEFT }),
  p("[4] Apache Spark Documentation. https://spark.apache.org/docs/latest/", { alignment: AlignmentType.LEFT }),
  p("[5] Chen, T. and Guestrin, C. 2016. XGBoost: A Scalable Tree Boosting System. Proceedings of KDD. https://arxiv.org/abs/1603.02754", { alignment: AlignmentType.LEFT }),
  p("[6] Lundberg, S. M. and Lee, S.-I. 2017. A Unified Approach to Interpreting Model Predictions. NeurIPS. https://arxiv.org/abs/1705.07874", { alignment: AlignmentType.LEFT }),
  p("[7] SHAP Documentation. https://shap.readthedocs.io/", { alignment: AlignmentType.LEFT }),
  p("[8] Folium Documentation. https://python-visualization.github.io/folium/", { alignment: AlignmentType.LEFT }),
);

const doc = new Document({
  creator: "Urban Mobility Intelligence Team",
  title: "Urban Mobility Intelligence Final Project Report",
  description: "Final project report for Big Data Analytics",
  styles: {
    default: {
      document: {
        run: { font: "Times New Roman", size: 22 },
        paragraph: { spacing: { after: 120, line: 276 } },
      },
    },
    paragraphStyles: [
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 28, bold: true, color: "A6192E", font: "Arial" },
        paragraph: { spacing: { before: 260, after: 120 }, outlineLevel: 0 },
      },
      {
        id: "Heading2",
        name: "Heading 2",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 24, bold: true, color: "222222", font: "Arial" },
        paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 1 },
      },
    ],
  },
  numbering: {
    config: [
      {
        reference: "section-numbering",
        levels: [
          {
            level: 0,
            format: LevelFormat.DECIMAL,
            text: "%1.",
            alignment: AlignmentType.LEFT,
            style: {
              paragraph: { indent: { left: 720, hanging: 360 } },
            },
          },
        ],
      },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          margin: { top: 720, right: 720, bottom: 720, left: 720 },
        },
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              children: [text("Urban Mobility Intelligence System - Final Project Report", { size: 16, color: "666666", font: "Arial" })],
              border: { bottom: { color: "A6192E", space: 1, style: BorderStyle.SINGLE, size: 6 } },
            }),
          ],
        }),
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              alignment: AlignmentType.RIGHT,
              children: [text("Page ", { size: 16, color: "666666", font: "Arial" }), PageNumber.CURRENT],
            }),
          ],
        }),
      },
      children,
    },
  ],
});

fs.mkdirSync(OUT_DIR, { recursive: true });
const buffer = await Packer.toBuffer(doc);
fs.writeFileSync(OUT, buffer);
console.log(OUT);
