import os, sys, glob, json
import numpy as np
import pandas as pd
import lightgbm as lgb
import shap
import urllib.request
import urllib.parse
import warnings
warnings.filterwarnings('ignore')

# Automatically load GROQ_API_KEY from .env file at root workspace
def load_env_file():
    base_dir = r'c:\Users\ranje\sales forcasting'
    env_path = os.path.join(base_dir, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    k, v = k.strip(), v.strip()
                    if v and v != 'your_groq_api_key_here':
                        os.environ[k] = v

load_env_file()

DATA_DIR = r'c:\Users\ranje\sales forcasting\times_series\dataset'
OUTPUT_DIR = r'c:\Users\ranje\sales forcasting\explainable_forecasting'

train_df = pd.read_csv(os.path.join(DATA_DIR, 'train_daily.csv'))
val_df   = pd.read_csv(os.path.join(DATA_DIR, 'val_daily.csv'))
test_df  = pd.read_csv(os.path.join(DATA_DIR, 'test_daily.csv'))

for df in [train_df, val_df, test_df]:
    df['date'] = pd.to_datetime(df['date'])

full_train_df = pd.concat([train_df, val_df]).sort_values('date').set_index('date')
test_df_idx   = test_df.set_index('date')

def build_features(df_all, drug):
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

def extract_structured_facts(drug='R03', sample_date=None):
    """
    Step 1 & Step 2: Runs Champion Model + SHAP Explainer and extracts Structured Facts.
    """
    combined_df = pd.concat([full_train_df, test_df_idx])
    feat_matrix = build_features(combined_df, drug)
    
    y_tr = np.log1p(full_train_df[drug].dropna())
    X_tr = feat_matrix.loc[y_tr.index].fillna(0)
    
    y_ts = test_df_idx[drug].dropna()
    X_ts = feat_matrix.loc[y_ts.index].fillna(0)
    
    # Train Model
    model = lgb.LGBMRegressor(num_leaves=31, max_depth=4, learning_rate=0.03, n_estimators=300, random_state=42, verbose=-1, n_jobs=-1)
    model.fit(X_tr, y_tr)
    
    # SHAP Explainer
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(X_ts)
    base_val  = float(explainer.expected_value)
    
    # Select Date Index
    if sample_date is not None and pd.to_datetime(sample_date) in X_ts.index:
        idx = X_ts.index.get_loc(pd.to_datetime(sample_date))
    else:
        # Default to peak demand day in 2019 test set
        idx = int(np.argmax(y_ts.values))
        
    date_str = X_ts.index[idx].strftime('%Y-%m-%d')
    pred_log = model.predict(X_ts.iloc[[idx]])[0]
    pred_units = int(round(np.expm1(pred_log)))
    base_units = int(round(np.expm1(base_val)))
    
    position = "ABOVE BASELINE" if pred_units >= base_units else "BELOW BASELINE"
    
    # Map features to clean domain descriptions
    domain_map = {
        'rolling_mean_28': f"Recent {drug} demand",
        'rolling_mean_7': f"7-day average {drug} demand",
        'rolling_mean_14': f"14-day average {drug} demand",
        'lag_1': f"Previous-day {drug} demand",
        'lag_2': f"2-day lag {drug} demand",
        'lag_7': f"Same-day-last-week demand",
        'lag_14': f"14-day historical lag demand",
        'sin_dayofyear': f"Annual seasonal pattern",
        'cos_dayofyear': f"Annual seasonal pattern",
        'dayofweek': f"Day-of-week demand pattern",
        'sin_dayofweek': f"Day-of-week demand pattern",
        'cos_dayofweek': f"Day-of-week demand pattern",
        'is_weekend': f"Weekend trading pattern"
    }
    
    # Extract feature attributions
    shaps_for_day = shap_vals[idx]
    sorted_feat_indices = np.argsort(np.abs(shaps_for_day))[::-1]
    
    contributing_factors = []
    seen_domains = set()
    
    for f_idx in sorted_feat_indices:
        f_name = X_ts.columns[f_idx]
        val = shaps_for_day[f_idx]
        dom_desc = domain_map.get(f_name, f_name)
        
        if dom_desc not in seen_domains and abs(val) > 0.001:
            direction = "-> Increased prediction" if val > 0 else "-> Decreased prediction"
            contributing_factors.append({
                'factor_name': dom_desc,
                'direction': direction,
                'shap_value': round(val, 4)
            })
            seen_domains.add(dom_desc)
            if len(contributing_factors) >= 5:
                break

    facts = {
        'date': date_str,
        'drug_category': drug,
        'predicted_sales': pred_units,
        'shap_baseline': base_units,
        'prediction_position': position,
        'contributing_factors': contributing_factors
    }
    
    return facts

def call_groq_llm_api(facts, groq_api_key):
    """
    Step 4 (LLM Inference): Calls Groq API using llama-3.3-70b-versatile.
    """
    prompt = f"""
You are an expert pharmaceutical supply chain analytics assistant.
Based on the following structured SHAP facts for drug {facts['drug_category']}, write a concise, executive-level 2-3 sentence overall explanation paragraph describing why predicted demand is {facts['prediction_position']}.

Structured Facts:
- Drug Category: {facts['drug_category']}
- Predicted Demand: {facts['predicted_sales']} units
- SHAP Baseline Demand: {facts['shap_baseline']} units
- Position: {facts['prediction_position']}
- Key Factors:
"""
    for f in facts['contributing_factors']:
        prompt += f"  * {f['factor_name']} {f['direction']}\n"
        
    prompt += "\nWrite ONLY the final overall explanation paragraph. Do not include markdown headers or extra conversational intro."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 250
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"[Groq API Warning] {e}. Falling back to rule-based synthesis.")
        return generate_fallback_narrative(facts)

