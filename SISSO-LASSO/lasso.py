import pandas as pd
import numpy as np
from sklearn.linear_model import LassoCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

data = pd.read_csv('test.csv')

X = data.iloc[:, 2:].values  # 特征：从第三列到最后
y = data.iloc[:, 1].values   # 目标值：第二列

feature_names = data.columns[2:].values

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=42)

lasso_cv = LassoCV(cv=5)  # 进行 5 折交叉验证来选择最佳的 alpha
lasso_cv.fit(X_train, y_train)

print(f'Best alpha: {lasso_cv.alpha_}')

coefficients = lasso_cv.coef_

importance = np.abs(coefficients)  # 计算系数的绝对值（即特征的重要性）
sorted_indices = np.argsort(importance)[::-1]  # 对特征重要性排序，按从大到小排列

print("\nFeature importance ranking (sorted by coefficient magnitude):")
for idx in sorted_indices:
    print(f"Feature: {feature_names[idx]}, Coefficient: {coefficients[idx]}, Importance: {importance[idx]}")

selected_features_cv = feature_names[coefficients != 0]

top_features_indices = sorted_indices[:4]  # 选择前 4 个特征
top_features_cv = feature_names[top_features_indices]
top_coeffs_cv = coefficients[top_features_indices]

print(f'\nSelected top 4 features after CV: {top_features_cv}')

expression_cv = "y = "
for i, coef in enumerate(top_coeffs_cv):
    expression_cv += f"{coef} * {top_features_cv[i]} + "

expression_cv = expression_cv.strip(" +")
print(f'\nModel expression after CV: {expression_cv}')

y_pred = lasso_cv.predict(X_test)

mse = mean_squared_error(y_test, y_pred)
print(f'Mean Squared Error (MSE): {mse}')
df = pd.DataFrame({
        'y_test': y_test,
            'y_pred': y_pred
})

df.to_excel('predictions.xlsx', index=False)





