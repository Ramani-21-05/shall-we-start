import os
import numpy as np
import pandas as pd

OUTPUT_DIR = r'c:\Users\ranje\sales forcasting\anomaly_detection'
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, 'data'), exist_ok=True)

DATA_DIR = r'c:\Users\ranje\sales forcasting\times_series\dataset'
DRUGS = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']

def generate_synthetic_anomalies(anomaly_rate=0.06, random_seed=42):
    """
    Creates a synthetic labeled copy of the 2019 test set for anomaly evaluation.
    Injects 3 realistic anomaly types:
    1. Sudden Demand Spikes (+300% to +500% sales surge)
    2. Supply Stockout Drops (Demand dropped to 0 on peak sales days)
    3. High-Variance Outliers (Extreme unusual volatility)
    """
    np.random.seed(random_seed)
    
    test_df = pd.read_csv(os.path.join(DATA_DIR, 'test_daily.csv'))
    test_df['date'] = pd.to_datetime(test_df['date'])
    
    synthetic_records = []
    
    for drug in DRUGS:
        df_drug = test_df[['date', drug]].copy()
        df_drug.rename(columns={drug: 'raw_sales'}, inplace=True)
        df_drug['drug_category'] = drug
        df_drug['is_anomaly'] = 0
        df_drug['anomaly_type'] = 'Normal'
        df_drug['synthetic_sales'] = df_drug['raw_sales']
        
        n_samples = len(df_drug)
        n_anomalies = int(n_samples * anomaly_rate)
        
        # Candidate indices (exclude early edge dates)
        possible_indices = np.arange(14, n_samples - 5)
        chosen_indices = np.random.choice(possible_indices, size=n_anomalies, replace=False)
        
        for idx in chosen_indices:
            orig_val = df_drug.loc[idx, 'raw_sales']
            mean_val = df_drug['raw_sales'].mean()
            std_val  = df_drug['raw_sales'].std()
            
            anomaly_kind = np.random.choice(['Spike', 'Stockout_Drop', 'Variance_Outlier'], p=[0.4, 0.35, 0.25])
            
            if anomaly_kind == 'Spike':
                # +3.5 to +6 standard deviations spike
                surge = max(5.0, mean_val + np.random.uniform(3.5, 6.0) * max(std_val, 1.0))
                df_drug.loc[idx, 'synthetic_sales'] = round(orig_val + surge, 2)
                df_drug.loc[idx, 'anomaly_type'] = 'Demand_Spike'
                
            elif anomaly_kind == 'Stockout_Drop':
                # Sudden drop to 0 on a non-zero day
                if orig_val > 0:
                    df_drug.loc[idx, 'synthetic_sales'] = 0.0
                    df_drug.loc[idx, 'anomaly_type'] = 'Stockout_Drop'
                else:
                    # If already 0, make it a massive spike
                    df_drug.loc[idx, 'synthetic_sales'] = round(mean_val + 4.0 * max(std_val, 1.0), 2)
                    df_drug.loc[idx, 'anomaly_type'] = 'Demand_Spike'
                    
            elif anomaly_kind == 'Variance_Outlier':
                # Extreme outlier deviation
                factor = np.random.choice([0.1, 4.5])
                df_drug.loc[idx, 'synthetic_sales'] = round(orig_val * factor + np.random.uniform(2.0, 5.0), 2)
                df_drug.loc[idx, 'anomaly_type'] = 'Variance_Outlier'
                
            df_drug.loc[idx, 'is_anomaly'] = 1
            
        synthetic_records.append(df_drug)
        
    full_synthetic_df = pd.concat(synthetic_records, ignore_index=True)
    
    out_path = os.path.join(OUTPUT_DIR, 'data', 'synthetic_2019_labeled_anomalies.csv')
    full_synthetic_df.to_csv(out_path, index=False)
    
    print(f"=== SYNTHETIC ANOMALY GENERATION COMPLETE ===")
    print(f"Total synthetic test records: {len(full_synthetic_df)}")
    print(f"Total injected anomalies: {full_synthetic_df['is_anomaly'].sum()} ({full_synthetic_df['is_anomaly'].mean()*100:.2f}%)")
    print(full_synthetic_df['anomaly_type'].value_counts())
    print(f"Saved to: {out_path}\n")
    
    return full_synthetic_df

if __name__ == '__main__':
    generate_synthetic_anomalies()
