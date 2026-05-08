# AeroNet Lite — Autonomous Drone Delivery Simulation

A simulation of an autonomous drone delivery system built on a 10x10 city grid. The system validates city layouts, selects drone fleets, plans delivery routes, handles disruptions in real time, forecasts demand, and detects flight anomalies.

Built as a semester project for BS Data Science — AI, Spring 2026.

---

## Project Structure

```
aeronet_lite/
  data/
    raw/              # Original datasets (not tracked by git)
    processed/        # Trained model .pkl files
  src/
    grid_model.py         # Shared 10x10 grid data model
    layout_validator.py   # CSP-based layout constraint checker
    fleet_selector.py     # Heuristic / GA fleet selection
    astar_planner.py      # A* delivery path planner
    delivery_simulator.py # 20-step simulation engine
    ml_pipeline.py        # Demand forecasting and anomaly detection
    visualization.py      # Grid, route, and heatmap plots
    main.py               # Entry point
  notebooks/
    demand_forecasting.ipynb    # Regression model training
    anomaly_classifier.ipynb    # Classification model training
  report/
    figures/          # Saved plots
    final_report.docx
  requirements.txt
  README.md
```

---

## Modules

### Module 1 — Grid Model and Layout Validator
Defines the shared 10x10 grid. Each cell holds zone type, population density, hub and charging flags, no-fly status, and demand value. The layout validator checks four CSP constraints and reports any violations with suggested fixes.

### Module 2 — Fleet Selector
Selects a combination of light and heavy drones under a fixed budget. Uses a heuristic scoring function or a Genetic Algorithm. Output is a list of assigned drones used by the path planner and simulator.

### Module 3 — A* Path Planner and Disruption Handler
Plans routes for each delivery as hub to pickup to drop-off to hub using A* search. Avoids no-fly cells. If a no-fly cell is activated mid-simulation, affected drones are rerouted automatically from their current position.

### Module 4 — ML Pipeline
Provides two callable functions used during the simulation:

- `get_demand_forecast()` — predicts hourly delivery demand using a trained Random Forest regressor
- `detect_anomaly()` — classifies drone telemetry as Normal, Battery Anomaly, Route Anomaly, or Sensor Spike using a trained Random Forest classifier

Additional helpers include `get_grid_demand()` for full grid demand arrays, `detect_anomalies_batch()` for checking all active drones at once, and `assign_demand_to_grid()` for writing forecasts directly into the shared grid model.

### Module 5 — Visualization and Integration
Renders the zone map, route overlays, demand heatmap, and anomaly event log. Integrates all modules and drives the 20-step simulation through main.py.

---

## Setup

Clone the repository and set up a virtual environment.

```bash
git clone <repo-url>
cd aeronet_lite
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # Mac / Linux
pip install -r requirements.txt
```

---

## Running the ML Pipeline

The ML pipeline requires trained model files before it can be used. Run the notebooks first in this order.

**Step 1 — Train the demand forecasting model**

Open and run all cells in `notebooks/demand_forecasting.ipynb`. This saves the following files to `data/processed/`:
- `demand_model.pkl`
- `demand_scaler.pkl`

The notebook requires `data/raw/bike-sharing/train.csv` from the Kaggle Bike Sharing Demand dataset.

**Step 2 — Train the anomaly classifier**

Open and run all cells in `notebooks/anomaly_classifier.ipynb`. This saves:
- `anomaly_model.pkl`
- `anomaly_scaler.pkl`
- `anomaly_label_encoder.pkl`

This notebook generates its own synthetic drone telemetry data. No external dataset is required.

**Step 3 — Verify the pipeline**

```bash
cd src
python ml_pipeline.py
```

All status checks should show Yes and all self-tests should pass.

---

## Importing the ML Pipeline in Other Modules

```python
from ml_pipeline import get_demand_forecast, detect_anomaly, get_grid_demand, assign_demand_to_grid

# Predict demand for a single hour
demand = get_demand_forecast(hour=8, season=2, workingday=1, weather=1)

# Classify a drone telemetry reading
result = detect_anomaly(battery_drop=35.0, route_deviation=1.0)
print(result['label'], result['is_anomaly'])

# Populate demand across the full grid
grid = assign_demand_to_grid(grid, hour=14, season=2)
```

---

## Datasets

| Purpose | Source |
|---|---|
| Demand forecasting | Kaggle — Bike Sharing Demand (train.csv) |
| Anomaly detection | Synthetic data generated in notebook |

Raw data files are not tracked by git. Each team member downloads their own copy and places it in `data/raw/`.

---

## Team

| Member | Module |
|---|---|
| 1 | Grid model and CSP layout validator |
| 2 | Fleet selector |
| 3 | A* path planner and disruption handler |
| 4 | ML pipeline |
| 5 | Visualization and integration |

---

*This README will be updated as modules are completed and integrated.*