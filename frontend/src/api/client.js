import axios from 'axios';

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Health
  getHealth: () => client.get('/health'),

  // Dashboard
  getStats: () => client.get('/dashboard/stats'),
  getTrends: () => client.get('/dashboard/trends'),
  getStatusDistribution: () => client.get('/dashboard/status-distribution'),
  getPOUtilization: () => client.get('/dashboard/po-utilization'),
  getRecentActivity: () => client.get('/dashboard/recent-activity'),

  // Invoices
  uploadInvoices: (formData, onProgress, live = false) =>
    client.post(`/invoices/upload?live=${live ? 'true' : 'false'}`, formData, {
      headers: { 'Content-Type': undefined },
      onUploadProgress: onProgress,
    }),
  createManualInvoice: (data) => client.post('/invoices/manual', data),
  listInvoices: (params) => client.get('/invoices/', { params }),
  getInvoice: (id) => client.get(`/invoices/${id}`),
  deleteInvoice: (id) => client.delete(`/invoices/${id}`),
  getInvoicePdfUrl: (id) => `${API_BASE}/invoices/${id}/pdf`,
  getEventsUrl: (id) => `${API_BASE}/events/invoice/${id}`,
  exportInvoicesUrl: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return `${API_BASE}/invoices/export?${qs}`;
  },

  // Vendors
  listVendors: (params) => client.get('/vendors/', { params }),
  createVendor: (data) => client.post('/vendors/', data),
  updateVendor: (id, data) => client.put(`/vendors/${id}`, data),
  getVendor: (id) => client.get(`/vendors/${id}`),
  importVendorsCsv: (formData) =>
    client.post('/vendors/import-csv', formData, {
      headers: { 'Content-Type': undefined },
    }),

  // Purchase Orders
  listPOs: (params) => client.get('/purchase-orders/', { params }),
  createPO: (data) => client.post('/purchase-orders/', data),
  updatePO: (id, data) => client.put(`/purchase-orders/${id}`, data),
  getPO: (id) => client.get(`/purchase-orders/${id}`),
  importPOsCsv: (formData) =>
    client.post('/purchase-orders/import-csv', formData, {
      headers: { 'Content-Type': undefined },
    }),

  // Human Review
  getReviewQueue: () => client.get('/review/queue'),
  getReviewDetail: (id) => client.get(`/review/${id}`),
  revalidateReview: (id, data) => client.post(`/review/${id}/revalidate`, data),
  submitReview: (id, data) => client.post(`/review/${id}/submit`, data),
};

export default client;
