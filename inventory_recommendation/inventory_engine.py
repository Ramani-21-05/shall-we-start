import os, sys, glob
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

OUTPUT_DIR = r'c:\Users\ranje\sales forcasting\inventory_recommendation'
DRUG_MODELS_DIR = r'c:\Users\ranje\sales forcasting\drug_models'
os.makedirs(OUTPUT_DIR, exist_ok=True)

DRUGS = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']
LEAD_TIME_DAYS = 3   # Fixed 3-day resupply lead time

def generate_inventory_recommendations(drug, lead_time_days=LEAD_TIME_DAYS):
    """
    3-Day Sequential Carryover Inventory Engine with Chart-Aligned KPIs:
      1. Stock_t = starting stock today (includes arriving shipments).
      2. Stockout Risk = 1 IF Stock_t < Reorder Point (Purple line below Orange line in chart).
      3. Overstock Risk = 1 IF Stock_t > Target Stock Level (Purple line above Green line in chart).
      4. Forward Threshold Lookahead: If Stock - ROP_{t+1} - ROP_{t+2} < 0 → trigger reorder.
      5. Unsold balance (Stock_t - ActualSales_t) carries forward to Day t+1.
    """
    drug_lower = drug.lower()
    plan_path = os.path.join(DRUG_MODELS_DIR, f'{drug_lower}_models', f'{drug_lower}_hybrid_supply_chain_plan.csv')
    
    if not os.path.exists(plan_path):
        raise FileNotFoundError(f"Could not locate supply chain plan at {plan_path}")
        
    df = pd.read_csv(plan_path)
    df.columns = [c.strip() for c in df.columns]
    
    date_col = next((c for c in df.columns if 'date' in c.lower()), 'Date')
    act_col  = next((c for c in df.columns if 'actual' in c.lower()), 'Actual Sales')
    p10_col  = next((c for c in df.columns if 'p10' in c.lower() and 'lean' in c.lower()), 'Lean Lower Bound (P10)')
    p50_col  = next((c for c in df.columns if 'p50' in c.lower() and 'expected' in c.lower()), 'Expected Demand Anchor (P50)')
    p90_col  = next((c for c in df.columns if 'p90' in c.lower() and 'upper' in c.lower()), 'Upper Target Stock (P90)')
    
    dates        = pd.to_datetime(df[date_col])
    actual_sales = df[act_col].values
    p10_demand   = df[p10_col].values
    p50_demand   = df[p50_col].values
    p90_demand   = df[p90_col].values

    n_days = len(df)

    # 1. Supply Chain Safety Parameters
    safety_stock     = np.round((p90_demand - p50_demand) * np.sqrt(lead_time_days), 2)
    reorder_point    = np.round((p50_demand * lead_time_days) + safety_stock, 2)
    target_stock_lvl = np.round((p90_demand * lead_time_days) + safety_stock, 2)

    # 2. Sequential Dynamic Inventory Simulation
    stock_on_hand       = np.zeros(n_days)
    pending_orders      = np.zeros(n_days + lead_time_days + 10)
    recommendations     = []
    recommended_orders  = np.zeros(n_days)
    stockout_risks      = np.zeros(n_days, dtype=int)
    overstock_risks     = np.zeros(n_days, dtype=int)
    order_triggers      = []

    # Day 1 Initial Stock = Target Stock Level
    current_stock = target_stock_lvl[0]

    for t in range(n_days):
        # Step A: Add incoming shipment arriving today
        current_stock += pending_orders[t]

        # Step B: Record today's starting stock (Purple Line)
        stock_on_hand[t] = np.round(current_stock, 2)

        rop_t = reorder_point[t]
        tsl_t = target_stock_lvl[t]
        actual_sold = actual_sales[t]

        # Chart-Aligned Risk Definitions:
        # Stockout Risk = Purple line dips below Orange line (Inventory < Reorder Point)
        if current_stock < rop_t:
            stockout_risks[t] = 1
        else:
            stockout_risks[t] = 0

        # Overstock Risk = Purple line rises above Green line (Inventory > Target Stock Level)
        if current_stock > tsl_t:
            overstock_risks[t] = 1
        else:
            overstock_risks[t] = 0

        # Step C: Sequential 3-Day Forward Subtract Lookahead Check
        rop_next1 = reorder_point[t+1] if (t+1) < n_days else rop_t
        rop_next2 = reorder_point[t+2] if (t+2) < n_days else rop_t

        remainder_1 = current_stock - rop_next1
        remainder_2 = remainder_1 - rop_next2

        reactive_trigger  = current_stock < rop_t
        proactive_trigger = remainder_2 < 0

        # In-transit orders already placed and arriving within 3 days
        pipeline_in_transit = np.sum(pending_orders[t+1 : t+1+lead_time_days])
        effective_inventory = current_stock + pipeline_in_transit

        if reactive_trigger or proactive_trigger:
            if effective_inventory < tsl_t:
                order_qty = np.maximum(0, np.ceil(tsl_t - effective_inventory))
                recommended_orders[t] = order_qty

                # Schedule delivery arrival in 3 days
                arrival_day = t + lead_time_days
                pending_orders[arrival_day] += order_qty

                rec = 'INCREASE REPLENISHMENT'
                trigger_label = 'REACTIVE (Below ROP)' if reactive_trigger else 'PROACTIVE (Forward Shortfall)'
            else:
                rec = 'MAINTAIN REPLENISHMENT'
                trigger_label = 'PIPELINE IN-TRANSIT SUFFICIENT'
        elif current_stock > tsl_t:
            rec = 'REDUCE REPLENISHMENT'
            trigger_label = 'OVERSTOCKED'
        else:
            rec = 'MAINTAIN REPLENISHMENT'
            trigger_label = 'HEALTHY ZONE'

        recommendations.append(rec)
        order_triggers.append(trigger_label)

        # Step D: Deduct today's sales from stock (use actual_sales if available, else fallback to p50 forecast)
        actual_sold = actual_sales[t] if (pd.notna(actual_sales[t]) and not np.isnan(float(actual_sales[t]))) else p50_demand[t]
        current_stock = np.maximum(0, current_stock - actual_sold)

    rec_df = pd.DataFrame({
        'date': dates,
        'drug_category': drug,
        'actual_sales': actual_sales,
        'p10_demand': p10_demand,
        'p50_demand': p50_demand,
        'p90_demand': p90_demand,
        'uncertainty_band': np.round(p90_demand - p10_demand, 2),
        'safety_stock': safety_stock,
        'reorder_point': reorder_point,
        'target_stock_lvl': target_stock_lvl,
        'simulated_inventory': stock_on_hand,
        'stockout_risk': stockout_risks,
        'overstock_risk': overstock_risks,
        'replenishment_recommendation': recommendations,
        'recommended_order_qty': recommended_orders,
        'order_trigger': order_triggers
    })
    
    return rec_df

def run_inventory_engine_suite():
    print("==========================================================================")
    print("  CHART-ALIGNED 3-DAY SEQUENTIAL INVENTORY ENGINE")
    print("==========================================================================")
    
    all_recs = []
    
    for drug in DRUGS:
        rdf = generate_inventory_recommendations(drug)
        all_recs.append(rdf)
        
        n = len(rdf)
        so_pct = (rdf['stockout_risk'].sum() / n) * 100
        os_pct = (rdf['overstock_risk'].sum() / n) * 100
        svc_pct = ((rdf['simulated_inventory'] >= rdf['actual_sales']).sum() / n) * 100
        
        print(f"[{drug}] Stockout Risk (Purple < Orange): {so_pct:4.1f}% | Overstock Risk (Purple > Green): {os_pct:4.1f}% | Service Level: {svc_pct:5.1f}%")

    full_recs_df = pd.concat(all_recs, ignore_index=True)
    out_csv = os.path.join(OUTPUT_DIR, 'inventory_recommendations_all_drugs.csv')
    full_recs_df.to_csv(out_csv, index=False)
    
    print(f"\nSaved inventory recommendations summary to: {out_csv}\n")
    return full_recs_df

if __name__ == '__main__':
    run_inventory_engine_suite()