def generate_fallback_narrative(facts):
    """
    Step 4 Fallback Synthesizer when no Groq API Key is supplied.
    """
    drug = facts['drug_category']
    pred = facts['predicted_sales']
    base = facts['shap_baseline']
    pos  = facts['prediction_position'].lower()
    
    pos_factors = [f['factor_name'] for f in facts['contributing_factors'] if 'Increased' in f['direction']]
    neg_factors = [f['factor_name'] for f in facts['contributing_factors'] if 'Decreased' in f['direction']]
    
    pos_str = ", ".join(pos_factors[:2]) if pos_factors else "historical baseline trends"
    neg_str = f", while {neg_factors[0].lower()} partially reduced the forecast" if neg_factors else ""
    
    narrative = (
        f"The model predicts {pred} units of {drug} demand, which is {pos} its SHAP baseline of {base} units. "
        f"The forecast is primarily supported by {pos_str.lower()}{neg_str}. "
        f"This provides a data-driven foundation for risk-aware inventory replenishment."
    )
    return narrative

def generate_human_explanation(drug='R03', sample_date=None, groq_api_key=None):
    """
    Complete Pipeline: Forecast -> SHAP -> Structured Facts -> LLM -> Human Explanation
    """
    load_env_file()
    if groq_api_key is None:
        groq_api_key = os.environ.get('GROQ_API_KEY')
        
    facts = extract_structured_facts(drug, sample_date)
    
    if groq_api_key:
        overall_narrative = call_groq_llm_api(facts, groq_api_key)
    else:
        overall_narrative = generate_fallback_narrative(facts)
        
    # Format the exact output template requested by the user
    output_lines = []
    output_lines.append("====================================================")
    output_lines.append(f"Drug Category : {facts['drug_category']}")
    output_lines.append("")
    output_lines.append(f"Predicted Sales : {facts['predicted_sales']} units")
    output_lines.append(f"SHAP Baseline   : {facts['shap_baseline']} units")
    output_lines.append("")
    output_lines.append(f"Prediction Position : {facts['prediction_position']}")
    output_lines.append("====================================================")
    output_lines.append("")
    output_lines.append("Major Contributing Factors:")
    output_lines.append("")
    
    for i, factor in enumerate(facts['contributing_factors'], 1):
        output_lines.append(f"{i}. {factor['factor_name']}")
        output_lines.append(f"   {factor['direction']}")
        output_lines.append("")
        
    output_lines.append("")
    output_lines.append("Overall Explanation:")
    output_lines.append("")
    output_lines.append(overall_narrative)
    
    full_report = "\n".join(output_lines)
    return full_report, facts

if __name__ == '__main__':
    print("=== EXPLAINABLE PIPELINE DEMO: FORECAST -> SHAP -> FACTS -> GROQ LLM -> HUMAN EXPLANATION ===")
    api_key = os.environ.get('GROQ_API_KEY')
    
    report, _ = generate_human_explanation(drug='R03', sample_date='2019-01-15', groq_api_key=api_key)
    print(report)
