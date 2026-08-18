import os, sys, glob
import numpy as np
import pandas as pd
import lightgbm as lgb
import shap
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

OUTPUT_DIR = r'c:\Users\ranje\sales forcasting\explainable_forecasting'
PLOT_DIR = os.path.join(OUTPUT_DIR, 'plots')
os.makedirs(PLOT_DIR, exist_ok=True)

DATA_DIR = r'c:\Users\ranje\sales forcasting\times_series\dataset'
DRUGS = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']

train_df = pd.read_csv(os.path.join(DATA_DIR, 'train_daily.csv'))
val_df   = pd.read_csv(os.path.join(DATA_DIR, 'val_daily.csv'))
test_df  = pd.read_csv(os.path.join(DATA_DIR, 'test_daily.csv'))

for df in [train_df, val_df, test_df]:
    df['date'] = pd.to_datetime(df['date'])

full_train_df = pd.concat([train_df, val_df]).sort_values('date').set_index('date')
test_df_idx   = test_df.set_index('date')

# 1. Model Family Comparison Rationale Dataframe
def export_model_comparison_rationale():
    comparison_records = [
        {
            'Model Family': 'Tree-Based Machine Learning',
            'Representative Models': 'LightGBM, XGBoost',
            'Test Accuracy (RMSLE)': '0.458 - 0.537 (Top Rank)',
            'Interpretability Level': 'High (Exact SHAP TreeExplainer)',
            'Explainability Method': 'SHAP Additive Attribution',
            'Selection Decision': 'SELECTED (Champion Engine)',
            'Why Selected / Rejected': 'Achieved highest accuracy + exact polynomial-time SHAP tree attribution.'
        },
        {
            'Model Family': 'Statistical Trend Models',
            'Representative Models': 'Meta Prophet',
            'Test Accuracy (RMSLE)': '0.493 - 0.569',
            'Interpretability Level': 'High (Component Decomposition)',
            'Explainability Method': 'Trend + Seasonality Curves',
            'Selection Decision': 'SELECTED (Ensemble Partner)',
            'Why Selected / Rejected': 'Provides transparent visual trend/weekly/annual additive components.'
        },
        {
            'Model Family': 'Classical Time-Series',
            'Representative Models': 'ARIMA, Holt-Winters ETS, SARIMAX',
            'Test Accuracy (RMSLE)': '0.509 - 0.718',
            'Interpretability Level': 'Moderate (Linear Coefficients)',
            'Explainability Method': 'AR / MA Polynomial Params',
            'Selection Decision': 'SELECTED FOR HIGH-ZERO (N05C)',
            'Why Selected / Rejected': 'Excellent for zero-inflated data; limited non-linear feature interaction.'
        },
        {
            'Model Family': 'Deep Neural Networks',
            'Representative Models': 'PyTorch LSTM, Temporal Fusion Transformer',
            'Test Accuracy (RMSLE)': '0.526 - 1.100',
            'Interpretability Level': 'Low (Black-Box Hidden Layers)',
            'Explainability Method': 'Integrated Gradients / Attention',
            'Selection Decision': 'REJECTED FOR EXPLAINABILITY',
            'Why Selected / Rejected': 'Suffered from lower test accuracy + complex non-linear black-box weights.'
        }
    ]
    comp_df = pd.DataFrame(comparison_records)
    comp_df.to_csv(os.path.join(OUTPUT_DIR, 'explainable_model_comparison.csv'), index=False)
    return comp_df

def build_explainable_features(df_all, drug):
    feat = pd.DataFrame(index=df_all.index)
    series = df_all[drug]
    
    feat['lag_1']  = series.shift(1)
    feat['lag_2']  = series.shift(2)
    feat['lag_7']  = series.shift(7)
    feat['lag_14'] = series.shift(14)
    
    feat['rolling_mean_7']  = series.shift(1).rolling(7).mean()
    feat['rolling_std_7']   = series.shift(1).rolling(7).std()
    feat['rolling_mean_14'] = series.shift(1).rolling(14).mean()
    feat['rolling_mean_28'] = series.shift(1).rolling(28).mean()
    
    dof = feat.index.dayofyear
    dow = feat.index.dayofweek
    feat['sin_dayofyear']  = np.sin(2 * np.pi * dof / 365.25)
    feat['cos_dayofyear']  = np.cos(2 * np.pi * dof / 365.25)
    feat['sin_dayofweek']  = np.sin(2 * np.pi * dow / 7.0)
    feat['cos_dayofweek']  = np.cos(2 * np.pi * dow / 7.0)
    feat['dayofweek']      = dow
    feat['month']          = feat.index.month
    feat['is_weekend']     = (dow >= 5).astype(float)
    
    return feat

