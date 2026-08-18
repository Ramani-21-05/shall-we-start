import os
import numpy as np
import pandas as pd
import lightgbm as lgb
import optuna
import shap
import warnings
warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)

OUTPUT_DIR = r'c:\Users\ranje\sales forcasting\explainable_forecasting'
DRUG_MODELS_DIR = r'c:\Users\ranje\sales forcasting\drug_models'
DATA_DIR   = r'c:\Users\ranje\sales forcasting\times_series\dataset'
DRUGS      = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']

train_df = pd.read_csv(os.path.join(DATA_DIR, 'train_daily.csv'))
val_df   = pd.read_csv(os.path.join(DATA_DIR, 'val_daily.csv'))
test_df  = pd.read_csv(os.path.join(DATA_DIR, 'test_daily.csv'))

for df in [train_df, val_df, test_df]:
    df['date'] = pd.to_datetime(df['date'])

full_train_df = pd.concat([train_df, val_df]).sort_values('date').set_index('date')
test_df_idx   = test_df.set_index('date')

def export_per_drug_model_rankings():
    src_rankings = os.path.join(DRUG_MODELS_DIR, 'drug_model_selection_rankings.csv')
    if os.path.exists(src_rankings):
        df_rank = pd.read_csv(src_rankings)
        out_rank = os.path.join(OUTPUT_DIR, 'explainable_drug_model_rankings.csv')
        df_rank.to_csv(out_rank, index=False)
        return df_rank
    return None

def build_features(df_all, drug):
    feat = pd.DataFrame(index=df_all.index)
    series = df_all[drug]
    
    feat['lag_1']  = series.shift(1)
    feat['lag_2']  = series.shift(2)
    feat['lag_7']  = series.shift(7)
    feat['lag_14'] = series.shift(14)
    feat['lag_28'] = series.shift(28)
    
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

def optimize_lightgbm_optuna(drug, n_trials=10):
    combined_df = pd.concat([full_train_df, test_df_idx])
    feat_matrix = build_features(combined_df, drug)
    
    tr_series  = train_df.set_index('date')[drug]
    val_series = val_df.set_index('date')[drug]
    
    y_tr = np.log1p(tr_series.dropna())
    X_tr = feat_matrix.loc[y_tr.index].fillna(0)
    
    y_va = val_series.dropna()
    X_va = feat_matrix.loc[y_va.index].fillna(0)
    
    def objective(trial):
        params = {
            'num_leaves': trial.suggest_int('num_leaves', 15, 63),
            'max_depth': trial.suggest_int('max_depth', 3, 6),
            'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.05, log=True),
            'n_estimators': trial.suggest_int('n_estimators', 100, 500),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 1.0, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 1.0, log=True),
            'random_state': 42,
            'verbose': -1,
            'n_jobs': -1
        }
        
        model = lgb.LGBMRegressor(**params)
        model.fit(X_tr, y_tr)
        
        preds_log = model.predict(X_va)
        preds_units = np.expm1(preds_log)
        
        rmsle = np.sqrt(np.mean((np.log1p(np.maximum(preds_units, 0)) - np.log1p(np.maximum(y_va.values, 0)))**2))
        return rmsle

    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=n_trials)
    
    return study.best_params, study.best_value

def run_explainable_model_selection():
    print("==========================================================================")
    print("  EXPLAINABLE FORECASTING: DRUG-BY-DRUG MODEL SELECTION & PARAMETER TUNING")
    print("==========================================================================")
    
    df_rank = export_per_drug_model_rankings()
    if df_rank is not None:
        print("\n--- PER-DRUG CHAMPION MODEL SELECTION SUMMARY ---")
        champions = df_rank.groupby('drug').first().reset_index()
        print(champions[['drug', 'model_name', 'rmsle', 'mae']].to_string(index=False))
        
    optuna_results = []
    
    for drug in DRUGS:
        best_params, best_rmsle = optimize_lightgbm_optuna(drug, n_trials=10)
        print(f"\n[{drug}] Optuna Selected Params (Val RMSLE: {best_rmsle:.4f}):")
        print(f"       {best_params}")
        
        optuna_results.append({
            'drug': drug,
            'best_val_rmsle': round(best_rmsle, 4),
            'best_params': str(best_params)
        })
        
    opt_df = pd.DataFrame(optuna_results)
    out_path = os.path.join(OUTPUT_DIR, 'explainable_optuna_tuning_results.csv')
    opt_df.to_csv(out_path, index=False)
    print(f"\nSaved Optuna parameter tuning results to: {out_path}")
    return opt_df

if __name__ == '__main__':
    run_explainable_model_selection()
