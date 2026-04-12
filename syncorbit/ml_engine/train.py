import os
import random
import numpy as np
import joblib
from datetime import timedelta
import sklearn
from sklearn.linear_model import LogisticRegression
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from satellites.orbit import load_satellites, ts, GROUND_STATION

MODEL_DIR = os.path.dirname(__file__)
LOG_REG_PATH = os.path.join(MODEL_DIR, "logreg.pkl")
LSTM_PATH = os.path.join(MODEL_DIR, "lstm_model.h5")

SEQ_LENGTH = 10

def generate_training_data(num_samples=500):
    print("🛰️ Generating TLE-based training data...")
    sats = load_satellites()
    if not sats:
        raise ValueError("No satellites found.")
        
    sats = list(sats)       # Convert to list so shuffle works
    random.shuffle(sats)    # Randomise so we don't always train on the same 50
    sats = sats[:50]        # Subset to speed up generation
    
    X_snapshot = []
    y_snapshot = []
    
    X_sequence = []
    y_sequence = []
    
    t0 = ts.now()
    
    count = 0
    while count < num_samples:
        sat1, sat2 = np.random.choice(sats, 2, replace=False)
        seq_features = []
        t_start = ts.from_datetime(t0.utc_datetime() + timedelta(minutes=np.random.randint(0, 100)))
        
        for step in range(SEQ_LENGTH + 5):
            t = ts.from_datetime(t_start.utc_datetime() + timedelta(seconds=step*10))
            
            alt1, az1, _ = (sat1 - GROUND_STATION).at(t).altaz()
            elev1 = alt1.degrees
            rssi1 = -80 + (elev1 - 10) * (40 / 80) if elev1 > 10 else -100
            
            alt2, az2, _ = (sat2 - GROUND_STATION).at(t).altaz()
            elev2 = alt2.degrees
            rssi2 = -80 + (elev2 - 10) * (40 / 80) if elev2 > 10 else -100
            
            feat = [rssi1, rssi2, elev1, elev2]
            seq_features.append(feat)
            
            is_cand_better = 1 if (rssi2 > rssi1 + 3 and elev2 > 15) else 0
            if step > 0:
                X_snapshot.append(feat)
                y_snapshot.append(is_cand_better)
                
        for i in range(len(seq_features) - SEQ_LENGTH):
            chunk = seq_features[i:i+SEQ_LENGTH]
            last_feat = chunk[-1]
            first_feat = chunk[0]
            
            is_optimal = 1 if (last_feat[1] > last_feat[0] + 1 and first_feat[1] <= first_feat[0]) else 0
            X_sequence.append(chunk)
            y_sequence.append(is_optimal)
            count += 1
            if count >= num_samples:
                break
                
    return (np.array(X_snapshot), np.array(y_snapshot)), (np.array(X_sequence), np.array(y_sequence))

def train_models():
    (X_snap, y_snap), (X_seq, y_seq) = generate_training_data(1000)
    
    print("📈 Training Logistic Regression...")
    logreg = LogisticRegression()
    logreg.fit(X_snap, y_snap)
    joblib.dump(logreg, LOG_REG_PATH)
    print(f"✅ Saved Logistic Regression to {LOG_REG_PATH}")
    
    print("📈 Training LSTM...")
    model = Sequential([
        LSTM(32, input_shape=(SEQ_LENGTH, 4), return_sequences=False),
        Dense(16, activation='relu'),
        Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    model.fit(X_seq, y_seq, epochs=10, batch_size=32, verbose=1)
    model.save(LSTM_PATH)
    print(f"✅ Saved LSTM to {LSTM_PATH}")

if __name__ == "__main__":
    train_models()
