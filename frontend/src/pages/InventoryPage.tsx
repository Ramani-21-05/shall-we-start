// src/pages/InventoryPage.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchInventoryOverview,
  fetchDrugInventory,
  fetchInventoryAlerts,
  fetchSundayReview,
  fetchTransactions,
  fetchBaselineHistory,
  recordSale,
  recordTransaction,
  updateBaselineStock,
  approveReplenishmentOrder,
  resetInventory,
  type DrugInventoryEvaluation,
} from '@/api/inventoryV2'
import { DRUGS } from '@/types'
import {
  Package,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  ShoppingCart,
  Calendar,
  Layers,
  ArrowRight,
  PlusCircle,
  RefreshCw,
  Clock,
  ShieldAlert,
  Info,
  Check,
  X,
  Edit3,
  Truck,
  Send,
  Sparkles,
} from 'lucide-react'

type TabType = 'overview' | 'detail' | 'sunday' | 'history'

const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; border: string; icon: any }> = {
  HEALTHY: {
    label: 'Healthy Stock',
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    border: 'border-emerald-500/30',
    icon: CheckCircle2,
  },
  WATCH: {
    label: '60% Watch',
    bg: 'bg-amber-500/10',
    text: 'text-amber-400',
    border: 'border-amber-500/30',
    icon: AlertTriangle,
  },
  REPLENISHMENT_RECOMMENDED: {
    label: '70% Reorder',
    bg: 'bg-orange-500/10',
    text: 'text-orange-400',
    border: 'border-orange-500/30',
    icon: TrendingUp,
  },
  STOCKOUT_RISK: {
    label: 'Stockout Risk',
    bg: 'bg-rose-500/10',
    text: 'text-rose-400',
    border: 'border-rose-500/30',
    icon: ShieldAlert,
  },
  EMERGENCY_REPLENISHMENT: {
    label: 'Emergency Reorder',
    bg: 'bg-purple-500/10',
    text: 'text-purple-400',
    border: 'border-purple-500/30',
    icon: ShieldAlert,
  },
  OUT_OF_STOCK: {
    label: 'Out of Stock',
    bg: 'bg-red-600/20',
    text: 'text-red-400',
    border: 'border-red-500/50',
    icon: AlertTriangle,
  },
}

