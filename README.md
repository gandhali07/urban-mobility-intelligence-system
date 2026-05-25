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
| R² Score | 0.843 |
| MAE | 175.7 seconds |
| Modeling Dataset | 48,305 rows |
| Total Taxi Trips Processed | 2.9 Million |

### Interpretation
The model explains approximately **84% of the variance** in taxi trip duration and predicts travel time within approximately **2.9 minutes** of the actual value.

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
Estimated duration: 49.7 minutes
Estimated congestion: Low
```

The system dynamically changes predictions based on:
- route
- time
- distance
- contextual conditions

---

# 📂 Project Structure

```text
BDA_Final_Project/
│
├── src/
│   ├── data_loading.py
│   ├── preprocessing.py
│   ├── merging.py
│   ├── feature_engineering.py
│   ├── modeling.py
│   ├── shap_explainability.py
│   ├── analytics.py
│   └── map_visualization.py
│
├── notebooks/
├── scripts/
├── outputs/
│
├── main.py
├── predict_trip.py
├── streamlit_app.py
├── requirements.txt
├── README.md
└── .gitignore
```

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
pip install -r requirements.txt
```

---

## 4️⃣ Run Main Pipeline

```bash
python main.py
```

---

## 5️⃣ Run Prediction Demo

```bash
python predict_trip.py --pickup "Times Square" --dropoff "JFK Airport" --datetime "2023-02-10 17:30"
```

---

## 6️⃣ Run Streamlit Dashboard

```bash
streamlit run streamlit_app.py
```

---

# ⚠️ Limitations

- Taxi dataset does not provide exact GPS coordinates
- Event data is citywide rather than localized
- Spatial analysis is zone-level rather than street-level

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
