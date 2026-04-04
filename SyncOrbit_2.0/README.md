# SyncOrbit 🚀  
**Predictive Zero-Loss Handover Optimization for LEO Satellite Communication**

---

## 📌 Overview

SyncOrbit is a sophisticated system focused on improving **handover reliability in Low Earth Orbit (LEO) satellite communication systems**.  
Because LEO satellites move rapidly relative to Earth, ground stations must frequently switch connections between satellites. Poorly timed handovers result in **signal drops, packet loss, and degraded quality of service**.

This project provides a complete solution modeling **orbital physics, machine learning telemetry analysis, and predictive decision logic** to achieve **seamless, zero-loss handovers**.

---

## ❗ Problem Statement

- LEO satellites have **short contact durations** with single ground stations.
- Traditional handover methods are **reactive** (decisions happen *after* signal quality degrades).
- Reactive handovers cause packet loss, disconnections, and latency spikes.

## 💡 Our Solution

SyncOrbit completely replaces reactive architecture with a **predictive handover optimization framework**:

- **Real-time Orbital Parsing**: Ingests Celestrak TLE (Two-Line Element) data using `skyfield` to model satellite trajectories and predict visibility parameters.
- **Dual ML Pipeline**:
  - **Logistic Regression**: Identifies the optimal candidate satellite out of all visible targets.
  - **LSTM (Long Short-Term Memory)**: Analyzes time-series signal data to predict the precise handover crossover point long before signal degradation.
- **Virtual Packet Buffer**: Intelligently intercepts and buffers mid-flight packets during the physical handover switch, instantly replaying them to the new link.
- **Zero-Loss Guarantee**: Ensures 100% data integrity with **0 dropped packets**.

---

## 🛠️ Tech Stack

- **Backend Framework**: Django
- **Orbital Mechanics**: Skyfield, SGP4
- **Machine Learning**: TensorFlow/Keras (LSTM), Scikit-Learn (Logistic Regression)
- **Frontend / Dashboards**: HTML5 Canvas, Chart.js, Vanilla CSS
- **Hardware Integration**: RTL-SDR hardware support (`pyrtlsdr`)

---

## 🚀 How to Run

Follow these steps to run the SyncOrbit simulation and dashboards locally.

### 1. Prerequisites
Ensure you have Python 3.9+ installed on your system.

### 2. Install Dependencies
Navigate to the root directory containing `requirements.txt` and install the required packages:

```bash
pip install -r requirements.txt
```

### 3. Run the Django Server
Navigate into the `syncorbit` project folder and start the server:

```bash
cd syncorbit
python manage.py runserver
```

### 4. Access the Dashboards
Open your browser and navigate to:
- **Handover Simulation Canvas**: [http://127.0.0.1:8000/simulation/](http://127.0.0.1:8000/simulation/)
  *Watch the live, automated zero-loss handover process between two modeled satellites and dual geographical ground stations.*
- **System Telemetry Dashboard**: [http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/)
  *Monitor the live ML engine confidence scores, satellite elevations, packet stats, and the waterfall frequency plot.*

---

## 🧠 System Architecture

1. **Telemetry Ingestion**: Real-time TLE sync and parsing.
2. **Feature Extraction**: Elevation and RSSI calculations.
3. **ML Prediction**: LSTM sequence processing over a 10-tick sliding window.
4. **Buffer Controller**: State-machine logic managing the `handoverActive` cycle.
5. **Zero-Loss Resolution**: Buffer flush and active link switch.

---

## 👨‍💻 Author

**Harsh Kumar**  
B.Tech Computer Science Engineering  
Interests: AI & ML, Python Programming, Embedded Systems, Space & Intelligent Systems.

---

## 📄 License

This project is intended for educational and research purposes.