export function InventoryPage() {
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [selectedDrug, setSelectedDrug] = useState<string>('N02BE')

  // Modals & Form States
  const [saleDrug, setSaleDrug] = useState('N02BE')
  const [saleQty, setSaleQty] = useState('')
  const [saleNotes, setSaleNotes] = useState('')

  const [txDrug, setTxDrug] = useState('N02BE')
  const [txType, setTxType] = useState('RESTOCK')
  const [txQty, setTxQty] = useState('')
  const [txNotes, setTxNotes] = useState('')

  const [editOrderModal, setEditOrderModal] = useState<DrugInventoryEvaluation | null>(null)
  const [editOrderQtyInput, setEditOrderQtyInput] = useState('')

  const [editBaselineModal, setEditBaselineModal] = useState<DrugInventoryEvaluation | null>(null)
  const [editBaselineInput, setEditBaselineInput] = useState('')
  const [editBaselineReason, setEditBaselineReason] = useState('')

  const [notification, setNotification] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)

  const queryClient = useQueryClient()

  // Queries
  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['inventory-overview'],
    queryFn: fetchInventoryOverview,
    refetchInterval: 10000,
  })

  const { data: drugDetail } = useQuery({
    queryKey: ['inventory-detail', selectedDrug],
    queryFn: () => fetchDrugInventory(selectedDrug),
    enabled: !!selectedDrug,
  })

  const { data: sundayReview } = useQuery({
    queryKey: ['sunday-review'],
    queryFn: fetchSundayReview,
  })

  const { data: transactions } = useQuery({
    queryKey: ['transactions', selectedDrug],
    queryFn: () => fetchTransactions(activeTab === 'detail' ? selectedDrug : undefined),
  })

  const { data: baselineHistory } = useQuery({
    queryKey: ['baseline-history', selectedDrug],
    queryFn: () => fetchBaselineHistory(activeTab === 'detail' ? selectedDrug : undefined),
  })

  const notify = (msg: string, type: 'success' | 'error' = 'success') => {
    setNotification({ msg, type })
    setTimeout(() => setNotification(null), 4000)
  }

  // Mutations
  const saleMutation = useMutation({
    mutationFn: () => recordSale(saleDrug, parseFloat(saleQty), 'pharmacist', saleNotes),
    onSuccess: (data) => {
      notify(`Sale recorded for ${saleDrug}! Stock updated to ${data.evaluation.current_stock}.`)
      setSaleQty('')
      setSaleNotes('')
      queryClient.invalidateQueries({ queryKey: ['inventory-overview'] })
      queryClient.invalidateQueries({ queryKey: ['inventory-detail'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
    onError: (err: any) => notify(err.message || 'Sale failed', 'error'),
  })

  const txMutation = useMutation({
    mutationFn: () => recordTransaction(txDrug, txType, parseFloat(txQty), 'pharmacist', txNotes),
    onSuccess: () => {
      notify(`Transaction ${txType} recorded successfully for ${txDrug}.`)
      setTxQty('')
      setTxNotes('')
      queryClient.invalidateQueries({ queryKey: ['inventory-overview'] })
      queryClient.invalidateQueries({ queryKey: ['inventory-detail'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
    onError: (err: any) => notify(err.message || 'Transaction failed', 'error'),
  })

  const approveOrderMutation = useMutation({
    mutationFn: ({ drugCode, qty, reason }: { drugCode: string; qty: number; reason?: string }) =>
      approveReplenishmentOrder(drugCode, qty, 'pharmacist', reason || 'Approved recommendation'),
    onSuccess: (data) => {
      notify(`Replenishment order for ${data.data.quantity} units sent to Vendor Dashboard!`)
      setEditOrderModal(null)
      queryClient.invalidateQueries({ queryKey: ['inventory-overview'] })
      queryClient.invalidateQueries({ queryKey: ['inventory-detail'] })
      queryClient.invalidateQueries({ queryKey: ['sunday-review'] })
    },
    onError: (err: any) => notify(err.message || 'Order approval failed', 'error'),
  })

  const updateBaselineMutation = useMutation({
    mutationFn: ({ drugCode, val, src, reason, status }: { drugCode: string; val: number; src?: string; reason?: string; status?: string }) =>
      updateBaselineStock(drugCode, val, src, reason, 'pharmacist', status),
    onSuccess: () => {
      notify('Baseline stock updated successfully!')
      setEditBaselineModal(null)
      queryClient.invalidateQueries({ queryKey: ['inventory-overview'] })
      queryClient.invalidateQueries({ queryKey: ['inventory-detail'] })
      queryClient.invalidateQueries({ queryKey: ['baseline-history'] })
    },
    onError: (err: any) => notify(err.message || 'Baseline update failed', 'error'),
  })

  const resetMutation = useMutation({
    mutationFn: resetInventory,
    onSuccess: () => {
      notify('Inventory database reset to clean default state!')
      queryClient.invalidateQueries({ queryKey: ['inventory-overview'] })
      queryClient.invalidateQueries({ queryKey: ['inventory-detail'] })
      queryClient.invalidateQueries({ queryKey: ['sunday-review'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['baseline-history'] })
    },
    onError: (err: any) => notify(err.message || 'Reset failed', 'error'),
  })

  // Actionable Alerts (Filter drugs needing attention)
  const alerts = (overview || []).filter((item) => item.status !== 'HEALTHY')

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto text-slate-100">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`fixed top-5 right-5 z-50 px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 border backdrop-blur-md transition-all ${
            notification.type === 'success'
              ? 'bg-emerald-950/90 border-emerald-500/50 text-emerald-200'
              : 'bg-rose-950/90 border-rose-500/50 text-rose-200'
          }`}
        >
          {notification.type === 'success' ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
          <span className="text-sm font-medium">{notification.msg}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-card p-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-md text-[10px] font-extrabold uppercase tracking-wider bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              Decision Engine Active
            </span>
            <span className="text-xs text-slate-400">• Forecast-Driven Stock Control</span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">Pharmacy Inventory Management</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Forecast recommends stock position; Pharmacy Member makes the final decision.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => {
              if (window.confirm('Reset all inventory stock levels, transactions, and orders back to fresh initial state?')) {
                resetMutation.mutate()
              }
            }}
            disabled={resetMutation.isPending}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-2 border border-white/10 transition-all"
          >
            <RefreshCw size={14} />
            Reset Data
          </button>

          {/* Quick Tabs */}
          <div className="flex items-center gap-2 bg-slate-900/60 p-1.5 rounded-xl border border-white/5">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
              activeTab === 'overview'
                ? 'bg-gradient-to-r from-indigo-500 to-indigo-600 text-white shadow-lg shadow-indigo-500/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <Package size={15} />
            Control Center
            {alerts.length > 0 && (
              <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-amber-500 text-slate-950 font-bold">
                {alerts.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('detail')}
            className={`px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
              activeTab === 'detail'
                ? 'bg-gradient-to-r from-indigo-500 to-indigo-600 text-white shadow-lg shadow-indigo-500/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <Sparkles size={15} />
            Drug Decision Deep Dive
          </button>

          <button
            onClick={() => setActiveTab('sunday')}
            className={`px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
              activeTab === 'sunday'
                ? 'bg-gradient-to-r from-indigo-500 to-indigo-600 text-white shadow-lg shadow-indigo-500/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <Calendar size={15} />
            Sunday Planning Board
          </button>

          <button
            onClick={() => setActiveTab('history')}
            className={`px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
              activeTab === 'history'
                ? 'bg-gradient-to-r from-indigo-500 to-indigo-600 text-white shadow-lg shadow-indigo-500/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <Clock size={15} />
            Audit History
          </button>
        </div>
        </div>
      </div>

      {/* TAB 1: CONTROL CENTER & LIVE ACTIONABLE ALERTS */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Actionable Alerts Header Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <AlertTriangle className="text-amber-400" size={18} />
                  Actionable Replenishment Alerts
                </h2>
                <p className="text-xs text-slate-400">
                  Alerts triggered by 60%/70% baseline consumption or forecast stockout predictions. Shows exact unit recommendations.
                </p>
              </div>
              <span className="text-xs text-slate-500 font-mono">
                {alerts.length} Active {alerts.length === 1 ? 'Alert' : 'Alerts'}
              </span>
            </div>

            {alerts.length === 0 ? (
              <div className="glass-card p-6 text-center text-slate-400 flex flex-col items-center gap-2">
                <CheckCircle2 size={32} className="text-emerald-400" />
                <p className="text-sm font-semibold text-white">All Stock Levels Healthy</p>
                <p className="text-xs text-slate-400">No drugs currently breach consumption thresholds or forecast risk buffers.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {alerts.map((alert) => {
                  const cfg = STATUS_CONFIG[alert.status] || STATUS_CONFIG.WATCH
                  const Icon = cfg.icon

                  return (
                    <div
                      key={alert.drug_code}
                      className={`glass-card p-5 border-l-4 ${cfg.border} relative overflow-hidden flex flex-col justify-between space-y-4`}
                    >
                      <div>
                        {/* Header Badge */}
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="font-extrabold text-base text-white">{alert.drug_code}</span>
                            <span className="text-xs text-slate-400">• {alert.drug_name}</span>
                          </div>
                          <div className={`px-2.5 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5 ${cfg.bg} ${cfg.text}`}>
                            <Icon size={12} />
                            {cfg.label}
                          </div>
                        </div>

                        <p className="text-xs text-slate-300 bg-slate-900/40 p-2.5 rounded-lg border border-white/5">
                          {alert.reason}
                        </p>

                        {/* Detailed Metrics Table inside Alert */}
                        <div className="grid grid-cols-4 gap-2 text-center mt-3 pt-3 border-t border-white/5">
                          <div className="bg-slate-900/60 p-2 rounded-lg">
                            <p className="text-[10px] text-slate-400 uppercase font-semibold">Current</p>
                            <p className="text-sm font-bold text-white">{alert.current_stock}</p>
                          </div>

                          <div className="bg-slate-900/60 p-2 rounded-lg">
                            <p className="text-[10px] text-slate-400 uppercase font-semibold">Baseline</p>
                            <p className="text-sm font-bold text-slate-300">{alert.baseline_stock}</p>
                          </div>

                          <div className="bg-slate-900/60 p-2 rounded-lg">
                            <p className="text-[10px] text-slate-400 uppercase font-semibold">Consumed %</p>
                            <p className={`text-sm font-bold ${alert.consumed_pct >= 70 ? 'text-amber-400' : 'text-amber-300'}`}>
                              {alert.consumed_pct}%
                            </p>
                          </div>

                          <div className="bg-slate-900/60 p-2 rounded-lg">
                            <p className="text-[10px] text-slate-400 uppercase font-semibold">Incoming</p>
                            <p className="text-sm font-bold text-indigo-400">{alert.incoming_stock}</p>
                          </div>
                        </div>

                        {/* Target Stock & Order Quantity Callout */}
                        <div className="mt-3 bg-gradient-to-r from-indigo-950/40 to-slate-900/60 p-3 rounded-xl border border-indigo-500/20 flex items-center justify-between">
                          <div>
                            <p className="text-[10px] text-indigo-300 uppercase font-semibold">Recommended Replenishment</p>
                            <p className="text-lg font-black text-white">
                              {alert.recommended_order_qty} <span className="text-xs font-normal text-slate-400">units</span>
                            </p>
                            <p className="text-[10px] text-slate-400">Target Stock: {alert.target_stock} (Safety: {alert.safety_stock})</p>
                          </div>

                          <div className="text-right">
                            <p className="text-[10px] text-slate-400 uppercase font-semibold">7-Day Forecast</p>
                            <p className="text-sm font-bold text-indigo-400">{alert.forecast_demand} units</p>
                          </div>
                        </div>
                      </div>

                      {/* Action Buttons: Approve, Edit, Reject */}
                      <div className="flex items-center gap-2 pt-2 border-t border-white/5">
                        <button
                          onClick={() => approveOrderMutation.mutate({ drugCode: alert.drug_code, qty: alert.recommended_order_qty })}
                          disabled={approveOrderMutation.isPending || alert.recommended_order_qty <= 0}
                          className="flex-1 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-all shadow-md"
                        >
                          <Check size={14} />
                          Approve ({alert.recommended_order_qty} units)
                        </button>

                        <button
                          onClick={() => {
                            setEditOrderModal(alert)
                            setEditOrderQtyInput(String(alert.recommended_order_qty))
                          }}
                          className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1 border border-white/10 transition-all"
                        >
                          <Edit3 size={14} />
                          Edit Qty
                        </button>

                        <button
                          onClick={() => notify(`Alert recommendation for ${alert.drug_code} dismissed by pharmacist.`)}
                          className="px-3 py-2 rounded-lg bg-rose-950/40 hover:bg-rose-900/50 text-rose-300 text-xs font-semibold flex items-center gap-1 border border-rose-500/20 transition-all"
                        >
                          <X size={14} />
                          Dismiss
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Quick POS & Stock Adjustment Actions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Record Sale Card */}
            <div className="glass-card p-5 space-y-4 border border-indigo-500/20">
              <div className="flex items-center gap-2">
                <ShoppingCart className="text-indigo-400" size={18} />
                <h3 className="text-sm font-bold text-white">Pharmacy Point of Sale (Record Sale)</h3>
              </div>
              <p className="text-xs text-slate-400">
                Recording a sale automatically updates live inventory stock and evaluates consumption thresholds.
              </p>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] uppercase font-bold text-slate-400">Drug</label>
                  <select
                    value={saleDrug}
                    onChange={(e) => setSaleDrug(e.target.value)}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {DRUGS.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-[10px] uppercase font-bold text-slate-400">Quantity Sold</label>
                  <input
                    type="number"
                    value={saleQty}
                    onChange={(e) => setSaleQty(e.target.value)}
                    placeholder="e.g. 25"
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-slate-400">Sale Notes / Customer</label>
                <input
                  type="text"
                  value={saleNotes}
                  onChange={(e) => setSaleNotes(e.target.value)}
                  placeholder="Optional notes..."
                  className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <button
                onClick={() => saleMutation.mutate()}
                disabled={saleMutation.isPending || !saleQty}
                className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-indigo-600/20"
              >
                <ShoppingCart size={14} />
                Record POS Sale Transaction
              </button>
            </div>

            {/* Inventory Adjustment Card */}
            <div className="glass-card p-5 space-y-4 border border-white/5">
              <div className="flex items-center gap-2">
                <Layers className="text-cyan-400" size={18} />
                <h3 className="text-sm font-bold text-white">Stock Adjustment & Audit Transaction</h3>
              </div>
              <p className="text-xs text-slate-400">
                Log non-sale movements (Restock, Return, Damage, Expiry, Manual Adjustment) with full audit logging.
              </p>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-[10px] uppercase font-bold text-slate-400">Drug</label>
                  <select
                    value={txDrug}
                    onChange={(e) => setTxDrug(e.target.value)}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {DRUGS.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-[10px] uppercase font-bold text-slate-400">Type</label>
                  <select
                    value={txType}
                    onChange={(e) => setTxType(e.target.value)}
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="RESTOCK">RESTOCK (+)</option>
                    <option value="RETURN">RETURN (+)</option>
                    <option value="DAMAGE">DAMAGE (-)</option>
                    <option value="EXPIRY">EXPIRY (-)</option>
                    <option value="ADJUSTMENT">ADJUSTMENT (=)</option>
                  </select>
                </div>

                <div>
                  <label className="text-[10px] uppercase font-bold text-slate-400">Quantity</label>
                  <input
                    type="number"
                    value={txQty}
                    onChange={(e) => setTxQty(e.target.value)}
                    placeholder="Qty"
                    className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-slate-400">Audit Reason / Notes</label>
                <input
                  type="text"
                  value={txNotes}
                  onChange={(e) => setTxNotes(e.target.value)}
                  placeholder="e.g. Expired batch discarded..."
                  className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <button
                onClick={() => txMutation.mutate()}
                disabled={txMutation.isPending || !txQty}
                className="w-full py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-white/10 disabled:opacity-50 text-white text-xs font-bold flex items-center justify-center gap-2 transition-all"
              >
                <PlusCircle size={14} />
                Log Stock Adjustment
              </button>
            </div>
          </div>

          {/* Full Inventory Status Matrix Table */}
          <div className="glass-card p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Package size={16} className="text-indigo-400" />
                Live Pharmaceutical Stock Decision Matrix (All 8 Drugs)
              </h3>
              <span className="text-xs text-slate-400">Auto-calculated using forecast & inventory position</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-white/10 text-slate-400 uppercase text-[10px] font-bold">
                    <th className="py-3 px-3">Drug</th>
                    <th className="py-3 px-3">Category</th>
                    <th className="py-3 px-3 text-right">Current Stock</th>
                    <th className="py-3 px-3 text-right">Baseline Stock</th>
                    <th className="py-3 px-3 text-center">Consumed %</th>
                    <th className="py-3 px-3 text-right">Incoming Stock</th>
                    <th className="py-3 px-3 text-right">7-Day Forecast</th>
                    <th className="py-3 px-3 text-right">Target Stock</th>
                    <th className="py-3 px-3 text-right font-bold text-indigo-300">Rec Order</th>
                    <th className="py-3 px-3 text-center">Status</th>
                    <th className="py-3 px-3 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {(overview || []).map((item) => {
                    const cfg = STATUS_CONFIG[item.status] || STATUS_CONFIG.HEALTHY
                    return (
                      <tr key={item.drug_code} className="hover:bg-white/5 transition-colors">
                        <td className="py-3 px-3 font-extrabold text-white">
                          <button
                            onClick={() => {
                              setSelectedDrug(item.drug_code)
                              setActiveTab('detail')
                            }}
                            className="hover:underline hover:text-indigo-400 text-left"
                          >
                            {item.drug_code}
                          </button>
                        </td>
                        <td className="py-3 px-3 text-slate-400 text-[11px]">{item.category}</td>
                        <td className="py-3 px-3 text-right font-bold text-white">{item.current_stock}</td>
                        <td className="py-3 px-3 text-right text-slate-300">{item.baseline_stock}</td>
                        <td className="py-3 px-3 text-center">
                          <span
                            className={`px-2 py-0.5 rounded-full font-bold text-[11px] ${
                              item.consumed_pct >= 70
                                ? 'bg-amber-500/20 text-amber-300'
                                : item.consumed_pct >= 60
                                ? 'bg-amber-500/10 text-amber-400'
                                : 'bg-slate-800 text-slate-300'
                            }`}
                          >
                            {item.consumed_pct}%
                          </span>
                        </td>
                        <td className="py-3 px-3 text-right text-indigo-400 font-semibold">{item.incoming_stock}</td>
                        <td className="py-3 px-3 text-right text-slate-300">{item.forecast_demand}</td>
                        <td className="py-3 px-3 text-right text-slate-300">{item.target_stock}</td>
                        <td className="py-3 px-3 text-right font-black text-indigo-300">{item.recommended_order_qty}</td>
                        <td className="py-3 px-3 text-center">
                          <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${cfg.bg} ${cfg.text}`}>
                            {cfg.label}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-center">
                          {item.recommended_order_qty > 0 ? (
                            <button
                              onClick={() => approveOrderMutation.mutate({ drugCode: item.drug_code, qty: item.recommended_order_qty })}
                              className="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[11px] transition-all flex items-center gap-1 mx-auto"
                            >
                              <Send size={11} /> Order
                            </button>
                          ) : (
                            <span className="text-[11px] text-slate-500">Sufficient</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: DRUG DECISION DEEP DIVE */}
      {activeTab === 'detail' && (
        <div className="space-y-6">
          {/* Selector Bar */}
          <div className="glass-card p-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <label className="text-xs font-bold text-slate-400 uppercase">Select Drug Category:</label>
              <div className="flex flex-wrap gap-1.5">
                {DRUGS.map((d) => (
                  <button
                    key={d}
                    onClick={() => setSelectedDrug(d)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                      selectedDrug === d
                        ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                        : 'bg-slate-900/60 text-slate-400 hover:bg-white/5 hover:text-slate-200'
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>

            {drugDetail && (
              <button
                onClick={() => {
                  setEditBaselineModal(drugDetail)
                  setEditBaselineInput(String(drugDetail.baseline_stock))
                  setEditBaselineReason('')
                }}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-white/10 text-slate-200 text-xs font-semibold flex items-center gap-1.5"
              >
                <Edit3 size={14} />
                Edit Baseline ({drugDetail.baseline_stock})
              </button>
            )}
          </div>

          {drugDetail && (
            <div className="space-y-6">
              {/* Forecast Suggestion Banner */}
              {drugDetail.baseline_recommendation && (
                <div className="glass-card p-5 border-l-4 border-indigo-500 bg-indigo-950/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <Sparkles size={20} className="text-indigo-400 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-bold text-white">ML Forecast Suggests Baseline Increase</h4>
                      <p className="text-xs text-slate-300 mt-0.5">
                        Forecast projects high sustained demand for {drugDetail.drug_code}. Suggests increasing baseline from{' '}
                        <span className="font-bold text-amber-300">{drugDetail.baseline_recommendation.current_baseline}</span> to{' '}
                        <span className="font-bold text-emerald-300">{drugDetail.baseline_recommendation.suggested_baseline}</span> units.
                      </p>
                      <p className="text-[11px] text-slate-400 italic mt-1">{drugDetail.baseline_recommendation.reason}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() =>
                        updateBaselineMutation.mutate({
                          drugCode: drugDetail.drug_code,
                          val: drugDetail.baseline_recommendation!.suggested_baseline,
                          src: 'FORECAST_RECOMMENDATION',
                          reason: 'Accepted ML model recommendation',
                          status: 'ACCEPTED',
                        })
                      }
                      className="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1"
                    >
                      <Check size={14} /> Accept ({drugDetail.baseline_recommendation.suggested_baseline})
                    </button>
                    <button
                      onClick={() => {
                        setEditBaselineModal(drugDetail)
                        setEditBaselineInput(String(drugDetail.baseline_recommendation!.suggested_baseline))
                      }}
                      className="px-3 py-2 rounded-lg bg-slate-800 text-slate-200 text-xs font-semibold"
                    >
                      Edit Custom
                    </button>
                    <button
                      onClick={() => notify('Forecast baseline suggestion rejected.')}
                      className="px-3 py-2 rounded-lg bg-rose-950/40 text-rose-300 text-xs font-semibold"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              )}

              {/* 4 Core Parameter Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="glass-card p-4 space-y-1">
                  <p className="text-[10px] font-extrabold uppercase text-slate-400">Current Stock</p>
                  <p className="text-2xl font-black text-white">{drugDetail.current_stock}</p>
                  <p className="text-[11px] text-slate-400">Consumed: {drugDetail.consumed_pct}% of baseline</p>
                </div>

                <div className="glass-card p-4 space-y-1">
                  <p className="text-[10px] font-extrabold uppercase text-slate-400">Baseline Stock</p>
                  <p className="text-2xl font-black text-slate-200">{drugDetail.baseline_stock}</p>
                  <p className="text-[11px] text-slate-400">Normal desired pharmacy level</p>
                </div>

                <div className="glass-card p-4 space-y-1">
                  <p className="text-[10px] font-extrabold uppercase text-slate-400">Incoming Stock</p>
                  <p className="text-2xl font-black text-indigo-400">{drugDetail.incoming_stock}</p>
                  <p className="text-[11px] text-slate-400">Orders in pipeline to vendor</p>
                </div>

                <div className="glass-card p-4 space-y-1">
                  <p className="text-[10px] font-extrabold uppercase text-slate-400">Safety & Lead Time</p>
                  <p className="text-2xl font-black text-cyan-300">
                    {drugDetail.safety_stock} <span className="text-xs font-normal text-slate-400">units</span>
                  </p>
                  <p className="text-[11px] text-slate-400">Supplier Lead Time: {drugDetail.lead_time_days} days</p>
                </div>
              </div>

              {/* Demand Forecast Projections & Decision Output */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Demand Projections */}
                <div className="glass-card p-5 space-y-4">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <TrendingUp size={16} className="text-indigo-400" />
                    Demand Forecast Projections
                  </h3>

                  <div className="space-y-3 text-xs">
                    <div className="bg-slate-900/60 p-3 rounded-lg flex items-center justify-between">
                      <span className="text-slate-400">Tomorrow Demand:</span>
                      <span className="font-bold text-white text-sm">{drugDetail.forecast_details?.tomorrow} units</span>
                    </div>

                    <div className="bg-slate-900/60 p-3 rounded-lg space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Next 7 Days Demand (P50):</span>
                        <span className="font-bold text-indigo-400 text-sm">{drugDetail.forecast_details?.next_7_days} units</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-white/5">
                        <span>Quantiles: P10 = {drugDetail.forecast_details?.p10_7_days}</span>
                        <span>P90 = {drugDetail.forecast_details?.p90_7_days}</span>
                      </div>
                    </div>

                    <div className="bg-slate-900/60 p-3 rounded-lg flex items-center justify-between">
                      <span className="text-slate-400">Next 14 Days Demand:</span>
                      <span className="font-bold text-slate-200 text-sm">{drugDetail.forecast_details?.next_14_days} units</span>
                    </div>
                  </div>
                </div>

                {/* Inventory Decision Engine Box */}
                <div className="glass-card p-5 space-y-4 md:col-span-2 border border-indigo-500/30">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <Sparkles size={16} className="text-indigo-400" />
                      Inventory Engine Calculation Breakdown
                    </h3>
                    <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-indigo-500/20 text-indigo-300">
                      Status: {drugDetail.status}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div className="bg-slate-900/60 p-3 rounded-xl">
                      <p className="text-[10px] text-slate-400 uppercase font-semibold">Inventory Position</p>
                      <p className="text-base font-bold text-white mt-1">
                        {drugDetail.current_stock} + {drugDetail.incoming_stock} = {drugDetail.inventory_position}
                      </p>
                      <p className="text-[10px] text-slate-500">Current + Incoming</p>
                    </div>

                    <div className="bg-slate-900/60 p-3 rounded-xl">
                      <p className="text-[10px] text-slate-400 uppercase font-semibold">Target Stock</p>
                      <p className="text-base font-bold text-cyan-300 mt-1">{drugDetail.target_stock}</p>
                      <p className="text-[10px] text-slate-500">Baseline + Forecast + Safety</p>
                    </div>

                    <div className="bg-gradient-to-br from-indigo-950 to-slate-900 p-3 rounded-xl border border-indigo-500/30">
                      <p className="text-[10px] text-indigo-300 uppercase font-bold">Recommended Order</p>
                      <p className="text-xl font-black text-white mt-0.5">{drugDetail.recommended_order_qty} units</p>
                      <p className="text-[10px] text-slate-400">Target - Position</p>
                    </div>
                  </div>

                  <div className="bg-slate-900/60 p-3 rounded-xl border border-white/5 text-xs text-slate-300 space-y-1">
                    <p className="font-semibold text-white">Decision Analysis:</p>
                    <p>{drugDetail.reason}</p>
                  </div>

                  <div className="flex items-center gap-3 pt-2">
                    <button
                      onClick={() => approveOrderMutation.mutate({ drugCode: drugDetail.drug_code, qty: drugDetail.recommended_order_qty })}
                      disabled={approveOrderMutation.isPending || drugDetail.recommended_order_qty <= 0}
                      className="flex-1 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20"
                    >
                      <Send size={14} />
                      Approve & Send Order ({drugDetail.recommended_order_qty} units)
                    </button>

                    <button
                      onClick={() => {
                        setEditOrderModal(drugDetail)
                        setEditOrderQtyInput(String(drugDetail.recommended_order_qty))
                      }}
                      className="px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs border border-white/10"
                    >
                      Edit Quantity
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: SUNDAY REPLENISHMENT PLANNING BOARD */}
      {activeTab === 'sunday' && (
        <div className="space-y-6">
          <div className="glass-card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Calendar className="text-indigo-400" size={20} />
                  Sunday Replenishment Cycle Board
                </h2>
                <p className="text-xs text-slate-400">
                  Full weekly review of ALL 8 drugs. Evaluates consumption %, forecast risk, and calculates exact reorder quantities.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-white/10 text-slate-400 uppercase text-[10px] font-bold">
                    <th className="py-3 px-3">Drug</th>
                    <th className="py-3 px-3 text-right">Baseline</th>
                    <th className="py-3 px-3 text-right">Current</th>
                    <th className="py-3 px-3 text-right">Incoming</th>
                    <th className="py-3 px-3 text-center">Consumed %</th>
                    <th className="py-3 px-3 text-center">Forecast Risk</th>
                    <th className="py-3 px-3 text-center">Recommendation</th>
                    <th className="py-3 px-3 text-right font-bold text-indigo-300">Recommended Qty</th>
                    <th className="py-3 px-3 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {(sundayReview || []).map((item) => (
                    <tr key={item.drug_code} className="hover:bg-white/5">
                      <td className="py-3.5 px-3 font-extrabold text-white">
                        {item.drug_code} <span className="font-normal text-slate-400 text-[11px] block">{item.drug_name}</span>
                      </td>
                      <td className="py-3.5 px-3 text-right text-slate-300">{item.baseline_stock}</td>
                      <td className="py-3.5 px-3 text-right font-bold text-white">{item.current_stock}</td>
                      <td className="py-3.5 px-3 text-right text-indigo-400 font-semibold">{item.incoming_stock}</td>
                      <td className="py-3.5 px-3 text-center">
                        <span className="font-bold text-slate-200">{item.consumed_pct}%</span>
                      </td>
                      <td className="py-3.5 px-3 text-center">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            item.forecast_risk === 'CRITICAL'
                              ? 'bg-purple-500/20 text-purple-300'
                              : item.forecast_risk === 'HIGH'
                              ? 'bg-rose-500/20 text-rose-300'
                              : item.forecast_risk === 'MEDIUM'
                              ? 'bg-amber-500/20 text-amber-300'
                              : 'bg-emerald-500/20 text-emerald-300'
                          }`}
                        >
                          {item.forecast_risk}
                        </span>
                      </td>
                      <td className="py-3.5 px-3 text-center font-bold text-white">{item.recommendation_action}</td>
                      <td className="py-3.5 px-3 text-right font-black text-indigo-300 text-sm">
                        {item.recommended_order_qty} units
                      </td>
                      <td className="py-3.5 px-3 text-center">
                        {item.recommended_order_qty > 0 ? (
                          <button
                            onClick={() => approveOrderMutation.mutate({ drugCode: item.drug_code, qty: item.recommended_order_qty, reason: 'Sunday Replenishment Cycle' })}
                            className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs"
                          >
                            Approve Order
                          </button>
                        ) : (
                          <span className="text-[11px] text-slate-500">Maintain</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: AUDIT HISTORY */}
      {activeTab === 'history' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Inventory Transactions Audit Table */}
            <div className="glass-card p-5 space-y-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Clock size={16} className="text-indigo-400" />
                Inventory Audit Transactions Log
              </h3>

              <div className="overflow-x-auto max-h-[500px]">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-400 text-[10px] uppercase font-bold sticky top-0 bg-slate-950">
                      <th className="py-2 px-2">Drug</th>
                      <th className="py-2 px-2">Type</th>
                      <th className="py-2 px-2 text-right">Qty</th>
                      <th className="py-2 px-2 text-right">Before/After</th>
                      <th className="py-2 px-2">User</th>
                      <th className="py-2 px-2">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {(transactions || []).map((t) => (
                      <tr key={t.id} className="hover:bg-white/5 text-[11px]">
                        <td className="py-2 px-2 font-bold text-white">{t.drug_code}</td>
                        <td className="py-2 px-2">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                              t.transaction_type === 'SALE'
                                ? 'bg-amber-500/20 text-amber-300'
                                : t.transaction_type === 'RESTOCK'
                                ? 'bg-emerald-500/20 text-emerald-300'
                                : 'bg-slate-800 text-slate-300'
                            }`}
                          >
                            {t.transaction_type}
                          </span>
                        </td>
                        <td className="py-2 px-2 text-right font-bold text-white">{t.quantity}</td>
                        <td className="py-2 px-2 text-right text-slate-400">
                          {t.stock_before} → {t.stock_after}
                        </td>
                        <td className="py-2 px-2 text-slate-400">{t.user_id}</td>
                        <td className="py-2 px-2 text-slate-500 text-[10px]">{t.timestamp?.substring(0, 16)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Baseline Audit History */}
            <div className="glass-card p-5 space-y-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Edit3 size={16} className="text-cyan-400" />
                Baseline Modification Audit History
              </h3>

              <div className="overflow-x-auto max-h-[500px]">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-400 text-[10px] uppercase font-bold sticky top-0 bg-slate-950">
                      <th className="py-2 px-2">Drug</th>
                      <th className="py-2 px-2 text-right">Old → New</th>
                      <th className="py-2 px-2">Source</th>
                      <th className="py-2 px-2">Reason</th>
                      <th className="py-2 px-2">User</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {(baselineHistory || []).map((bh) => (
                      <tr key={bh.id} className="hover:bg-white/5 text-[11px]">
                        <td className="py-2 px-2 font-bold text-white">{bh.drug_code}</td>
                        <td className="py-2 px-2 text-right font-bold text-indigo-300">
                          {bh.old_baseline} → {bh.new_baseline}
                        </td>
                        <td className="py-2 px-2 text-slate-400 text-[10px]">{bh.source}</td>
                        <td className="py-2 px-2 text-slate-300 text-[10px]">{bh.reason}</td>
                        <td className="py-2 px-2 text-slate-400">{bh.changed_by}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: EDIT ORDER QUANTITY */}
      {editOrderModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 space-y-4 border border-indigo-500/30">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">Edit Replenishment Quantity</h3>
              <button onClick={() => setEditOrderModal(null)} className="text-slate-400 hover:text-white">
                <X size={18} />
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Drug: <span className="font-bold text-white">{editOrderModal.drug_code}</span> — Baseline: {editOrderModal.baseline_stock}, Current: {editOrderModal.current_stock}
            </p>

            <div>
              <label className="text-[10px] uppercase font-bold text-slate-400">Approved Replenishment Quantity (Units)</label>
              <input
                type="number"
                value={editOrderQtyInput}
                onChange={(e) => setEditOrderQtyInput(e.target.value)}
                className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm font-bold text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center gap-2 pt-2">
              <button
                onClick={() =>
                  approveOrderMutation.mutate({
                    drugCode: editOrderModal.drug_code,
                    qty: parseFloat(editOrderQtyInput),
                    reason: 'Pharmacist edited quantity',
                  })
                }
                className="flex-1 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs"
              >
                Confirm & Dispatch to Vendor
              </button>
              <button onClick={() => setEditOrderModal(null)} className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: EDIT BASELINE STOCK */}
      {editBaselineModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 space-y-4 border border-white/10">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">Edit Baseline Stock ({editBaselineModal.drug_code})</h3>
              <button onClick={() => setEditBaselineModal(null)} className="text-slate-400 hover:text-white">
                <X size={18} />
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Current Baseline: <span className="font-bold text-white">{editBaselineModal.baseline_stock}</span> units.
            </p>

            <div>
              <label className="text-[10px] uppercase font-bold text-slate-400">New Baseline Stock Level</label>
              <input
                type="number"
                value={editBaselineInput}
                onChange={(e) => setEditBaselineInput(e.target.value)}
                className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm font-bold text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-[10px] uppercase font-bold text-slate-400">Reason for Change</label>
              <input
                type="text"
                value={editBaselineReason}
                onChange={(e) => setEditBaselineReason(e.target.value)}
                placeholder="e.g. Seasonal demand increase..."
                className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center gap-2 pt-2">
              <button
                onClick={() =>
                  updateBaselineMutation.mutate({
                    drugCode: editBaselineModal.drug_code,
                    val: parseFloat(editBaselineInput),
                    src: 'MANUAL',
                    reason: editBaselineReason || 'Pharmacist manual update',
                  })
                }
                className="flex-1 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs"
              >
                Save Baseline
              </button>
              <button onClick={() => setEditBaselineModal(null)} className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