def explain_drug_forecast(drug):
    combined_df = pd.concat([full_train_df, test_df_idx])
    feat_matrix = build_explainable_features(combined_df, drug)
    
    y_tr = np.log1p(full_train_df[drug].dropna())
    X_tr = feat_matrix.loc[y_tr.index].fillna(0)
    
    y_ts = test_df_idx[drug].dropna()
    X_ts = feat_matrix.loc[y_ts.index].fillna(0)
    
    model = lgb.LGBMRegressor(
        num_leaves=31, max_depth=4, learning_rate=0.03, n_estimators=300,
        random_state=42, verbose=-1, n_jobs=-1
    )
    model.fit(X_tr, y_tr)
    
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_ts)
    base_value  = explainer.expected_value
    
    mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
    global_imp_df = pd.DataFrame({
        'drug_category': drug,
        'feature': X_ts.columns,
        'mean_abs_shap': mean_abs_shap
    }).sort_values('mean_abs_shap', ascending=False).reset_index(drop=True)
    
    def categorize_feature(feat_name):
        if 'lag' in feat_name:
            return 'Historical Sales Lag'
        elif 'rolling' in feat_name:
            return 'Rolling Window Stat'
        elif 'dayofyear' in feat_name or 'month' in feat_name:
            return 'Annual Seasonality'
        elif 'dayofweek' in feat_name or 'weekend' in feat_name:
            return 'Weekly Seasonality'
        else:
            return 'Time/Calendar'
            
    global_imp_df['feature_domain'] = global_imp_df['feature'].apply(categorize_feature)
    
    sample_records = []
    for i in range(min(15, len(X_ts))):
        dt = X_ts.index[i]
        actual_val = y_ts.iloc[i]
        pred_log   = model.predict(X_ts.iloc[[i]])[0]
        pred_val   = np.expm1(pred_log)
        
        pos_idx = np.argmax(shap_values[i])
        neg_idx = np.argmin(shap_values[i])
        
        sample_records.append({
            'date': dt.strftime('%Y-%m-%d'),
            'drug_category': drug,
            'actual_sales': actual_val,
            'predicted_sales': round(pred_val, 2),
            'base_value_log': round(base_value, 4),
            'top_positive_driver': f"{X_ts.columns[pos_idx]} (+{shap_values[i][pos_idx]:.3f})",
            'top_negative_driver': f"{X_ts.columns[neg_idx]} ({shap_values[i][neg_idx]:.3f})",
            'prediction_direction': 'UP (Above Base)' if pred_log > base_value else 'DOWN (Below Base)'
        })
        
    sample_attr_df = pd.DataFrame(sample_records)
    
    plt.figure(figsize=(10, 6), dpi=300)
    top_10 = global_imp_df.head(10)
    sns.barplot(data=top_10, x='mean_abs_shap', y='feature', palette='viridis')
    plt.title(f'SHAP Global Feature Importance — Drug Category: {drug}', fontsize=13, fontweight='bold', pad=15)
    plt.xlabel('Mean |SHAP Value| (Impact on Forecast Magnitude)', fontsize=11, fontweight='bold')
    plt.ylabel('Feature Name', fontsize=11, fontweight='bold')
    plt.tight_layout()
    
    chart_path = os.path.join(PLOT_DIR, f'shap_importance_{drug}.png')
    plt.savefig(chart_path, dpi=120, bbox_inches='tight')
    plt.close()
    
    return global_imp_df, sample_attr_df

def run_explainable_forecasting_suite():
    print("==========================================================================")
    print("  RUNNING EXPLAINABLE FORECASTING SUITE (MODEL COMPARISON & SHAP)")
    print("==========================================================================")
    
    comp_df = export_model_comparison_rationale()
    print("\n--- MODEL FAMILY COMPARISON FOR EXPLAINABILITY ---")
    print(comp_df[['Model Family', 'Test Accuracy (RMSLE)', 'Interpretability Level', 'Selection Decision']].to_string(index=False))
    
    all_global_imp = []
    all_sample_attr = []
    
    for drug in DRUGS:
        g_imp, s_attr = explain_drug_forecast(drug)
        all_global_imp.append(g_imp)
        all_sample_attr.append(s_attr)
        
        top_feat = g_imp.iloc[0]['feature']
        top_impact = g_imp.iloc[0]['mean_abs_shap']
        print(f"[{drug}] Top Influential Driver: '{top_feat}' (Impact: {top_impact:.4f})")

    full_global_imp_df = pd.concat(all_global_imp, ignore_index=True)
    full_sample_attr_df = pd.concat(all_sample_attr, ignore_index=True)
    
    global_csv_path = os.path.join(OUTPUT_DIR, 'explainable_forecasting_summary.csv')
    sample_csv_path = os.path.join(OUTPUT_DIR, 'explainable_shap_breakdown.csv')
    
    full_global_imp_df.to_csv(global_csv_path, index=False)
    full_sample_attr_df.to_csv(sample_csv_path, index=False)
    
    print("\n==========================================================================")
    print("  TOP FEATURE DRIVER SUMMARY ACROSS ALL 8 DRUG CATEGORIES")
    print("==========================================================================")
    top_per_drug = full_global_imp_df.groupby('drug_category').first().reset_index()
    print(top_per_drug[['drug_category', 'feature', 'feature_domain', 'mean_abs_shap']].to_string(index=False))
    
    return full_global_imp_df, full_sample_attr_df

if __name__ == '__main__':
    run_explainable_forecasting_suite()
