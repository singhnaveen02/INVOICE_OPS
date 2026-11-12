import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Building2,
  ClipboardList,
  Save,
  ShieldAlert,
  FileText,
  RotateCcw,
} from 'lucide-react';
import { api } from '../api/client';
import ValidationChecklist from '../components/ValidationChecklist';
import StatusBadge from '../components/StatusBadge';
import { formatCurrency, formatDate } from '../utils/format';
import LoadingSpinner from '../components/LoadingSpinner';

export default function ReviewDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [revalidating, setRevalidating] = useState(false);
  const [revalidateNotice, setRevalidateNotice] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // Editable Form Fields (Corrections)
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [invoiceDate, setInvoiceDate] = useState('');
  const [grandTotal, setGrandTotal] = useState('');
  const [subtotal, setSubtotal] = useState('');
  const [taxAmount, setTaxAmount] = useState('');
  const [selectedVendorId, setSelectedVendorId] = useState('');
  const [selectedPOId, setSelectedPOId] = useState('');

  // Review Decision Inputs
  const [decisionChoice, setDecisionChoice] = useState('APPROVE'); // 'APPROVE' | 'REJECT'
  const [reviewerName, setReviewerName] = useState('Jane Doe (Senior AP Specialist)');
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [overrideReason, setOverrideReason] = useState('Manual verification completed with procurement team');

  const fetchReviewData = async () => {
    try {
      setLoading(true);
      const res = await api.getReviewDetail(id);
      setData(res.data);
      const inv = res.data.invoice;
      setInvoiceNumber(inv.invoice_number || '');
      setInvoiceDate(inv.invoice_date || '');
      setGrandTotal(inv.grand_total ? String(inv.grand_total) : '');
      setSubtotal(inv.subtotal ? String(inv.subtotal) : '');
      setTaxAmount(inv.tax_amount ? String(inv.tax_amount) : '');
      setSelectedVendorId(inv.vendor_id || '');
      setSelectedPOId(inv.po_id || '');
    } catch (err) {
      console.error('Failed to load review detail:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReviewData();
  }, [id]);

  const handleRevalidate = async () => {
    setRevalidating(true);
    setErrorMsg('');
    setRevalidateNotice('');
    try {
      const payload = {
        reviewer_name: reviewerName,
        field_corrections: {
          invoice_number: invoiceNumber || null,
          invoice_date: invoiceDate || null,
          grand_total: grandTotal ? parseFloat(grandTotal) : null,
          subtotal: subtotal ? parseFloat(subtotal) : null,
          tax_amount: taxAmount ? parseFloat(taxAmount) : null,
        },
        new_vendor_id: selectedVendorId || '',
        new_po_id: selectedPOId || '',
      };
      const res = await api.revalidateReview(id, payload);
      setData((prev) => ({
        ...prev,
        decision: {
          ...(prev?.decision || {}),
          decision: res.data.recommended_decision,
          confidence_score: res.data.confidence_score,
          primary_reason: res.data.primary_reason,
          explanation: res.data.explanation,
          discrepancies: res.data.discrepancies,
          validation_results: res.data.validation_results,
        },
      }));
      setRevalidateNotice(
        `Validation re-executed (${res.data.validation_results.filter((r) => r.passed).length}/${res.data.validation_results.length} passed) — Recommended: ${res.data.recommended_decision}`
      );
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Failed to re-run validation rules');
    } finally {
      setRevalidating(false);
    }
  };

  const handleSubmitDecision = async (e) => {
    e.preventDefault();
    if (!reviewerName.trim()) {
      alert('Reviewer name is mandatory.');
      return;
    }
    if (!overrideReason.trim()) {
      alert('Mandatory justification reason must be specified for audit logs.');
      return;
    }

    setSubmitting(true);
    setErrorMsg('');

    try {
      const payload = {
        decision: decisionChoice,
        reviewer_name: reviewerName,
        reviewer_notes: reviewerNotes,
        override_reason: overrideReason,
        field_corrections: {
          invoice_number: invoiceNumber || null,
          invoice_date: invoiceDate || null,
          grand_total: grandTotal ? parseFloat(grandTotal) : null,
          subtotal: subtotal ? parseFloat(subtotal) : null,
          tax_amount: taxAmount ? parseFloat(taxAmount) : null,
        },
        new_vendor_id: selectedVendorId || null,
        new_po_id: selectedPOId || null,
        rerun_validation: true,
      };

      await api.submitReview(id, payload);
      navigate(`/invoices/${id}`);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Failed to submit review decision');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !data) {
    return <LoadingSpinner message="Loading review workspace..." />;
  }

  const { invoice, decision, available_vendors, available_pos } = data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <Link
            to="/review"
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                Review Workspace: {invoice.original_filename}
              </h2>
              <StatusBadge status="REVIEW" size="md" />
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Review reason: <strong className="text-slate-700">{decision?.primary_reason}</strong>
            </p>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold flex items-center gap-3">
          <ShieldAlert className="w-5 h-5 flex-shrink-0 text-rose-600" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Two Column Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (5 cols): Original Document & Extracted Context */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-3">
              Source PDF Preview
            </span>
            {invoice.id ? (
              <div className="w-full h-[380px] bg-slate-100 rounded-lg overflow-hidden border border-slate-200">
                <iframe
                  src={api.getInvoicePdfUrl(invoice.id)}
                  title="Source PDF"
                  className="w-full h-full"
                />
              </div>
            ) : null}
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-3 pb-2 border-b border-slate-100">
              Raw Automated Extraction
            </span>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span className="text-slate-400">Extracted Vendor:</span>
                <span className="font-semibold text-slate-800">{invoice.vendor_name_extracted || 'None'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span className="text-slate-400">Extracted PO:</span>
                <span className="font-mono text-slate-800">{invoice.po_number_extracted || 'None'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span className="text-slate-400">Extracted Amount:</span>
                <span className="font-bold text-slate-900">{formatCurrency(invoice.grand_total)}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Extraction Confidence:</span>
                <span className="font-mono font-bold text-amber-600">{(invoice.extraction_confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-3 pb-2 border-b border-slate-100">
              Validation Checklist ({decision?.validation_results?.filter((r) => r.passed).length || 0}/{decision?.validation_results?.length || 11} Passed)
            </span>
            <ValidationChecklist results={decision?.validation_results || []} />
          </div>
        </div>

        {/* Right Column (7 cols): Human Review & Correction Form */}
        <div className="lg:col-span-7">
          <form
            onSubmit={handleSubmitDecision}
            className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6"
          >
            <div>
              <h3 className="text-base font-bold text-slate-900">Field Corrections &amp; Overrides</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Adjust parsed fields or manually link to the correct approved vendor and purchase order.
              </p>
            </div>

            {/* Vendor & PO Re-assignment */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Re-assign Approved Vendor
                </label>
                <select
                  value={selectedVendorId}
                  onChange={(e) => setSelectedVendorId(e.target.value)}
                  className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2 bg-white"
                >
                  <option value="">-- No Vendor Linked --</option>
                  {available_vendors?.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name} ({v.approval_status})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Re-assign Purchase Order
                </label>
                <select
                  value={selectedPOId}
                  onChange={(e) => setSelectedPOId(e.target.value)}
                  className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2 bg-white"
                >
                  <option value="">-- No PO Linked --</option>
                  {available_pos?.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.po_number} (Rem: {formatCurrency(p.remaining_amount)})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Editable Field Corrections */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Invoice Number
                </label>
                <input
                  type="text"
                  value={invoiceNumber}
                  onChange={(e) => setInvoiceNumber(e.target.value)}
                  className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Invoice Date
                </label>
                <input
                  type="date"
                  value={invoiceDate}
                  onChange={(e) => setInvoiceDate(e.target.value)}
                  className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Grand Total ($)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={grandTotal}
                  onChange={(e) => setGrandTotal(e.target.value)}
                  className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2 font-bold"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Subtotal ($)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={subtotal}
                  onChange={(e) => setSubtotal(e.target.value)}
                  className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Tax Amount ($)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={taxAmount}
                  onChange={(e) => setTaxAmount(e.target.value)}
                  className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2"
                />
              </div>
            </div>

            {/* Decision Radio Selector */}
            <div className="pt-4 border-t border-slate-200">
              <label className="block text-xs font-bold text-slate-900 mb-2">
                Mandatory Review Decision *
              </label>
              <div className="grid grid-cols-2 gap-4">
                <label
                  className={`p-4 rounded-xl border cursor-pointer flex items-center gap-3 transition-colors ${
                    decisionChoice === 'APPROVE'
                      ? 'border-emerald-500 bg-emerald-50 text-emerald-900 ring-1 ring-emerald-500'
                      : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <input
                    type="radio"
                    name="decisionChoice"
                    value="APPROVE"
                    checked={decisionChoice === 'APPROVE'}
                    onChange={() => setDecisionChoice('APPROVE')}
                    className="text-emerald-600 focus:ring-emerald-500"
                  />
                  <div>
                    <span className="font-bold text-xs block">APPROVE FOR PAYMENT</span>
                    <span className="text-[11px] text-slate-500">
                      Discrepancies resolved &amp; vendor approved
                    </span>
                  </div>
                </label>

                <label
                  className={`p-4 rounded-xl border cursor-pointer flex items-center gap-3 transition-colors ${
                    decisionChoice === 'REJECT'
                      ? 'border-rose-500 bg-rose-50 text-rose-900 ring-1 ring-rose-500'
                      : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <input
                    type="radio"
                    name="decisionChoice"
                    value="REJECT"
                    checked={decisionChoice === 'REJECT'}
                    onChange={() => setDecisionChoice('REJECT')}
                    className="text-rose-600 focus:ring-rose-500"
                  />
                  <div>
                    <span className="font-bold text-xs block">REJECT INVOICE</span>
                    <span className="text-[11px] text-slate-500">
                      Unresolvable policy error or fraudulent bill
                    </span>
                  </div>
                </label>
              </div>
            </div>

            {/* Mandatory Reviewer Details & Audit Rationale */}
            <div className="space-y-4 pt-2">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Reviewer Name *
                </label>
                <input
                  type="text"
                  required
                  value={reviewerName}
                  onChange={(e) => setReviewerName(e.target.value)}
                  className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Justification / Audit Rationale *
                </label>
                <input
                  type="text"
                  required
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="e.g. Verified vendor tax ID against state register; price variance within approved limits."
                  className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Internal AP Notes
                </label>
                <textarea
                  rows={2}
                  value={reviewerNotes}
                  onChange={(e) => setReviewerNotes(e.target.value)}
                  placeholder="Optional internal comments for accounts payable audit logs..."
                  className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2"
                />
              </div>
            </div>

            {revalidateNotice && (
              <div className="p-3 rounded-lg bg-sky-50 border border-sky-200 text-sky-800 text-xs font-medium">
                {revalidateNotice}
              </div>
            )}

            <div className="pt-4 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3">
              <button
                type="button"
                onClick={handleRevalidate}
                disabled={revalidating || submitting}
                className="inline-flex items-center gap-2 bg-sky-50 hover:bg-sky-100 text-sky-700 border border-sky-200 text-xs font-semibold px-4 py-2.5 rounded-lg transition-colors"
              >
                <RotateCcw className={`w-4 h-4 ${revalidating ? 'animate-spin' : ''}`} />
                <span>{revalidating ? 'Re-validating...' : 'Re-run Validation'}</span>
              </button>

              <div className="flex items-center gap-3">
                <Link
                  to={`/invoices/${id}`}
                  className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold px-4 py-2.5 rounded-lg transition-colors"
                >
                  Cancel
                </Link>
                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex items-center gap-2 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 text-white text-xs font-semibold px-6 py-2.5 rounded-lg shadow-sm transition-colors"
                >
                  <Save className="w-4 h-4" />
                  <span>{submitting ? 'Applying Decision...' : 'Commit Review Decision'}</span>
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
