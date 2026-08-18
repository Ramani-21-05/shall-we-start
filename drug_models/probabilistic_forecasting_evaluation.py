import os, glob
import pandas as pd
import numpy as np

# Directory setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DRUG_FOLDERS = ['m01ab_models', 'm01ae_models', 'n02ba_models', 'n02be_models', 
                'n05b_models', 'n05c_models', 'r03_models', 'r06_models']

CHAMPION_NAMES = {
    "M01AB": "LightGBM + SHAP",
    "M01AE": "Meta Prophet",
    "N02BA": "LightGBM + SHAP",
    "N02BE": "LightGBM + SHAP",
    "N05B":  "LightGBM + SHAP",
    "N05C":  "ARIMA",
    "R03":   "XGBoost Quantile",
    "R06":   "LightGBM + SHAP"
}

def evaluate_probabilistic_forecasting(base_dir=BASE_DIR, folders=DRUG_FOLDERS):
    """
    Evaluates Probabilistic Forecasting Metrics across all 8 Drug Categories:
    1. PICP (Prediction Interval Coverage Probability): % of actual sales inside [P10, P90]
    2. MPIW (Mean Prediction Interval Width): Average width (P90 - P10) in physical pack units
    3. P90 Service Level Coverage: % of days actual sales <= P90 (Stockout Protection Target >= 95%)
    """
    results = []

    for folder_name in folders:
        folder_path = os.path.join(base_dir, folder_name)
        csv_files = glob.glob(os.path.join(folder_path, '*_supply_chain_plan.csv'))
        
        if not csv_files:
            print(f"Warning: No supply chain plan CSV found in {folder_path}")
            continue
            
        csv_path = csv_files[0]
        df = pd.read_csv(csv_path)
        drug_code = folder_name.split('_')[0].upper()
        
        df_2019 = df[df['Date'].str.startswith('2019')].dropna(subset=['Actual Sales'])
        y_true = df_2019['Actual Sales'].values
        p10    = df_2019['Lean Lower Bound (P10)'].values
        p90    = df_2019['Upper Target Stock (P90)'].values
        
        # 1. PICP (Prediction Interval Coverage Probability) [% within [P10, P90]]
        picp = np.mean((y_true >= p10) & (y_true <= p90)) * 100
        
        # 2. P90 Upper Service Level Coverage [% y <= P90]
        p90_coverage = np.mean(y_true <= p90) * 100
        
        # 3. MPIW (Mean Prediction Interval Width) [P90 - P10]
        mpiw = np.mean(p90 - p10)
        
        results.append({
            'Drug Category': drug_code,
            'Best Champion Model': CHAMPION_NAMES.get(drug_code, "LightGBM + SHAP"),
            'PICP (%) [P10-P90 Coverage]': round(picp, 2),
            'P90 Service Level (%)': round(p90_coverage, 2),
            'MPIW (Pack Units)': round(mpiw, 2),
            'Target PICP Interval': '80% Band [P10, P90]'
        })

    eval_df = pd.DataFrame(results)
    
    # Portfolio Average Row
    avg_row = {
        'Drug Category': 'PORTFOLIO AVG',
        'Best Champion Model': 'Optimal Champion Pipeline',
        'PICP (%) [P10-P90 Coverage]': round(eval_df['PICP (%) [P10-P90 Coverage]'].mean(), 2),
        'P90 Service Level (%)': round(eval_df['P90 Service Level (%)'].mean(), 2),
        'MPIW (Pack Units)': round(eval_df['MPIW (Pack Units)'].mean(), 2),
        'Target PICP Interval': '80% Nominal Target'
    }
    
    eval_df_with_avg = pd.concat([eval_df, pd.DataFrame([avg_row])], ignore_index=True)
    
    # Save CSV evaluation inside drug_models directory
    output_csv = os.path.join(base_dir, 'probabilistic_forecasting_eval.csv')
    eval_df_with_avg.to_csv(output_csv, index=False)
    
    print("\n==========================================================================")
    print("  PROBABILISTIC FORECASTING EVALUATION REPORT (PICP & MPIW)")
    print("==========================================================================")
    print(eval_df_with_avg.to_string(index=False))
    print(f"\nSaved evaluation summary report to: {output_csv}\n")
    
    return eval_df_with_avg

if __name__ == '__main__':
    evaluate_probabilistic_forecasting()
