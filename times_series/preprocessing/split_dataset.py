import os
import json
import pandas as pd
import numpy as np

def split_and_export():
    dataset_dir = 'dataset'
    os.makedirs(dataset_dir, exist_ok=True)
    
    input_path = os.path.join(dataset_dir, 'saleshourly_preprocessed.csv')
    if not os.path.exists(input_path):
        input_path = os.path.join('dataset', 'saleshourly_preprocessed.csv')
        
    print(f"Loading preprocessed dataset from: {input_path}")
    df = pd.read_csv(input_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    drug_cols = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']
    
    # ----------------------------------------------------
    # 1. HOURLY SPLITS
    # ----------------------------------------------------
    train_hourly = df[df['Year'].isin([2014, 2015, 2016, 2017])].copy()
    val_hourly = df[df['Year'] == 2018].copy()
    test_hourly = df[df['Year'] == 2019].copy()
    
    # Export Hourly CSVs
    train_hourly_path = os.path.join(dataset_dir, 'train_hourly.csv')
    val_hourly_path = os.path.join(dataset_dir, 'val_hourly.csv')
    test_hourly_path = os.path.join(dataset_dir, 'test_hourly.csv')
    
    train_hourly.to_csv(train_hourly_path, index=False)
    val_hourly.to_csv(val_hourly_path, index=False)
    test_hourly.to_csv(test_hourly_path, index=False)
    
    # Also save standard train.csv, val.csv, test.csv
    train_hourly.to_csv(os.path.join(dataset_dir, 'train.csv'), index=False)
    val_hourly.to_csv(os.path.join(dataset_dir, 'val.csv'), index=False)
    test_hourly.to_csv(os.path.join(dataset_dir, 'test.csv'), index=False)
    
    # ----------------------------------------------------
    # 2. DAILY AGGREGATED SPLITS
    # ----------------------------------------------------
    df_daily = df.copy()
    df_daily['date'] = df_daily['datetime'].dt.date
    daily_group = df_daily.groupby('date')[drug_cols].sum().reset_index()
    daily_group['date'] = pd.to_datetime(daily_group['date'])
    daily_group['Year'] = daily_group['date'].dt.year
    daily_group['Month'] = daily_group['date'].dt.month
    daily_group['Day'] = daily_group['date'].dt.day
    daily_group['Weekday Name'] = daily_group['date'].dt.day_name()
    daily_group['Day_of_Week'] = daily_group['date'].dt.dayofweek
    daily_group['Day_of_Year'] = daily_group['date'].dt.dayofyear
    
    train_daily = daily_group[daily_group['Year'].isin([2014, 2015, 2016, 2017])].copy()
    val_daily = daily_group[daily_group['Year'] == 2018].copy()
    test_daily = daily_group[daily_group['Year'] == 2019].copy()
    
    train_daily_path = os.path.join(dataset_dir, 'train_daily.csv')
    val_daily_path = os.path.join(dataset_dir, 'val_daily.csv')
    test_daily_path = os.path.join(dataset_dir, 'test_daily.csv')
    
    train_daily.to_csv(train_daily_path, index=False)
    val_daily.to_csv(val_daily_path, index=False)
    test_daily.to_csv(test_daily_path, index=False)
    
    # ----------------------------------------------------
    # 3. METADATA SUMMARY JSON
    # ----------------------------------------------------
    summary = {
        "dataset_name": "Pharmaceutical Sales Forecasting (Hourly & Daily)",
        "split_strategy": "Temporal Chronological Split",
        "hourly_splits": {
            "train": {
                "years": "2014-2017",
                "rows": len(train_hourly),
                "start_time": str(train_hourly['datetime'].min()),
                "end_time": str(train_hourly['datetime'].max()),
                "file": "train_hourly.csv"
            },
            "validation": {
                "years": "2018",
                "rows": len(val_hourly),
                "start_time": str(val_hourly['datetime'].min()),
                "end_time": str(val_hourly['datetime'].max()),
                "file": "val_hourly.csv"
            },
            "test": {
                "years": "2019",
                "rows": len(test_hourly),
                "start_time": str(test_hourly['datetime'].min()),
                "end_time": str(test_hourly['datetime'].max()),
                "file": "test_hourly.csv"
            }
        },
        "daily_splits": {
            "train": {
                "years": "2014-2017",
                "days": len(train_daily),
                "start_date": str(train_daily['date'].min()),
                "end_date": str(train_daily['date'].max()),
                "file": "train_daily.csv"
            },
            "validation": {
                "years": "2018",
                "days": len(val_daily),
                "start_date": str(val_daily['date'].min()),
                "end_date": str(val_daily['date'].max()),
                "file": "val_daily.csv"
            },
            "test": {
                "years": "2019",
                "days": len(test_daily),
                "start_date": str(test_daily['date'].min()),
                "end_date": str(test_daily['date'].max()),
                "file": "test_daily.csv"
            }
        }
    }
    
    json_path = os.path.join(dataset_dir, 'dataset_splits_summary.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=4)
        
    print("\n--- DATASET SPLIT & EXPORT COMPLETED SUCCESSFULLY ---")
    print(f"Hourly Train (2014-2017): {len(train_hourly):,} rows ({train_hourly['datetime'].min()} to {train_hourly['datetime'].max()})")
    print(f"Hourly Val   (2018):      {len(val_hourly):,} rows ({val_hourly['datetime'].min()} to {val_hourly['datetime'].max()})")
    print(f"Hourly Test  (2019):      {len(test_hourly):,} rows ({test_hourly['datetime'].min()} to {test_hourly['datetime'].max()})")
    print(f"\nDaily Train (2014-2017):  {len(train_daily):,} days")
    print(f"Daily Val   (2018):       {len(val_daily):,} days")
    print(f"Daily Test  (2019):       {len(test_daily):,} days")

if __name__ == '__main__':
    split_and_export()
