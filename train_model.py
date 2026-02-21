import sqlite3
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
import joblib

# ─────────────────────────────────────────────
#  LOAD DATA FROM DATABASE
# ─────────────────────────────────────────────
def load_training_data():
    """Load historical test results from database"""
    conn = sqlite3.connect("database.db")
    query = """
        SELECT stress, anxiety, sleep, focus, social, sadness, energy, overwhelm, result
        FROM test_results
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# ─────────────────────────────────────────────
#  PREPARE DATA FOR MODEL
# ─────────────────────────────────────────────
def prepare_features(df):
    """
    Features: the 8 mental health dimensions
    Target: binary classification (1 = needs support, 0 = doing well)
    """
    
    # Create features
    features = ['stress', 'anxiety', 'sleep', 'focus', 'social', 'sadness', 'energy', 'overwhelm']
    X = df[features]
    
    # Create binary target: 1 if "High/Severe", 0 if "Excellent/Moderate"
    # You can customize this threshold based on your data
    y = df['result'].isin(['High Stress & Anxiety', 'Severe Distress Detected']).astype(int)
    
    return X, y


# ─────────────────────────────────────────────
#  TRAIN LOGISTIC REGRESSION MODEL
# ─────────────────────────────────────────────
def train_model():
    """Train and save the Logistic Regression model"""
    
    # Load data
    df = load_training_data()
    
    if len(df) < 10:
        print("⚠️  Not enough training data. Need at least 10 samples.")
        print("The model will be trained once more data is collected.")
        return False
    
    # Prepare features
    X, y = prepare_features(df)
    
    # Split data: 80% training, 20% testing
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Normalize features (important for Logistic Regression)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train Logistic Regression model
    model = LogisticRegression(
        random_state=42,
        max_iter=1000,
        class_weight='balanced'  # handles imbalanced data
    )
    model.fit(X_train_scaled, y_train)
    
    # Evaluate model
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_pred_proba)
    
    print("=" * 50)
    print("🤖 MODEL TRAINING REPORT")
    print("=" * 50)
    print(f"Training samples: {len(X_train)}")
    print(f"Testing samples:  {len(X_test)}")
    print(f"Accuracy:  {accuracy:.2%}")
    print(f"Precision: {precision:.2%}")
    print(f"Recall:    {recall:.2%}")
    print(f"AUC-ROC:   {auc:.2%}")
    print("=" * 50)
    
    # Feature importance (coefficients)
    feature_importance = pd.DataFrame({
        'Feature': X.columns,
        'Coefficient': model.coef_[0]
    }).sort_values('Coefficient', ascending=False)
    
    print("\n📊 FEATURE IMPORTANCE:")
    print(feature_importance.to_string(index=False))
    
    # Save model and scaler
    joblib.dump(model, 'models/logistic_model.pkl')
    joblib.dump(scaler, 'models/scaler.pkl')
    
    print("\n✅ Model and scaler saved to 'models/' directory")
    return True


if __name__ == '__main__':
    train_model()