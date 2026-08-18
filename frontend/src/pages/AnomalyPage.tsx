// src/pages/AnomalyPage.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchAnomalies } from '@/api/anomaly'
import { DRUGS } from '@/types'
import { AlertTriangle } from 'lucide-react'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'

const SEV_BADGE: Record<string, string> = {
  HIGH: 'badge-danger',
  MEDIUM: 'badge-warning',
  LOW: 'badge-info',
}

export function AnomalyPage() {
  const [drug, setDrug] = useState('M01AB')

  const { data, isLoading } = useQuery({
    queryKey: ['anomalies', drug],
    queryFn: () => fetchAnomalies(drug),
  })

  const anomalies = data?.filter(d => d.is_anomaly) ?? []
  const highSev = anomalies.filter(d => d.severity === 'HIGH').length
  const medSev = anomalies.filter(d => d.severity === 'MEDIUM').length

  const chartData = data?.map((d, i) => ({
    x: i,
    y: d.residual,
    is_anomaly: d.is_anomaly,
    date: d.anomaly_date,
    severity: d.severity,
    type: d.anomaly_type,
  })) ?? []

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold gradient-text flex items-center gap-2">
            <AlertTriangle size={22} /> Anomaly Detection
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            2019 data only · Stage 2: Forecast-Aware detection · Model NOT trained on 2019
          </p>
        </div>
        <select value={drug} onChange={e => setDrug(e.target.value)}
          className="glass-card-sm px-4 py-2 text-sm text-white bg-transparent cursor-pointer">
          {DRUGS.map(d => <option key={d} value={d} className="bg-slate-900">{d}</option>)}
        </select>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="glass-card p-4 text-center border border-red-500/20">
          <p className="text-2xl font-bold text-red-400">{highSev}</p>
          <p className="text-xs text-slate-400 mt-1">HIGH severity</p>
        </div>
        <div className="glass-card p-4 text-center border border-amber-500/20">
          <p className="text-2xl font-bold text-amber-400">{medSev}</p>
          <p className="text-xs text-slate-400 mt-1">MEDIUM severity</p>
        </div>
        <div className="glass-card p-4 text-center border border-indigo-500/20">
          <p className="text-2xl font-bold text-indigo-300">{anomalies.length}</p>
          <p className="text-xs text-slate-400 mt-1">Total anomalies</p>
        </div>
      </div>

      {isLoading ? <Spinner /> : (
        <>
          <div className="glass-card p-6">
            <p className="text-xs text-slate-400 mb-4">
              Residual scatter — <span className="text-red-400">●</span> Anomaly &nbsp;
              <span className="text-slate-500">●</span> Normal
            </p>
            <ResponsiveContainer width="100%" height={280}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="x" type="number" hide />
                <YAxis dataKey="y" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} label={{ value: 'Residual', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: 'hsl(245 40% 12%)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '0.5rem', color: '#e2e8f0', fontSize: 12 }}
                  formatter={(v, k, props) => [(props as any)?.payload?.date, (props as any)?.payload?.type]}
                  labelFormatter={() => ''}
                />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 4" />
                <Scatter
                  data={chartData.filter(d => !d.is_anomaly)}
                  fill="rgba(100,116,139,0.4)"
                  r={2}
                />
                <Scatter
                  data={chartData.filter(d => d.is_anomaly)}
                  fill="#ef4444"
                  r={4}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>

          {anomalies.length > 0 && (
            <div className="glass-card overflow-hidden">
              <div className="px-5 py-3 border-b border-white/10 text-xs text-slate-400 uppercase tracking-wider font-semibold">
                Detected Anomalies
              </div>
              <div className="max-h-64 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0">
                    <tr className="border-b border-white/10 text-xs text-slate-400 uppercase tracking-wider bg-slate-900/80 backdrop-blur-sm">
                      <th className="px-5 py-2.5 text-left">Date</th>
                      <th className="px-5 py-2.5 text-right">Actual</th>
                      <th className="px-5 py-2.5 text-right">Expected</th>
                      <th className="px-5 py-2.5 text-right">Residual</th>
                      <th className="px-5 py-2.5 text-center">Severity</th>
                      <th className="px-5 py-2.5 text-left">Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    {anomalies.slice(0, 30).map((a, i) => (
                      <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                        <td className="px-5 py-2.5 font-mono text-xs text-slate-300">{a.anomaly_date}</td>
                        <td className="px-5 py-2.5 text-right font-mono text-xs text-white">{a.actual_demand?.toFixed(1)}</td>
                        <td className="px-5 py-2.5 text-right font-mono text-xs text-indigo-300">{a.expected_demand?.toFixed(1)}</td>
                        <td className={`px-5 py-2.5 text-right font-mono text-xs ${a.residual > 0 ? 'text-red-400' : 'text-cyan-400'}`}>
                          {a.residual > 0 ? '+' : ''}{a.residual?.toFixed(2)}
                        </td>
                        <td className="px-5 py-2.5 text-center">
                          <span className={`badge ${SEV_BADGE[a.severity] ?? 'badge-info'}`}>{a.severity}</span>
                        </td>
                        <td className="px-5 py-2.5 text-xs text-slate-400">{a.anomaly_type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function Spinner() {
  return (
    <div className="flex justify-center items-center h-48">
      <div className="w-10 h-10 rounded-full border-2 border-red-500 border-t-transparent animate-spin" />
    </div>
  )
}
