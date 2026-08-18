import os
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.metrics import f1_score, roc_auc_score, precision_score, recall_score
import warnings
warnings.filterwarnings('ignore')

from synthetic_anomaly_generator import generate_synthetic_anomalies

OUTPUT_DIR = r'c:\Users\ranje\sales forcasting\anomaly_detection'
DRUGS = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']

def get_drug_data(synthetic_df, drug):
    df_drug = synthetic_df[synthetic_df['drug_category'] == drug].copy().reset_index(drop=True)
    
    sales = df_drug['synthetic_sales'].values
    y_true = df_drug['is_anomaly'].values
    
    lag_1 = pd.Series(sales).shift(1).bfill().fillna(0).values
    lag_7 = pd.Series(sales).shift(7).bfill().fillna(0).values
    rm7   = pd.Series(sales).shift(1).rolling(7, min_periods=1).mean().bfill().fillna(0).values
    
    X = np.column_stack([sales, lag_1, lag_7, rm7])
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return X, y_true

def tune_iqr_rule(X, y_true):
    best_f1 = -1
    best_res = None
    sales = X[:, 0]
    
    q25, q75 = np.percentile(sales, [25, 75])
    iqr = q75 - q25
    
    for mult in [1.5, 2.0, 2.5, 3.0]:
        upper = q75 + mult * iqr
        lower = q25 - mult * iqr
        pred = ((sales > upper) | (sales < lower)).astype(int)
        
        f1 = f1_score(y_true, pred, zero_division=0)
        auc = roc_auc_score(y_true, (sales - np.median(sales))**2)
        prec = precision_score(y_true, pred, zero_division=0)
        rec = recall_score(y_true, pred, zero_division=0)
        
        if f1 > best_f1:
            best_f1 = f1
            best_res = {
                'model': 'IQR Rule',
                'best_params': str({'multiplier': mult}),
                'F1': round(f1, 4),
                'ROC-AUC': round(auc, 4),
                'Precision': round(prec, 4),
                'Recall': round(rec, 4)
            }
    return best_res

def tune_zscore_rule(X, y_true):
    best_f1 = -1
    best_res = None
    sales = X[:, 0]
    mean, std = np.mean(sales), np.std(sales) + 1e-5
    z_scores = np.abs((sales - mean) / std)
    
    for thresh in [2.0, 2.5, 3.0, 3.5]:
        pred = (z_scores > thresh).astype(int)
        
        f1 = f1_score(y_true, pred, zero_division=0)
        auc = roc_auc_score(y_true, z_scores)
        prec = precision_score(y_true, pred, zero_division=0)
        rec = recall_score(y_true, pred, zero_division=0)
        
        if f1 > best_f1:
            best_f1 = f1
            best_res = {
                'model': 'Z-Score Rule',
                'best_params': str({'threshold': thresh}),
                'F1': round(f1, 4),
                'ROC-AUC': round(auc, 4),
                'Precision': round(prec, 4),
                'Recall': round(rec, 4)
            }
    return best_res

def tune_isolation_forest(X, y_true):
    best_f1 = -1
    best_res = None
    
    for n_est in [50, 100, 200]:
        for cont in [0.05, 0.10]:
            clf = IsolationForest(n_estimators=n_est, contamination=cont, random_state=42)
            preds_raw = clf.fit_predict(X)
            pred = np.where(preds_raw == -1, 1, 0)
            scores = -clf.decision_function(X)
            
            f1 = f1_score(y_true, pred, zero_division=0)
            auc = roc_auc_score(y_true, scores)
            prec = precision_score(y_true, pred, zero_division=0)
            rec = recall_score(y_true, pred, zero_division=0)
            
            if f1 > best_f1:
                best_f1 = f1
                best_res = {
                    'model': 'Isolation Forest',
                    'best_params': str({'n_estimators': n_est, 'contamination': cont}),
                    'F1': round(f1, 4),
                    'ROC-AUC': round(auc, 4),
                    'Precision': round(prec, 4),
                    'Recall': round(rec, 4)
                }
    return best_res

