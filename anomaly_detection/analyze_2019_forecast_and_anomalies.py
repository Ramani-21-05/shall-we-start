import os, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from stage2_forecast_aware_detector import load_champion_forecasts, build_forecast_aware_features
from sklearn.ensemble import IsolationForest

DATA_DIR = r'c:\Users\ranje\sales forcasting\times_series\dataset'
OUTPUT_DIR = r'c:\Users\ranje\sales forcasting\anomaly_detection'
PLOT_DIR = os.path.join(OUTPUT_DIR, 'plots', '2019_analysis')
os.makedirs(PLOT_DIR, exist_ok=True)

DRUGS = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']

train_df = pd.read_csv(os.path.join(DATA_DIR, 'train_daily.csv'))
val_df   = pd.read_csv(os.path.join(DATA_DIR, 'val_daily.csv'))
test_df  = pd.read_csv(os.path.join(DATA_DIR, 'test_daily.csv'))

for df in [train_df, val_df, test_df]:
    df['date'] = pd.to_datetime(df['date'])

def analyze_2019_drug_anomalies(drug):
    """
    Runs 2019 Forecast-Aware Anomaly Analysis for a specific drug category:
    1. Loads Champion Model P50, P10, P90 predictions.
    2. Runs Stage 2 Forecast-Aware Isolation Forest.
    3. Identifies detected anomaly dates, residuals, and severity.
    4. Generates an annotated forecast & anomaly chart.
    """
    # 1. Load Champion Forecast Plan (P10, P50, P90)
    folder = os.path.join(r'c:\Users\ranje\sales forcasting\drug_models', f"{drug.lower()}_models")
    plan_csvs = glob.glob(os.path.join(folder, '*_supply_chain_plan.csv'))
    
    if not plan_csvs:
        raise FileNotFoundError(f"No supply chain plan CSV found for {drug}")
        
    plan_df = pd.read_csv(plan_csvs[0])
    plan_df['date'] = pd.to_datetime(plan_df['Date'])
    
    # Merge actual 2019 sales with plan
    df_2019 = test_df[['date', drug]].rename(columns={drug: 'actual_sales'}).copy()
    df_2019 = pd.merge(df_2019, plan_df[['date', 'Lean Lower Bound (P10)', 'Expected Demand Anchor (P50)', 'Upper Target Stock (P90)']], on='date', how='left')
    
    # 2. Fit Stage 2 Detector on historical baseline
    train_p50 = train_df[drug].shift(1).rolling(7).mean().fillna(train_df[drug].mean())
    val_p50   = val_df[drug].shift(1).rolling(7).mean().fillna(val_df[drug].mean())
    
    X_train = build_forecast_aware_features(train_df, drug, train_p50)
    X_val   = build_forecast_aware_features(val_df, drug, val_p50)
    
    clf = IsolationForest(n_estimators=150, contamination='auto', random_state=42, n_jobs=-1)
    clf.fit(X_train)
    
    val_scores = -clf.score_samples(X_val)
    threshold  = np.percentile(val_scores, 95)
    
    # 3. Predict Anomalies on 2019 Real Data
    X_2019 = build_forecast_aware_features(df_2019, 'actual_sales', df_2019['Expected Demand Anchor (P50)'])
    scores_2019 = -clf.score_samples(X_2019)
    
    df_2019['anomaly_score'] = scores_2019
    df_2019['is_anomaly']    = (scores_2019 >= threshold).astype(int)
    df_2019['residual']      = df_2019['actual_sales'] - df_2019['Expected Demand Anchor (P50)']
    df_2019['abs_residual']  = np.abs(df_2019['residual'])
    
    # Categorize Anomaly Severity & Type
    def classify_anomaly(row):
        if row['is_anomaly'] == 0:
            return 'Normal'
        if row['residual'] > 0:
            return 'Demand Surge Spike'
        else:
            return 'Unexpected Sales Drop'
            
    df_2019['anomaly_type'] = df_2019.apply(classify_anomaly, axis=1)
    
    anomalies = df_2019[df_2019['is_anomaly'] == 1].sort_values('abs_residual', ascending=False)
    
    # 4. Plot 2019 Forecast + Anomaly Overlay Chart
    plt.figure(figsize=(15, 6), dpi=300)
    
    # Actual Sales
    plt.plot(df_2019['date'], df_2019['actual_sales'], label='Actual 2019 Sales', color='#1f77b4', linewidth=1.5, alpha=0.85)
    
    # P50 Champion Forecast
    plt.plot(df_2019['date'], df_2019['Expected Demand Anchor (P50)'], label='Champion P50 Forecast', color='#2ca02c', linewidth=2.0, linestyle='--')
    
    # P10-P90 Probabilistic Band
    plt.fill_between(df_2019['date'], df_2019['Lean Lower Bound (P10)'], df_2019['Upper Target Stock (P90)'], color='#2ca02c', alpha=0.15, label='Probabilistic Range [P10, P90]')
    
    # Highlight Detected Anomalies
    anom_df = df_2019[df_2019['is_anomaly'] == 1]
    if len(anom_df) > 0:
        plt.scatter(anom_df['date'], anom_df['actual_sales'], color='red', s=70, zorder=5, label=f'Detected Anomalies ({len(anom_df)} days)', marker='o', edgecolors='black')
        
    plt.title(f'2019 Demand Forecast & Anomaly Detection Analysis — Drug Category: {drug}', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Date (2019 Test Holdout)', fontsize=12, fontweight='bold')
    plt.ylabel('Sales Volume (Packs/Day)', fontsize=12, fontweight='bold')
    plt.legend(loc='upper right', fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    
    chart_path = os.path.join(PLOT_DIR, f'2019_forecast_anomalies_{drug}.png')
    plt.savefig(chart_path, dpi=120, bbox_inches='tight')
    plt.close()
    
    return df_2019, anomalies

def run_all_2019_analysis():
    print("==========================================================================")
    print("  RUNNING REAL 2019 FORECAST & ANOMALY ANALYSIS ACROSS ALL 8 DRUGS")
    print("==========================================================================")
    
    all_anomalies = []
    summary_stats = []
    
    for drug in DRUGS:
        df_full, anom_df = analyze_2019_drug_anomalies(drug)
        anom_df['drug_category'] = drug
        all_anomalies.append(anom_df)
        
        n_anom = len(anom_df)
        avg_res = anom_df['abs_residual'].mean() if n_anom > 0 else 0.0
        max_res = anom_df['abs_residual'].max() if n_anom > 0 else 0.0
        
        summary_stats.append({
            'Drug Category': drug,
            'Total 2019 Days': len(df_full),
            'Detected Anomalies': n_anom,
            'Anomaly Rate (%)': round(n_anom / len(df_full) * 100, 2),
            'Avg Anomaly Deviation': round(avg_res, 2),
            'Max Anomaly Spike': round(max_res, 2)
        })
        
        print(f"[{drug}] Detected {n_anom} anomalies ({n_anom/len(df_full)*100:.2f}%) | Max Deviation: {max_res:.2f} packs/day")
        
    summary_df = pd.DataFrame(summary_stats)
    full_anom_df = pd.concat(all_anomalies, ignore_index=True)
    
    print("\n==========================================================================")
    print("  2019 ANOMALY DETECTION SUMMARY REPORT")
    print("==========================================================================")
    print(summary_df.to_string(index=False))
    
    sum_path  = os.path.join(OUTPUT_DIR, '2019_anomaly_detection_summary.csv')
    anom_path = os.path.join(OUTPUT_DIR, '2019_detected_anomalies_detail.csv')
    
    summary_df.to_csv(sum_path, index=False)
    full_anom_df.to_csv(anom_path, index=False)
    
    print(f"\nSummary saved to: {sum_path}")
    print(f"Detailed anomalies saved to: {anom_path}")
    print(f"Visualization plots saved to: {PLOT_DIR}\n")
    
    return summary_df, full_anom_df

if __name__ == '__main__':
    run_all_2019_analysis()
