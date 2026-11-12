import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  FileText,
  Building2,
  ClipboardList,
  ShieldCheck,
  Scale,
  Clock,
  ArrowLeft,
  Download,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileSearch,
  ExternalLink,
} from 'lucide-react';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import ValidationChecklist from '../components/ValidationChecklist';
import ProcessingTimeline from '../components/ProcessingTimeline';
import { formatCurrency, formatDate } from '../utils/format';
import LoadingSpinner from '../components/LoadingSpinner';

export default function InvoiceDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchDetail = async () => {
    try {
      setLoading(true);
      const res = await api.getInvoice(id);
      setData(res.data);
    } catch (err) {
      console.error('Failed to load invoice detail:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [id]);

  if (loading || !data) {
    return <LoadingSpinner message="Loading full invoice analysis..." />;
  }

  const { invoice, line_items, vendor, purchase_order, decision, validation_results, stages, audit_logs } = data;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <Link
            to="/invoices"
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                {invoice.invoice_number || invoice.original_filename}
              </h2>
              <StatusBadge status={invoice.status} size="md" />
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Ingested {formatDate(invoice.created_at)} &bull; Method: {invoice.extraction_method} (Confidence: {(invoice.extraction_confidence * 100).toFixed(0)}%)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {invoice.file_path && (
            <a
              href={api.getInvoicePdfUrl(invoice.id, true)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold px-3.5 py-2 rounded-lg shadow-sm transition-colors"
            >
              <Download className="w-4 h-4 text-slate-500" />
              <span>Download PDF</span>
            </a>
          )}
          {invoice.status === 'REVIEW' && (
            <Link
              to={`/review/${invoice.id}`}
              className="inline-flex items-center gap-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-sm transition-colors"
            >
              <span>Take Review Action</span>
            </Link>
          )}
        </div>
      </div>

      {/* Decision Summary Banner */}
      {decision && (
        <div
          className={`p-5 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 ${
            ['APPROVE', 'APPROVED'].includes(decision.decision)
              ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
              : ['REJECT', 'REJECTED'].includes(decision.decision)
              ? 'bg-rose-50/70 border-rose-200 text-rose-900'
              : 'bg-amber-50/70 border-amber-200 text-amber-900'
          }`}
        >
          <div className="space-y-1">
            <span className="text-[11px] font-bold uppercase tracking-wider opacity-75">
              Audited Payment Decision: {decision.decision}
            </span>
            <p className="text-sm font-semibold">{decision.primary_reason}</p>
            {decision.explanation && decision.explanation.length > 0 && (
              <ul className="text-xs space-y-0.5 mt-2 opacity-90">
                {decision.explanation.slice(0, 3).map((exp, i) => (
                  <li key={i}>{exp}</li>
                ))}
              </ul>
            )}
          </div>
          <div className="text-right text-xs flex-shrink-0">
            <p className="font-bold">Decided by: {decision.decided_by}</p>
            {decision.is_manual_override && (
              <span className="inline-block mt-1 bg-amber-200 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded">
                Manual Override
              </span>
            )}
          </div>
        </div>
      )}

      {/* Two Column Layout: Left Column PDF & Extraction, Right Column Validation & Decision */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (7 cols): PDF Viewer + Line Items */}
        <div className="lg:col-span-7 space-y-6">
          {/* PDF Viewer */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
                <FileText className="w-4 h-4 text-sky-600" />
                Original Document View
              </span>
              <div className="flex items-center gap-3">
                {invoice.file_path && (
                  <a
                    href={api.getInvoicePdfUrl(invoice.id)}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-sky-600 hover:text-sky-700 font-semibold flex items-center gap-1 hover:underline"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Open in New Tab
                  </a>
                )}
                <span className="text-xs text-slate-400 font-mono">
                  {invoice.file_hash ? `${invoice.file_hash.slice(0, 16)}...` : 'Manual Entry'}
                </span>
              </div>
            </div>

            {invoice.file_path ? (
              <div className="w-full h-[520px] bg-slate-100 rounded-lg overflow-hidden border border-slate-200">
                <iframe
                  src={`${api.getInvoicePdfUrl(invoice.id)}#toolbar=1&navpanes=0`}
                  title="Invoice PDF"
                  className="w-full h-full border-0"
                />
              </div>
            ) : (
              <div className="h-64 flex flex-col items-center justify-center bg-slate-50 text-slate-400 rounded-lg border border-dashed border-slate-200 text-xs">
                <FileSearch className="w-8 h-8 mb-2 text-slate-300" />
                <span>Manual invoice entry &bull; No source PDF binary stored</span>
              </div>
            )}
          </div>

          {/* Line Items Table */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Extracted Line Items ({line_items?.length || 0})
              </span>
              <span className="text-xs text-slate-500 font-semibold">
                Subtotal: {formatCurrency(invoice.subtotal, invoice.currency)}
              </span>
            </div>

            {line_items && line_items.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-100">
                    <tr>
                      <th className="py-2 px-3">#</th>
                      <th className="py-2 px-3">Description</th>
                      <th className="py-2 px-3">SKU</th>
                      <th className="py-2 px-3 text-right">Qty</th>
                      <th className="py-2 px-3 text-right">Unit Price</th>
                      <th className="py-2 px-3 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {line_items.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50">
                        <td className="py-2.5 px-3 font-mono text-slate-400">{item.line_number}</td>
                        <td className="py-2.5 px-3 font-medium text-slate-900">{item.description}</td>
                        <td className="py-2.5 px-3 font-mono text-slate-500">{item.sku || '—'}</td>
                        <td className="py-2.5 px-3 text-right font-mono">{item.quantity}</td>
                        <td className="py-2.5 px-3 text-right font-mono">{formatCurrency(item.unit_price)}</td>
                        <td className="py-2.5 px-3 text-right font-bold text-slate-900 font-mono">
                          {formatCurrency(item.total_price)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-500 text-center py-4">No individual line items parsed.</p>
            )}

            {/* Financial Summary Breakdown */}
            <div className="mt-4 pt-3 border-t border-slate-100 flex justify-end">
              <div className="w-64 space-y-1.5 text-xs">
                <div className="flex justify-between text-slate-500">
                  <span>Subtotal:</span>
                  <span>{formatCurrency(invoice.subtotal, invoice.currency)}</span>
                </div>
                <div className="flex justify-between text-slate-500">
                  <span>Tax Amount:</span>
                  <span>{formatCurrency(invoice.tax_amount, invoice.currency)}</span>
                </div>
                {invoice.discount_amount ? (
                  <div className="flex justify-between text-emerald-600">
                    <span>Discount:</span>
                    <span>-{formatCurrency(invoice.discount_amount, invoice.currency)}</span>
                  </div>
                ) : null}
                <div className="flex justify-between font-bold text-sm text-slate-900 pt-2 border-t border-slate-200">
                  <span>Grand Total:</span>
                  <span>{formatCurrency(invoice.grand_total, invoice.currency)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column (5 cols): Matched Vendor/PO, Verification Checklist, Audit History */}
        <div className="lg:col-span-5 space-y-6">
          {/* Matched Vendor & PO Entity Box */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
              Matched Entities
            </span>

            {/* Vendor Card */}
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 flex items-start gap-3">
              <Building2 className="w-5 h-5 text-sky-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-slate-900 truncate">
                    {vendor ? vendor.name : invoice.vendor_name_extracted || 'Unmatched Vendor'}
                  </span>
                  {vendor && (
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        vendor.approval_status === 'APPROVED'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}
                    >
                      {vendor.approval_status}
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  GSTIN / Tax ID: {vendor?.gstin || vendor?.tax_id || invoice.gstin_extracted || 'None'}
                </p>
              </div>
            </div>

            {/* PO Card */}
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 flex items-start gap-3">
              <ClipboardList className="w-5 h-5 text-sky-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-slate-900">
                    {purchase_order ? purchase_order.po_number : invoice.po_number_extracted || 'No PO Matched'}
                  </span>
                  {purchase_order && (
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-sky-100 text-sky-800">
                      {purchase_order.status}
                    </span>
                  )}
                </div>
                {purchase_order ? (
                  <p className="text-[11px] text-slate-500 mt-1">
                    Budget: {formatCurrency(purchase_order.total_amount)} &bull; Remaining: {formatCurrency(purchase_order.remaining_amount)}
                  </p>
                ) : (
                  <p className="text-[11px] text-amber-600 mt-1">Non-PO invoice or unmatched</p>
                )}
              </div>
            </div>
          </div>

          {/* Validation Checklist (11 Business Rules) */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-sky-600" />
                11-Point Validation Checklist
              </span>
              <span className="text-xs font-mono font-bold text-emerald-600">
                {validation_results?.filter((r) => r.passed).length} / {validation_results?.length || 11} Passed
              </span>
            </div>

            <ValidationChecklist results={validation_results || []} />
          </div>

          {/* 10-Stage Processing Timeline */}
          {stages && stages.length > 0 && (
            <ProcessingTimeline stages={stages} />
          )}

          {/* Audit History */}
          {audit_logs && audit_logs.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-3 pb-2 border-b border-slate-100">
                Audit Trail &amp; Modifications
              </span>
              <div className="space-y-2.5">
                {audit_logs.map((log) => (
                  <div key={log.id} className="text-xs p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="flex items-center justify-between font-semibold text-slate-800">
                      <span>{log.action}</span>
                      <span className="text-[11px] font-normal text-slate-400">{formatDate(log.timestamp)}</span>
                    </div>
                    <p className="text-slate-500 mt-1 text-[11px]">{log.notes || 'Status updated'}</p>
                    <span className="text-[10px] text-slate-400 block mt-1">Actor: {log.actor}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
