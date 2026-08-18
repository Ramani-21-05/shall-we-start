import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from stage1_standalone_detector import run_stage1_standalone_detection
from stage2_forecast_aware_detector import run_stage2_forecast_aware_detection

OUTPUT_DIR = r'c:\Users\ranje\sales forcasting\anomaly_detection'
PLOT_DIR = os.path.join(OUTPUT_DIR, 'plots')
os.makedirs(PLOT_DIR, exist_ok=True)

DRUGS = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']

def run_head_to_head_experiment():
    print("==========================================================================")
    print("  RUNNING HEAD-TO-HEAD ANOMALY DETECTION EXPERIMENT ACROSS ALL 8 DRUGS")
    print("  STAGE 1: Standalone Isolation Forest (Raw Sales + Lags)")
    print("  STAGE 2: Forecast-Aware Isolation Forest (Sales + Champion P50 + Residuals)")
    print("==========================================================================")
    
    all_results = []
    
    for drug in DRUGS:
        res1, _, _ = run_stage1_standalone_detection(drug)
        res2, _, _ = run_stage2_forecast_aware_detection(drug)
        
        all_results.append(res1)
        all_results.append(res2)
        
        f1_diff  = res2['F1-Score'] - res1['F1-Score']
        auc_diff = res2['ROC-AUC'] - res1['ROC-AUC']
        
        if f1_diff > 0.01:
            verdict = "STAGE 2 WIN (Forecast-Aware Outperformed)"
        elif f1_diff < -0.01:
            verdict = "STAGE 1 WIN (Standalone Outperformed)"
        else:
            verdict = "TIE / EQUAL PERFORMANCE"
            
        print(f"[{drug}] Stage 1 F1: {res1['F1-Score']:.4f} (AUC: {res1['ROC-AUC']:.4f}) | Stage 2 F1: {res2['F1-Score']:.4f} (AUC: {res2['ROC-AUC']:.4f}) -> {verdict}")

    res_df = pd.DataFrame(all_results)
    
    # Pivot for head-to-head table
    pivot_f1 = res_df.pivot(index='Drug Category', columns='Stage', values='F1-Score')
    pivot_auc = res_df.pivot(index='Drug Category', columns='Stage', values='ROC-AUC')
    pivot_prec = res_df.pivot(index='Drug Category', columns='Stage', values='Precision')
    pivot_rec = res_df.pivot(index='Drug Category', columns='Stage', values='Recall')
    
    comp_df = pd.DataFrame({
        'Stage 1 Standalone F1': pivot_f1['Stage 1 (Standalone)'],
        'Stage 2 Forecast-Aware F1': pivot_f1['Stage 2 (Forecast-Aware)'],
        'F1 Delta (Stage 2 - Stage 1)': pivot_f1['Stage 2 (Forecast-Aware)'] - pivot_f1['Stage 1 (Standalone)'],
        'Stage 1 Standalone AUC': pivot_auc['Stage 1 (Standalone)'],
        'Stage 2 Forecast-Aware AUC': pivot_auc['Stage 2 (Forecast-Aware)'],
        'AUC Delta (Stage 2 - Stage 1)': pivot_auc['Stage 2 (Forecast-Aware)'] - pivot_auc['Stage 1 (Standalone)'],
        'Stage 2 Precision': pivot_prec['Stage 2 (Forecast-Aware)'],
        'Stage 2 Recall': pivot_rec['Stage 2 (Forecast-Aware)']
    }).reset_index()
    
    comp_df['Experiment Verdict'] = np.where(
        comp_df['F1 Delta (Stage 2 - Stage 1)'] > 0.01,
        'STAGE 2 FORECAST-AWARE WIN',
        np.where(comp_df['F1 Delta (Stage 2 - Stage 1)'] < -0.01, 'STAGE 1 STANDALONE WIN', 'TIE')
    )
    
    print("\n==========================================================================")
    print("  EXPERIMENT SUMMARY REPORT: STAGE 1 VS STAGE 2 ANOMALY DETECTION")
    print("==========================================================================")
    print(comp_df.to_string(index=False))
    
    out_path = os.path.join(OUTPUT_DIR, 'anomaly_experiment_summary.csv')
    comp_df.to_csv(out_path, index=False)
    print(f"\nSaved experiment summary to: {out_path}")
    
    # 5. Plot F1-Score & ROC-AUC Comparison Chart
    plt.figure(figsize=(14, 6), dpi=300)
    
    x = np.arange(len(DRUGS))
    width = 0.35
    
    plt.subplot(1, 2, 1)
    plt.bar(x - width/2, comp_df['Stage 1 Standalone F1'], width, label='Stage 1: Standalone', color='#1f77b4')
    plt.bar(x + width/2, comp_df['Stage 2 Forecast-Aware F1'], width, label='Stage 2: Forecast-Aware', color='#2ca02c')
    plt.xlabel('Drug Category', fontsize=11, fontweight='bold')
    plt.ylabel('F1-Score (Higher is Better)', fontsize=11, fontweight='bold')
    plt.title('F1-Score Comparison: Standalone vs Forecast-Aware', fontsize=12, fontweight='bold')
    plt.xticks(x, DRUGS, fontweight='bold')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    
    plt.subplot(1, 2, 2)
    plt.bar(x - width/2, comp_df['Stage 1 Standalone AUC'], width, label='Stage 1: Standalone', color='#1f77b4')
    plt.bar(x + width/2, comp_df['Stage 2 Forecast-Aware AUC'], width, label='Stage 2: Forecast-Aware', color='#2ca02c')
    plt.xlabel('Drug Category', fontsize=11, fontweight='bold')
    plt.ylabel('ROC-AUC (Higher is Better)', fontsize=11, fontweight='bold')
    plt.title('ROC-AUC Comparison: Standalone vs Forecast-Aware', fontsize=12, fontweight='bold')
    plt.xticks(x, DRUGS, fontweight='bold')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    chart_path = os.path.join(PLOT_DIR, 'stage1_vs_stage2_anomaly_comparison.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved comparison chart to: {chart_path}\n")
    
    return comp_df

if __name__ == '__main__':
    run_head_to_head_experiment()
