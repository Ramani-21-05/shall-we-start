// src/api/vendor.ts
const API_BASE = `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/api/v2/vendor`

export interface VendorOrder {
  order_id: string
  drug_code: string
  drug_name: string
  category: string
  quantity: number
  order_date: string
  expected_arrival: string
  status: 'PENDING_VENDOR' | 'SHIPPED' | 'DELIVERED' | 'CANCELLED'
  approved_by: string
  reason: string
  vendor_notes: string
}

export async function fetchVendorOrders(statusFilter?: string): Promise<VendorOrder[]> {
  const url = statusFilter ? `${API_BASE}/orders?status=${statusFilter}` : `${API_BASE}/orders`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to fetch vendor orders')
  const json = await res.json()
  return json.data || []
}

export async function updateVendorOrderStatus(
  orderId: string,
  status: 'SHIPPED' | 'DELIVERED' | 'CANCELLED',
  vendorNotes = ''
) {
  const res = await fetch(`${API_BASE}/orders/${orderId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, vendor_notes: vendorNotes })
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to update order status')
  }
  return res.json()
}
