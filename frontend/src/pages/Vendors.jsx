import React, { useState, useEffect } from 'react';
import { Building2, Plus, Search, CheckCircle2, XCircle, AlertTriangle, Clock } from 'lucide-react';
import { api } from '../api/client';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';

export default function Vendors() {
  const [vendors, setVendors] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  // Modal create
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [taxId, setTaxId] = useState('');
  const [gstin, setGstin] = useState('');
  const [email, setEmail] = useState('');
  const [country, setCountry] = useState('US');
  const [approvalStatus, setApprovalStatus] = useState('APPROVED');

  const fetchVendors = async () => {
    try {
      setLoading(true);
      const params = {};
      if (statusFilter) params.status = statusFilter;
      if (search) params.search = search;
      const res = await api.listVendors(params);
      setVendors(res.data || []);
    } catch (err) {
      console.error('Failed to load vendors:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVendors();
  }, [statusFilter]);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchVendors();
  };

  const handleCreateVendor = async (e) => {
    e.preventDefault();
    try {
      await api.createVendor({
        name,
        tax_id: taxId || null,
        gstin: gstin || null,
        email: email || null,
        country,
        approval_status: approvalStatus,
      });
      setModalOpen(false);
      setName('');
      setTaxId('');
      setGstin('');
      setEmail('');
      fetchVendors();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create vendor');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Approved Vendor Directory</h2>
          <p className="text-sm text-slate-500 mt-1">
            Maintain authorized supplier master records and compliance approval states.
          </p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="inline-flex items-center gap-2 bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold px-4 py-2.5 rounded-lg shadow-sm transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Add New Vendor</span>
        </button>
      </div>

      {/* Filter and Search */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <form onSubmit={handleSearch} className="flex items-center gap-3 flex-1 max-w-md">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search vendor name, GSTIN, Tax ID..."
              className="w-full text-xs pl-9 pr-4 py-2 rounded-lg border border-slate-200 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            className="bg-slate-900 text-white text-xs font-semibold px-4 py-2 rounded-lg"
          >
            Search
          </button>
        </form>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="text-xs py-2 px-3 rounded-lg border border-slate-200 bg-white text-slate-700"
        >
          <option value="">All Statuses</option>
          <option value="APPROVED">Approved</option>
          <option value="PENDING">Pending</option>
          <option value="REJECTED">Rejected</option>
          <option value="SUSPENDED">Suspended</option>
        </select>
      </div>

      {/* Vendors Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <LoadingSpinner message="Loading vendors directory..." />
        ) : vendors.length === 0 ? (
          <EmptyState title="No vendors found" description="Try clearing your search filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-100">
                <tr>
                  <th className="py-3 px-4">Vendor Name</th>
                  <th className="py-3 px-4">Tax ID / GSTIN</th>
                  <th className="py-3 px-4">Country</th>
                  <th className="py-3 px-4">Contact Email</th>
                  <th className="py-3 px-4">Approval Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700 font-medium">
                {vendors.map((v) => (
                  <tr key={v.id} className="hover:bg-slate-50">
                    <td className="py-3.5 px-4 font-bold text-slate-900 flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-slate-400" />
                      <span>{v.name}</span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-600">
                      {v.gstin || v.tax_id || '—'}
                    </td>
                    <td className="py-3.5 px-4">{v.country}</td>
                    <td className="py-3.5 px-4 text-slate-500">{v.email || '—'}</td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                          v.approval_status === 'APPROVED'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : v.approval_status === 'REJECTED'
                            ? 'bg-rose-50 text-rose-700 border border-rose-200'
                            : v.approval_status === 'SUSPENDED'
                            ? 'bg-purple-50 text-purple-700 border border-purple-200'
                            : 'bg-amber-50 text-amber-700 border border-amber-200'
                        }`}
                      >
                        {v.approval_status === 'APPROVED' ? (
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        ) : v.approval_status === 'REJECTED' ? (
                          <XCircle className="w-3.5 h-3.5" />
                        ) : (
                          <AlertTriangle className="w-3.5 h-3.5" />
                        )}
                        <span>{v.approval_status}</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Add Vendor */}
      {modalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <h3 className="text-base font-bold text-slate-900">Add New Vendor Record</h3>
            <form onSubmit={handleCreateVendor} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Company Name *</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Apex Industrial Supplies"
                  className="w-full text-xs rounded-lg border-slate-300 p-2"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Tax ID / EIN</label>
                <input
                  type="text"
                  value={taxId}
                  onChange={(e) => setTaxId(e.target.value)}
                  placeholder="EIN-XX-XXXXXXX"
                  className="w-full text-xs rounded-lg border-slate-300 p-2"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">GSTIN (Optional)</label>
                <input
                  type="text"
                  value={gstin}
                  onChange={(e) => setGstin(e.target.value)}
                  placeholder="15-character alphanumeric"
                  className="w-full text-xs rounded-lg border-slate-300 p-2"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Contact Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="billing@vendor.com"
                  className="w-full text-xs rounded-lg border-slate-300 p-2"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Approval Status</label>
                <select
                  value={approvalStatus}
                  onChange={(e) => setApprovalStatus(e.target.value)}
                  className="w-full text-xs rounded-lg border-slate-300 p-2 bg-white"
                >
                  <option value="APPROVED">APPROVED</option>
                  <option value="PENDING">PENDING</option>
                  <option value="REJECTED">REJECTED</option>
                  <option value="SUSPENDED">SUSPENDED</option>
                </select>
              </div>

              <div className="pt-3 flex justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="text-xs px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="text-xs px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white font-semibold rounded-lg"
                >
                  Save Vendor
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
