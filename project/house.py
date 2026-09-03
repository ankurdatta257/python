"""
House Price Prediction
------------------------
A beginner ML project that predicts median house value using the
California Housing dataset (bundled locally as data/housing.csv,
so it works fully offline).

Author: <your name here>
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score


# ----------------------------
# 1. Load the data
# ----------------------------
df = pd.read_csv("data/housing.csv")

print("First 5 rows:")
print(df.head())

print("\nDataset shape:", df.shape)
print("\nMissing values per column:\n", df.isnull().sum())


# ----------------------------
# 2. Clean the data
# ----------------------------
# 'total_bedrooms' has some missing values -> fill with median
df["total_bedrooms"] = df["total_bedrooms"].fillna(df["total_bedrooms"].median())

# 'ocean_proximity' is categorical (text) -> convert to numeric columns
df = pd.get_dummies(df, columns=["ocean_proximity"], drop_first=True)


# ----------------------------
# 3. Explore the data
# ----------------------------
plt.figure(figsize=(10, 8))
sns.heatmap(df.corr(numeric_only=True), annot=True, fmt=".2f", cmap="coolwarm")
plt.title("Feature Correlation Heatmap")
plt.tight_layout()
plt.savefig("correlation_heatmap.png")
plt.close()
print("\nSaved correlation_heatmap.png")


# ----------------------------
# 4. Prepare features & target
# ----------------------------
X = df.drop("median_house_value", axis=1)   # features
y = df["median_house_value"]                # target

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Scale features (helps Linear Regression converge better)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)


# ----------------------------
# 5. Train models
# ----------------------------
# Model 1: Linear Regression
lin_reg = LinearRegression()
lin_reg.fit(X_train_scaled, y_train)
lin_preds = lin_reg.predict(X_test_scaled)

# Model 2: Random Forest (usually performs better, no scaling needed)
rf_reg = RandomForestRegressor(n_estimators=100, random_state=42)
rf_reg.fit(X_train, y_train)
rf_preds = rf_reg.predict(X_test)


# ----------------------------
# 6. Evaluate models
# ----------------------------
def evaluate(name, y_true, y_pred):
    rmse = mean_squared_error(y_true, y_pred) ** 0.5
    r2 = r2_score(y_true, y_pred)
    print(f"\n{name}")
    print(f"  RMSE: {rmse:.2f}")
    print(f"  R^2 Score: {r2:.4f}")


evaluate("Linear Regression", y_test, lin_preds)
evaluate("Random Forest", y_test, rf_preds)


# ----------------------------
# 7. Feature importance (Random Forest)
# ----------------------------
importances = pd.Series(rf_reg.feature_importances_, index=X.columns)
importances = importances.sort_values(ascending=False)

plt.figure(figsize=(8, 5))
importances.plot(kind="bar")
plt.title("Feature Importance (Random Forest)")
plt.ylabel("Importance")
plt.tight_layout()
plt.savefig("feature_importance.png")
plt.close()
print("\nSaved feature_importance.png")

print("\nDone! Check the generated PNG files for visualizations.")
