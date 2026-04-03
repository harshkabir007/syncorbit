import joblib
import numpy as np
import os
from sklearn.ensemble import RandomForestClassifier

# Simple synthetic training data
X = []
y = []

for _ in range(500):
    curr_rssi = np.random.uniform(-90, -60)
    cand_rssi = np.random.uniform(-90, -50)
    curr_elev = np.random.uniform(10, 80)
    cand_elev = np.random.uniform(10, 80)

    X.append([curr_rssi, cand_rssi, curr_elev, cand_elev])

    # Label: handover if candidate is clearly better
    y.append(1 if cand_rssi - curr_rssi > 5 else 0)

X = np.array(X)
y = np.array(y)

model = RandomForestClassifier(n_estimators=100)
model.fit(X, y)

# Save model
MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "model.pkl"
)

joblib.dump(model, MODEL_PATH)
print("✅ ML model trained & saved at:", MODEL_PATH)
