// src/pages/VendorDashboardPage.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchVendorOrders, updateVendorOrderStatus, type VendorOrder } from '@/api/vendor'
import {
  Truck,
  PackageCheck,
  Clock,
  CheckCircle2,
  AlertCircle,
  Building2,
  RefreshCw,
  Send,
  Calendar,
  X,
  Sparkles,
} from 'lucide-react'

export function VendorDashboardPage() {
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [selectedOrder, setSelectedOrder] = useState<VendorOrder | null>(null)
  const [notesInput, setNotesInput] = useState('')
  const [notification, setNotification] = useState<string | null>(null)

  const queryClient = useQueryClient()

  const { data: orders, isLoading } = useQuery({
    queryKey: ['vendor-orders', statusFilter],
    queryFn: () => fetchVendorOrders(statusFilter || undefined),
    refetchInterval: 5000,
  })

  const notify = (msg: string) => {
    setNotification(msg)
    setTimeout(() => setNotification(null), 4000)
  }

  const updateStatusMutation = useMutation({
    mutationFn: ({ orderId, status, notes }: { orderId: string; status: 'SHIPPED' | 'DELIVERED' | 'CANCELLED'; notes?: string }) =>
      updateVendorOrderStatus(orderId, status, notes),
    onSuccess: (data) => {
      if (data.data.new_status === 'DELIVERED') {
        notify(`Order ${data.data.order_id} fulfilled! ${data.data.quantity} units restocked in Pharmacy inventory.`)
      } else {
        notify(`Order ${data.data.order_id} status updated to ${data.data.new_status}.`)
      }
      setSelectedOrder(null)
      queryClient.invalidateQueries({ queryKey: ['vendor-orders'] })
      queryClient.invalidateQueries({ queryKey: ['inventory-overview'] })
    },
    onError: (err: any) => notify(err.message || 'Update failed'),
  })

  const allOrders = orders || []
  const pendingCount = allOrders.filter((o) => o.status === 'PENDING_VENDOR').length
  const shippedCount = allOrders.filter((o) => o.status === 'SHIPPED').length
  const deliveredCount = allOrders.filter((o) => o.status === 'DELIVERED').length
  const totalUnitsNeeded = allOrders
    .filter((o) => o.status === 'PENDING_VENDOR' || o.status === 'SHIPPED')
    .reduce((sum, o) => sum + o.quantity, 0)

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto text-slate-100">
      {/* Toast */}
      {notification && (
        <div className="fixed top-5 right-5 z-50 px-4 py-3 rounded-xl bg-emerald-950/90 border border-emerald-500/50 text-emerald-200 shadow-2xl flex items-center gap-3 backdrop-blur-md">
          <CheckCircle2 size={18} />
          <span className="text-sm font-medium">{notification}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-card p-6 border-l-4 border-indigo-500">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-md text-[10px] font-extrabold uppercase tracking-wider bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 flex items-center gap-1">
              <Building2 size={12} /> Supplier Portal
            </span>
            <span className="text-xs text-slate-400">• Real-Time Order Stream</span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">Pharmacy Vendor Dashboard</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Receive, process, and fulfill automated replenishment orders placed by the pharmacy decision engine.
          </p>
        </div>

        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: ['vendor-orders'] })}
          className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-2 border border-white/10"
        >
          <RefreshCw size={14} /> Refresh Stream
        </button>
      </div>

      {/* 4 Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-card p-4 space-y-1 border-l-4 border-amber-500">
          <p className="text-[10px] font-extrabold uppercase text-slate-400">Pending Orders</p>
          <p className="text-2xl font-black text-amber-400">{pendingCount}</p>
          <p className="text-[11px] text-slate-400">Awaiting vendor processing</p>
        </div>

        <div className="glass-card p-4 space-y-1 border-l-4 border-indigo-500">
          <p className="text-[10px] font-extrabold uppercase text-slate-400">Shipped In-Transit</p>
          <p className="text-2xl font-black text-indigo-400">{shippedCount}</p>
          <p className="text-[11px] text-slate-400">En route to pharmacy</p>
        </div>

        <div className="glass-card p-4 space-y-1 border-l-4 border-emerald-500">
          <p className="text-[10px] font-extrabold uppercase text-slate-400">Completed & Delivered</p>
          <p className="text-2xl font-black text-emerald-400">{deliveredCount}</p>
          <p className="text-[11px] text-slate-400">Fulfilled & restocked</p>
        </div>

        <div className="glass-card p-4 space-y-1 border-l-4 border-cyan-500">
          <p className="text-[10px] font-extrabold uppercase text-slate-400">Total Units Demanded</p>
          <p className="text-2xl font-black text-cyan-300">{totalUnitsNeeded}</p>
          <p className="text-[11px] text-slate-400">Active pending/shipped units</p>
        </div>
      </div>

      {/* Orders Filter & Table */}
      <div className="glass-card p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Truck size={18} className="text-indigo-400" />
            Incoming Pharmacy Replenishment Orders
          </h2>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Filter Status:</span>
            {['', 'PENDING_VENDOR', 'SHIPPED', 'DELIVERED'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  statusFilter === st
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white text-slate-400 hover:bg-white/5'
                }`}
              >
                {st === '' ? 'All Orders' : st}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-white/10 text-slate-400 uppercase text-[10px] font-bold">
                <th className="py-3 px-3">Order Reference</th>
                <th className="py-3 px-3">Drug</th>
                <th className="py-3 px-3 text-right">Quantity Needed</th>
                <th className="py-3 px-3">Order Date</th>
                <th className="py-3 px-3">Expected Delivery</th>
                <th className="py-3 px-3">Approved By</th>
                <th className="py-3 px-3 text-center">Status</th>
                <th className="py-3 px-3 text-center">Vendor Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {allOrders.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    No vendor orders found matching filter.
                  </td>
                </tr>
              ) : (
                allOrders.map((order) => (
                  <tr key={order.order_id} className="hover:bg-white/5 transition-colors">
                    <td className="py-3.5 px-3 font-mono font-bold text-indigo-300 text-[11px]">
                      {order.order_id}
                    </td>
                    <td className="py-3.5 px-3 font-bold text-white">
                      {order.drug_code} <span className="font-normal text-slate-400 text-[11px] block">{order.drug_name}</span>
                    </td>
                    <td className="py-3.5 px-3 text-right">
                      <span className="px-2.5 py-1 rounded-lg bg-indigo-950/60 border border-indigo-500/30 text-white font-black text-sm">
                        {order.quantity} units
                      </span>
                    </td>
                    <td className="py-3.5 px-3 text-slate-400 text-[11px]">{order.order_date?.substring(0, 16)}</td>
                    <td className="py-3.5 px-3 text-slate-300 text-[11px] font-semibold">{order.expected_arrival}</td>
                    <td className="py-3.5 px-3 text-slate-400">{order.approved_by}</td>
                    <td className="py-3.5 px-3 text-center">
                      <span
                        className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${
                          order.status === 'PENDING_VENDOR'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : order.status === 'SHIPPED'
                            ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                            : order.status === 'DELIVERED'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : 'bg-rose-500/20 text-rose-300'
                        }`}
                      >
                        {order.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-3 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        {order.status === 'PENDING_VENDOR' && (
                          <button
                            onClick={() =>
                              updateStatusMutation.mutate({
                                orderId: order.order_id,
                                status: 'SHIPPED',
                                notes: 'Shipment dispatched via express courier',
                              })
                            }
                            className="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[11px] transition-all flex items-center gap-1"
                          >
                            <Truck size={11} /> Mark Shipped
                          </button>
                        )}

                        {(order.status === 'PENDING_VENDOR' || order.status === 'SHIPPED') && (
                          <button
                            onClick={() =>
                              updateStatusMutation.mutate({
                                orderId: order.order_id,
                                status: 'DELIVERED',
                                notes: 'Shipment delivered to pharmacy store',
                              })
                            }
                            className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-[11px] transition-all flex items-center gap-1"
                          >
                            <PackageCheck size={11} /> Deliver & Fulfill
                          </button>
                        )}

                        {order.status === 'DELIVERED' && (
                          <span className="text-[11px] text-emerald-400 font-semibold flex items-center gap-1">
                            <CheckCircle2 size={12} /> Fulfilled
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
