import React, { useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate, Link } from 'react-router-dom';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  Plus,
  Trash2,
  Building2,
  ClipboardList,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../api/client';
import ProcessingTimeline from '../components/ProcessingTimeline';
import StatusBadge from '../components/StatusBadge';
import { formatCurrency } from '../utils/format';

export default function Upload() {
  const [activeTab, setActiveTab] = useState('pdf'); // 'pdf' | 'manual' | 'csv'
  const navigate = useNavigate();

  // PDF Upload states
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processedInvoices, setProcessedInvoices] = useState([]);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState(null);
  const [liveStagesByInvoice, setLiveStagesByInvoice] = useState({});
  const [activeInvoiceDetail, setActiveInvoiceDetail] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const eventSourcesRef = React.useRef([]);

  const closeAllStreams = () => {
    eventSourcesRef.current.forEach((es) => {
      try {
        es.close();
      } catch (e) {
        // ignore
      }
    });
    eventSourcesRef.current = [];
  };

  useEffect(() => {
    return () => closeAllStreams();
  }, []);

  // Dropzone setup
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
    onDrop: (accepted) => {
      setFiles(accepted);
      setErrorMsg('');
    },
  });

  const subscribeToInvoiceStream = (invId, isPrimary) => {
    const es = new EventSource(api.getEventsUrl(invId));
    eventSourcesRef.current.push(es);

    es.onmessage = async (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.event === 'error') {
          es.close();
          return;
        }
        if (payload.event === 'done') {
          es.close();
          try {
            const detailRes = await api.getInvoice(invId);
            const fullData = detailRes.data;
            setProcessedInvoices((prev) =>
              prev.map((item) =>
                item.id === invId
                  ? {
                      ...item,
                      status: fullData.invoice.status,
                      invoice_number: fullData.invoice.invoice_number,
                      grand_total: fullData.invoice.grand_total,
                      confidence: fullData.invoice.extraction_confidence,
                    }
                  : item
              )
            );
            setSelectedInvoiceId((currentSelected) => {
              if (currentSelected === invId || isPrimary) {
                setActiveInvoiceDetail(fullData);
              }
              return currentSelected;
            });
          } catch (err) {
            console.error('Failed to fetch finalized invoice detail:', err);
          }
          return;
        }

        if (payload.stage_name) {
          setLiveStagesByInvoice((prev) => {
            const existing = prev[invId] || [];
            const idx = existing.findIndex((s) => s.stage_name === payload.stage_name);
            const updated =
              idx >= 0
                ? existing.map((s, i) => (i === idx ? payload : s))
                : [...existing, payload];
            return { ...prev, [invId]: updated };
          });
        }
      } catch (parseErr) {
        console.error('Malformed SSE payload:', parseErr);
      }
    };

    es.onerror = () => {
      es.close();
    };
  };

  const handleUploadSubmit = async () => {
    if (files.length === 0) return;
    closeAllStreams();
    setUploading(true);
    setUploadProgress(0);
    setErrorMsg('');
    setProcessedInvoices([]);
    setSelectedInvoiceId(null);
    setLiveStagesByInvoice({});
    setActiveInvoiceDetail(null);

    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    try {
      const res = await api.uploadInvoices(
        formData,
        (evt) => {
          if (evt.total) {
            setUploadProgress(Math.round((evt.loaded * 100) / evt.total));
          }
        },
        true
      );
      const results = res.data.invoices || [];
      setProcessedInvoices(results);

      if (results.length > 0) {
        setSelectedInvoiceId(results[0].id);
        results.forEach((inv, idx) => {
          subscribeToInvoiceStream(inv.id, idx === 0);
        });
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Upload failed. Please check the backend service.');
    } finally {
      setUploading(false);
    }
  };

  const inspectInvoice = async (id) => {
    setSelectedInvoiceId(id);
    try {
      const res = await api.getInvoice(id);
      setActiveInvoiceDetail(res.data);
    } catch (err) {
      console.error('Failed to load invoice detail:', err);
    }
  };

  // Manual Invoice Form State
  const [manualVendorId, setManualVendorId] = useState('');
  const [manualPOId, setManualPOId] = useState('');
  const [manualInvoiceNumber, setManualInvoiceNumber] = useState('');
  const [manualDate, setManualDate] = useState(new Date().toISOString().slice(0, 10));
  const [manualDueDate, setManualDueDate] = useState('');
  const [manualCurrency, setManualCurrency] = useState('USD');
  const [manualSubtotal, setManualSubtotal] = useState('');
  const [manualTax, setManualTax] = useState('');
  const [manualGrandTotal, setManualGrandTotal] = useState('');
  const [manualNotes, setManualNotes] = useState('');
  const [vendorsList, setVendorsList] = useState([]);
  const [posList, setPosList] = useState([]);
  const [manualSuccess, setManualSuccess] = useState(null);

  useEffect(() => {
    api.listVendors().then((res) => setVendorsList(res.data || []));
    api.listPOs().then((res) => setPosList(res.data || []));
  }, []);

  const handleManualSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        original_filename: `Manual_${manualInvoiceNumber || 'Invoice'}.pdf`,
        invoice_number: manualInvoiceNumber,
        invoice_date: manualDate || null,
        due_date: manualDueDate || null,
        vendor_id: manualVendorId || null,
        po_id: manualPOId || null,
        currency: manualCurrency,
        subtotal: manualSubtotal ? parseFloat(manualSubtotal) : null,
        tax_amount: manualTax ? parseFloat(manualTax) : null,
        grand_total: manualGrandTotal ? parseFloat(manualGrandTotal) : null,
        notes: manualNotes,
      };
      const res = await api.createManualInvoice(payload);
      setManualSuccess(res.data);
    } catch (err) {
      alert('Failed to submit manual invoice: ' + (err.response?.data?.detail || err.message));
    }
  };

  // CSV Import States
  const [vendorCsvFile, setVendorCsvFile] = useState(null);
  const [poCsvFile, setPoCsvFile] = useState(null);
  const [csvStatus, setCsvStatus] = useState('');

  const handleVendorCsvUpload = async () => {
    if (!vendorCsvFile) return;
    const fd = new FormData();
    fd.append('file', vendorCsvFile);
    try {
      setCsvStatus('Importing vendors...');
      const res = await api.importVendorsCsv(fd);
      setCsvStatus(`Vendors imported: ${res.data.imported} created, ${res.data.updated} updated.`);
      setVendorCsvFile(null);
    } catch (err) {
      setCsvStatus('Vendor CSV import failed.');
    }
  };

  const handlePOCsvUpload = async () => {
    if (!poCsvFile) return;
    const fd = new FormData();
    fd.append('file', poCsvFile);
    try {
      setCsvStatus('Importing purchase orders...');
      const res = await api.importPOsCsv(fd);
      setCsvStatus(`POs imported: ${res.data.imported} created, ${res.data.updated} updated.`);
      setPoCsvFile(null);
    } catch (err) {
      setCsvStatus('PO CSV import failed.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Invoice Ingestion Center</h2>
        <p className="text-sm text-slate-500 mt-1">
          Upload PDF invoices, input manual bills, or ingest vendor/PO master CSV records.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-6">
        <button
          onClick={() => setActiveTab('pdf')}
          className={`pb-3 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'pdf'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          PDF Document Upload
        </button>
        <button
          onClick={() => setActiveTab('manual')}
          className={`pb-3 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'manual'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Manual Invoice Entry
        </button>
        <button
          onClick={() => setActiveTab('csv')}
          className={`pb-3 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'csv'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          CSV Master Data Import
        </button>
      </div>

      {/* TAB 1: PDF UPLOAD */}
      {activeTab === 'pdf' && (
        <div className="space-y-8">
          {/* Dropzone Box */}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all cursor-pointer ${
              isDragActive
                ? 'border-sky-500 bg-sky-50/50'
                : 'border-slate-300 hover:border-slate-400 bg-white'
            }`}
          >
            <input {...getInputProps()} />
            <div className="w-14 h-14 rounded-2xl bg-sky-50 text-sky-600 flex items-center justify-center mx-auto mb-4">
              <UploadCloud className="w-7 h-7" />
            </div>
            <h3 className="text-base font-semibold text-slate-900">
              Drag &amp; drop vendor invoice PDFs here
            </h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Supports single or multiple PDF documents. Scanned and machine-readable formats automatically parsed.
            </p>
            <div className="mt-4">
              <span className="inline-flex items-center text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200">
                Browse PDF Files
              </span>
            </div>
          </div>

          {/* Staged Files List */}
          {files.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  {files.length} File{files.length > 1 ? 's' : ''} Staged for Processing
                </span>
                <button
                  onClick={handleUploadSubmit}
                  disabled={uploading}
                  className="inline-flex items-center gap-2 bg-sky-600 hover:bg-sky-700 disabled:bg-slate-300 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors"
                >
                  {uploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Uploading ({uploadProgress}%)...</span>
                    </>
                  ) : (
                    <>
                      <span>Start Automated Processing</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

              <div className="divide-y divide-slate-100">
                {files.map((f, i) => (
                  <div key={i} className="py-2.5 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2.5">
                      <FileText className="w-4 h-4 text-slate-400" />
                      <span className="font-medium text-slate-800">{f.name}</span>
                    </div>
                    <span className="text-slate-400 font-mono">
                      {(f.size / 1024).toFixed(1)} KB
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {errorMsg && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
              {errorMsg}
            </div>
          )}

          {/* Processed Invoices Carousel / Results */}
          {processedInvoices.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-900">
                  Processing Outcome ({processedInvoices.length} Invoices)
                </h3>
                <span className="text-xs text-slate-500">
                  Select an invoice below to inspect live pipeline execution
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {processedInvoices.map((inv) => {
                  const isSelected = selectedInvoiceId === inv.id;
                  return (
                    <div
                      key={inv.id}
                      onClick={() => inspectInvoice(inv.id)}
                      className={`p-4 rounded-xl border cursor-pointer transition-all ${
                        isSelected
                          ? 'border-sky-500 bg-sky-50/30 shadow-sm ring-1 ring-sky-500'
                          : 'border-slate-200 bg-white hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="truncate pr-2">
                          <p className="font-semibold text-xs text-slate-900 truncate">
                            {inv.original_filename}
                          </p>
                          <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                            {inv.invoice_number || 'Extracting...'}
                          </p>
                        </div>
                        <StatusBadge status={inv.status} size="sm" />
                      </div>
                      <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs">
                        <span className="font-semibold text-slate-800">
                          {inv.grand_total !== null && inv.grand_total !== undefined
                            ? formatCurrency(inv.grand_total)
                            : '—'}
                        </span>
                        <span className="text-slate-400 text-[11px]">
                          Confidence: {((inv.confidence || 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Live Pipeline View for Selected Invoice (SSE-driven) */}
          {selectedInvoiceId && (
            <div className="space-y-6 pt-4 border-t border-slate-200">
              {(() => {
                const selectedSummary = processedInvoices.find((p) => p.id === selectedInvoiceId);
                const detailMatches = activeInvoiceDetail?.invoice?.id === selectedInvoiceId;
                const liveStages = liveStagesByInvoice[selectedInvoiceId] || [];
                const stagesToShow =
                  detailMatches && activeInvoiceDetail.stages?.length > 0
                    ? activeInvoiceDetail.stages
                    : liveStages;
                const currentStatus = detailMatches
                  ? activeInvoiceDetail.invoice.status
                  : selectedSummary?.status || 'PROCESSING';

                return (
                  <>
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-bold text-slate-900">
                          Execution Details:{' '}
                          {detailMatches
                            ? activeInvoiceDetail.invoice.original_filename
                            : selectedSummary?.original_filename}
                        </h3>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Live Server-Sent Events (SSE) &bull; {stagesToShow.filter((s) => s.status === 'COMPLETED' || s.status === 'WARNING').length} / 10 stages completed
                        </p>
                      </div>
                      {detailMatches && (
                        <Link
                          to={`/invoices/${activeInvoiceDetail.invoice.id}`}
                          className="text-xs font-semibold text-sky-600 hover:underline flex items-center gap-1"
                        >
                          <span>Open Full Invoice Analysis</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      )}
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                      {/* 10-Stage Pipeline Timeline */}
                      <div className="lg:col-span-2">
                        <ProcessingTimeline stages={stagesToShow} />
                      </div>

                      {/* Outcome & Decision Card */}
                      <div className="space-y-4">
                        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
                          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                            Policy Decision
                          </span>
                          <div className="mt-3">
                            <StatusBadge status={currentStatus} size="lg" />
                          </div>

                          <div className="mt-4 pt-4 border-t border-slate-100 space-y-2 text-xs">
                            <div>
                              <span className="text-slate-400">Primary Reason:</span>
                              <p className="font-semibold text-slate-800 mt-0.5">
                                {detailMatches
                                  ? activeInvoiceDetail.decision?.primary_reason || 'Pipeline evaluated'
                                  : 'Streaming backend stages via SSE...'}
                              </p>
                            </div>
                            <div>
                              <span className="text-slate-400">Matched Vendor:</span>
                              <p className="font-semibold text-slate-800 mt-0.5">
                                {detailMatches
                                  ? activeInvoiceDetail.vendor?.name || 'Unmatched'
                                  : 'Resolving...'}
                              </p>
                            </div>
                            <div>
                              <span className="text-slate-400">Matched PO:</span>
                              <p className="font-semibold text-slate-800 mt-0.5">
                                {detailMatches
                                  ? activeInvoiceDetail.purchase_order?.po_number || 'Unmatched'
                                  : 'Matching...'}
                              </p>
                            </div>
                          </div>

                          {detailMatches && (
                            <div className="mt-6">
                              <Link
                                to={`/invoices/${activeInvoiceDetail.invoice.id}`}
                                className="w-full inline-flex items-center justify-center gap-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold py-2.5 rounded-lg transition-colors"
                              >
                                Inspect Verification Checklist
                              </Link>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </>
                );
              })()}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: MANUAL INVOICE ENTRY */}
      {activeTab === 'manual' && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm max-w-3xl">
          {manualSuccess ? (
            <div className="p-6 text-center space-y-4">
              <div className="w-12 h-12 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Manual Invoice Created!</h3>
              <p className="text-xs text-slate-500">
                Invoice {manualSuccess.invoice_number} processed with decision:{' '}
                <strong>{manualSuccess.status}</strong>
              </p>
              <div className="flex justify-center gap-3 pt-2">
                <Link
                  to={`/invoices/${manualSuccess.id}`}
                  className="bg-sky-600 text-white text-xs font-semibold px-4 py-2 rounded-lg"
                >
                  View Details
                </Link>
                <button
                  onClick={() => setManualSuccess(null)}
                  className="bg-slate-100 text-slate-700 text-xs font-semibold px-4 py-2 rounded-lg"
                >
                  Create Another
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleManualSubmit} className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Select Approved Vendor *
                  </label>
                  <select
                    value={manualVendorId}
                    onChange={(e) => setManualVendorId(e.target.value)}
                    required
                    className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2.5 bg-slate-50"
                  >
                    <option value="">-- Choose Vendor --</option>
                    {vendorsList.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name} ({v.approval_status})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Select Purchase Order
                  </label>
                  <select
                    value={manualPOId}
                    onChange={(e) => setManualPOId(e.target.value)}
                    className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2.5 bg-slate-50"
                  >
                    <option value="">-- Choose PO (Optional) --</option>
                    {posList.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.po_number} - Budget {formatCurrency(p.total_amount)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Invoice Number *
                  </label>
                  <input
                    type="text"
                    required
                    value={manualInvoiceNumber}
                    onChange={(e) => setManualInvoiceNumber(e.target.value)}
                    placeholder="e.g. INV-2024-990"
                    className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2.5"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Invoice Date *
                  </label>
                  <input
                    type="date"
                    required
                    value={manualDate}
                    onChange={(e) => setManualDate(e.target.value)}
                    className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2.5"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Subtotal ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={manualSubtotal}
                    onChange={(e) => setManualSubtotal(e.target.value)}
                    placeholder="0.00"
                    className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2.5"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Grand Total ($) *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={manualGrandTotal}
                    onChange={(e) => setManualGrandTotal(e.target.value)}
                    placeholder="0.00"
                    className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2.5 font-bold"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Notes &amp; Reason
                </label>
                <textarea
                  rows={2}
                  value={manualNotes}
                  onChange={(e) => setManualNotes(e.target.value)}
                  placeholder="Optional context for manual submission..."
                  className="w-full text-xs rounded-lg border-slate-300 shadow-sm p-2.5"
                />
              </div>

              <button
                type="submit"
                className="bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold px-5 py-2.5 rounded-lg transition-colors"
              >
                Submit Manual Invoice
              </button>
            </form>
          )}
        </div>
      )}

      {/* TAB 3: CSV IMPORT */}
      {activeTab === 'csv' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Vendors CSV Import */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2 text-slate-900">
                <Building2 className="w-5 h-5 text-sky-600" />
                <h3 className="text-sm font-bold">Import Vendors Master CSV</h3>
              </div>
              <p className="text-xs text-slate-500 mb-4">
                Headers: name, gstin, tax_id, email, phone, address, country, approval_status
              </p>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setVendorCsvFile(e.target.files?.[0] || null)}
                className="text-xs text-slate-600 block w-full mb-4"
              />
            </div>
            <button
              onClick={handleVendorCsvUpload}
              disabled={!vendorCsvFile}
              className="bg-slate-900 hover:bg-slate-800 disabled:bg-slate-200 text-white text-xs font-semibold py-2.5 px-4 rounded-lg transition-colors w-full"
            >
              Upload Vendors CSV
            </button>
          </div>

          {/* POs CSV Import */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2 text-slate-900">
                <ClipboardList className="w-5 h-5 text-sky-600" />
                <h3 className="text-sm font-bold">Import Purchase Orders CSV</h3>
              </div>
              <p className="text-xs text-slate-500 mb-4">
                Headers: po_number, vendor_name, total_amount, currency, issue_date, status
              </p>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setPoCsvFile(e.target.files?.[0] || null)}
                className="text-xs text-slate-600 block w-full mb-4"
              />
            </div>
            <button
              onClick={handlePOCsvUpload}
              disabled={!poCsvFile}
              className="bg-slate-900 hover:bg-slate-800 disabled:bg-slate-200 text-white text-xs font-semibold py-2.5 px-4 rounded-lg transition-colors w-full"
            >
              Upload Purchase Orders CSV
            </button>
          </div>

          {csvStatus && (
            <div className="md:col-span-2 p-3 bg-sky-50 text-sky-800 border border-sky-200 rounded-lg text-xs font-medium">
              {csvStatus}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
