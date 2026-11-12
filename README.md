# 🚖 Urban Mobility Intelligence System

## Traffic Analysis and Prediction using Big Data and Explainable AI

An end-to-end Urban Mobility Intelligence System that integrates NYC taxi trips, weather conditions, and public event data to analyze traffic patterns, predict taxi trip duration, and generate explainable mobility insights using machine learning and SHAP Explainable AI.

---

# 📌 Project Overview

Urban transportation systems generate massive amounts of mobility data every day. However, understanding traffic behavior requires more than prediction alone — it requires explainability, contextual understanding, and visualization.

This project combines:
- 🚕 NYC Taxi Trip Data
- 🌦 Historical Weather Data
- 🎉 NYC Public Event Data

to build a scalable analytics system capable of:
- Predicting taxi trip duration
- Identifying congestion patterns
- Explaining model predictions
- Visualizing urban mobility behavior

---

# 🎯 Project Objectives

- Build a scalable urban mobility analytics pipeline
- Integrate multiple real-world datasets
- Predict taxi trip duration using machine learning
- Apply Explainable AI (SHAP) for transparency
- Generate business and mobility insights
- Create interactive visualization outputs
- Demonstrate practical route prediction

---

# 📊 Datasets Used

| Dataset | Description | Size |
|----------|-------------|------|
| NYC TLC Yellow Taxi Trips | Taxi trip records including pickup/dropoff zones, distance, timestamps | 2.9 Million Trips |
| Historical Weather Data | Temperature, humidity, wind, pressure, precipitation | 672 Hourly Records |
| NYC Public Events | Event records aligned with trip dates | 13,576 Events |
| TLC Taxi Zone Lookup | Zone IDs mapped to boroughs and zone names | 265 Zones |

---

# ⚙️ Tech Stack

## Big Data Processing
- Apache Spark
- PySpark

## Machine Learning
- XGBoost
- Scikit-learn

## Explainable AI
- SHAP (SHapley Additive exPlanations)

## Visualization
- Folium
- Leaflet
- Streamlit

## Data Processing
- Pandas
- NumPy

## Programming Language
- Python

---

# 🧠 System Architecture

```text
Taxi + Weather + Events
            ↓
    Data Preprocessing
            ↓
    Feature Engineering
            ↓
      XGBoost Model
            ↓
   SHAP Explainability
            ↓
 Interactive Map + Demo
```

---

# 🔧 Key Features

✅ Multi-source data integration  
✅ Big data preprocessing using Spark  
✅ Feature engineering pipeline  
✅ XGBoost regression modeling  
✅ SHAP explainability analysis  
✅ Interactive congestion map  
✅ Business insight analytics  
✅ User-facing prediction interface  

---

# 📈 Model Performance

| Metric | Result |
|--------|--------|
| R² Score (chronological holdout) | 0.7858 |
| MAE (chronological holdout) | 189.98 seconds (3.17 minutes) |
| Linear regression baseline MAE | 232.59 seconds |
| Mean baseline MAE | 474.72 seconds |
| Modeling Dataset | 48,162 rows; approximately 80% train / 20% test |
| Taxi records loaded | 2,913,955 |

### Interpretation
On a held-out **later-in-time** test partition (training through February 23, 2023, 15:32:16; testing from 15:32:26), XGBoost explains approximately **78.6% of the variance** in observed trip duration and achieves a **mean absolute error of 3.17 minutes**. MAE is an average absolute error, not a guarantee that individual predictions fall within that range. These results were reproduced locally on November 12, 2026. The model uses training-only median imputation and excludes post-trip payment fields. Historical scores from a different evaluation setup are not directly comparable.

---

# 🔍 Explainable AI (SHAP)

The project uses SHAP to interpret the XGBoost model and understand feature influence.

## Key Findings
- Trip distance is the strongest predictor
- Time of day significantly affects travel time
- Pickup/dropoff zones influence congestion
- Airport trips follow distinct travel patterns
- Weather provides contextual influence

This improves transparency and trust in model predictions.

---

# 📊 Business Insights

The system generates mobility insights including:

- Peak traffic demand hours
- Slowest travel windows
- Airport trip behavior
- Common travel corridors
- Weather impact analysis
- Event impact analysis

### Example Insights
- Peak demand occurs around **6 PM**
- Slowest trips occur around **2 PM**
- Airport trips are significantly longer than normal city trips

---

# 🗺️ Interactive Visualization

The project generates an interactive Folium-based map containing:

- Traffic density layers
- Congestion hotspots
- Event overlays
- Layer controls
- Mobility visualizations

The map can be explored directly in a browser.

---

# 💻 Route Prediction Demo

The project includes a command-line prediction tool where users can estimate trip duration using custom routes and timestamps.

## Example

```bash
python predict_trip.py --pickup "Times Square" --dropoff "JFK Airport" --datetime "2023-02-10 17:30"
```

## Example Output

```text
Pickup: Times Square
Dropoff: JFK Airport
Approx distance used: 18.26 miles
Estimated duration: 57.9 minutes
Estimated congestion: Low
```

This example was generated using the locally retrained model for February 24, 2023, at 17:30. It uses an approximate distance (straight-line distance × 1.35), **not** a routing API; the congestion label is a speed-based proxy rather than observed traffic.\n\nThe system dynamically changes predictions based on:
- route
- time
- distance
- contextual conditions

---

# ▶️ Installation & Setup

## 1️⃣ Clone Repository

```bash
git clone https://github.com/gandhali07/urban-mobility-intelligence-system.git
```

---

## 2️⃣ Navigate to Project

```bash
cd urban-mobility-intelligence-system
```

---

## 3️⃣ Install Requirements

```bash
pip install -r requirements.txt -c constraints.txt
```

---

## 4️⃣ Run Automated Tests

```bash
python -m unittest discover -s tests -v
```

---

## 5️⃣ Run Main Pipeline

```bash
python main.py
```

---

## 6️⃣ Run Prediction Demo

```bash
python predict_trip.py --pickup "Times Square" --dropoff "JFK Airport" --datetime "2023-02-10 17:30"
```

---

## 7️⃣ Run Streamlit Dashboard

```bash
streamlit run streamlit_app.py
```

---

# ⚠️ Limitations

- Taxi dataset does not provide exact GPS coordinates
- Event data is citywide rather than localized
- Spatial analysis is zone-level rather than street-level
- The CLI approximates road distance unless `--trip-distance` is supplied; this differs from recorded trip distance used in training
- Congestion is inferred from predicted average speed, not independently validated against live traffic
- Historical weather and event inputs are not real-time forecasts; coverage and date matching may be incomplete
- Training uses a sampled subset of the processed taxi trips, not all 2.9 million records
- Model scores are measured on historical held-out data, not on live deployed trips

---

# 🚀 Future Improvements

- Real-time traffic streaming
- Geospatial polygon mapping
- Localized event modeling
- Deep learning approaches
- Advanced route optimization
- Real-time congestion forecasting

---

# 👥 Team Members

- Gandhali Sheth
- Nithish Kumar Bhupathi
- Aditya Pavan Sattenapalli
- Raghav Reddy

---

# 📚 References

- NYC TLC Taxi Dataset
- Open-Meteo Weather Data
- NYC Open Data Events
- Apache Spark Documentation
- XGBoost Documentation
- SHAP Documentation

---

# 📄 License

This project is developed for academic and educational purposes as part of the Big Data Analytics course.