def tune_lof(X, y_true):
    best_f1 = -1
    best_res = None
    
    for k in [5, 10, 20, 30]:
        for cont in [0.05, 0.10]:
            clf = LocalOutlierFactor(n_neighbors=k, contamination=cont, novelty=False)
            preds_raw = clf.fit_predict(X)
            pred = np.where(preds_raw == -1, 1, 0)
            scores = -clf.negative_outlier_factor_
            
            f1 = f1_score(y_true, pred, zero_division=0)
            auc = roc_auc_score(y_true, scores)
            prec = precision_score(y_true, pred, zero_division=0)
            rec = recall_score(y_true, pred, zero_division=0)
            
            if f1 > best_f1:
                best_f1 = f1
                best_res = {
                    'model': 'Local Outlier Factor',
                    'best_params': str({'n_neighbors': k, 'contamination': cont}),
                    'F1': round(f1, 4),
                    'ROC-AUC': round(auc, 4),
                    'Precision': round(prec, 4),
                    'Recall': round(rec, 4)
                }
    return best_res

def tune_ocsvm(X, y_true):
    best_f1 = -1
    best_res = None
    
    for nu in [0.05, 0.10, 0.15]:
        for kernel in ['rbf']:
            clf = OneClassSVM(nu=nu, kernel=kernel, gamma='auto')
            preds_raw = clf.fit_predict(X)
            pred = np.where(preds_raw == -1, 1, 0)
            scores = -clf.decision_function(X)
            
            f1 = f1_score(y_true, pred, zero_division=0)
            auc = roc_auc_score(y_true, scores)
            prec = precision_score(y_true, pred, zero_division=0)
            rec = recall_score(y_true, pred, zero_division=0)
            
            if f1 > best_f1:
                best_f1 = f1
                best_res = {
                    'model': 'One-Class SVM',
                    'best_params': str({'nu': nu, 'kernel': kernel, 'gamma': 'auto'}),
                    'F1': round(f1, 4),
                    'ROC-AUC': round(auc, 4),
                    'Precision': round(prec, 4),
                    'Recall': round(rec, 4)
                }
    return best_res

def run_anomaly_model_selection():
    print("==========================================================================")
    print("  RUNNING ANOMALY MODEL SELECTION & HYPERPARAMETER TUNING SUITE")
    print("  Evaluating 5 Model Architectures: IQR Rule, Z-Score, Isolation Forest, LOF, OCSVM")
    print("==========================================================================")
    
    syn_file = os.path.join(OUTPUT_DIR, 'data', 'synthetic_2019_labeled_anomalies.csv')
    if os.path.exists(syn_file):
        synthetic_df = pd.read_csv(syn_file)
    else:
        synthetic_df = generate_synthetic_anomalies()
        
    all_rankings = []
    
    for drug in DRUGS:
        X, y_true = get_drug_data(synthetic_df, drug)
        
        m_iqr     = tune_iqr_rule(X, y_true)
        m_z       = tune_zscore_rule(X, y_true)
        m_iforest = tune_isolation_forest(X, y_true)
        m_lof     = tune_lof(X, y_true)
        m_ocsvm   = tune_ocsvm(X, y_true)
        
        drug_models = [m_iqr, m_z, m_iforest, m_ocsvm, m_lof]
        drug_models.sort(key=lambda x: x['F1'], reverse=True)
        
        for rank, m in enumerate(drug_models, 1):
            m['drug'] = drug
            m['rank'] = rank
            all_rankings.append(m)
            
        champion = drug_models[0]
        print(f"[{drug}] Champion Detector: {champion['model']} (F1: {champion['F1']:.4f}, AUC: {champion['ROC-AUC']:.4f}) | Params: {champion['best_params']}")
        
    rankings_df = pd.DataFrame(all_rankings)
    out_csv = os.path.join(OUTPUT_DIR, 'anomaly_model_selection_rankings.csv')
    rankings_df.to_csv(out_csv, index=False)
    
    print("\nSaved anomaly model selection rankings to:", out_csv)
    return rankings_df

if __name__ == '__main__':
    run_anomaly_model_selection()
