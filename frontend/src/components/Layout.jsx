import React, { useState, useEffect } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  UploadCloud,
  FileText,
  AlertCircle,
  Building2,
  ClipboardList,
  ShieldCheck,
  Menu,
  X,
  Bell,
  RefreshCw,
} from 'lucide-react';
import { api } from '../api/client';

export default function Layout() {
  const [reviewCount, setReviewCount] = useState(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const fetchReviewCount = async () => {
    try {
      const res = await api.getReviewQueue();
      setReviewCount(res.data?.length || 0);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchReviewCount();
    const interval = setInterval(fetchReviewCount, 8000);
    return () => clearInterval(interval);
  }, [location.pathname]);

  const navItems = [
    { name: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
    { name: 'Upload & Process', to: '/upload', icon: UploadCloud },
    { name: 'Invoice History', to: '/invoices', icon: FileText },
    {
      name: 'Review Queue',
      to: '/review',
      icon: AlertCircle,
      badge: reviewCount > 0 ? reviewCount : null,
      badgeColor: 'bg-amber-500 text-white',
    },
    { name: 'Vendors', to: '/vendors', icon: Building2 },
    { name: 'Purchase Orders', to: '/purchase-orders', icon: ClipboardList },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row">
      {/* Mobile Header */}
      <div className="md:hidden bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-sky-600 flex items-center justify-center text-white font-bold text-sm">
            IO
          </div>
          <span className="font-bold text-slate-900 tracking-tight">InvoiceOps</span>
        </div>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 text-slate-600 hover:text-slate-900"
        >
          {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Sidebar */}
      <aside
        className={`fixed md:sticky top-0 left-0 h-screen w-64 bg-slate-900 text-slate-300 flex flex-col justify-between z-40 transition-transform ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div>
          {/* Brand Logo */}
          <div className="px-6 py-6 border-b border-slate-800 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-500 flex items-center justify-center text-white font-black text-base shadow-sm">
              IO
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight">InvoiceOps</h1>
              <p className="text-[11px] text-slate-400 font-medium">AP Automation Center</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.name}
                  to={item.to}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                      isActive
                        ? 'bg-sky-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800'
                    }`
                  }
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-4 h-4" />
                    <span>{item.name}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${item.badgeColor}`}
                    >
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* System Health / Footer status */}
        <div className="p-4 m-3 bg-slate-800/80 rounded-xl border border-slate-700/60 text-xs">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="font-semibold text-slate-200">Rule Engine Online</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Multi-stage PO Matching &amp; 11-rule automated validation active.
          </p>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Navbar */}
        <header className="hidden md:flex bg-white border-b border-slate-200 px-8 py-3.5 items-center justify-between sticky top-0 z-30">
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 font-medium">Accounts Payable Control Center</span>
            <span className="text-slate-300">/</span>
            <span className="text-xs font-semibold text-slate-800 capitalize">
              {location.pathname.replace('/', '') || 'Dashboard'}
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-emerald-50 text-emerald-700 px-3 py-1 rounded-full text-xs font-medium border border-emerald-100">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Deterministic Auditing</span>
            </div>
          </div>
        </header>

        {/* Page Container */}
        <div className="p-6 md:p-8 flex-1 max-w-7xl w-full mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
