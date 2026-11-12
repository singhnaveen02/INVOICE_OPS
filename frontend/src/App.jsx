import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import InvoiceList from './pages/InvoiceList';
import InvoiceDetail from './pages/InvoiceDetail';
import ReviewQueue from './pages/ReviewQueue';
import ReviewDetail from './pages/ReviewDetail';
import Vendors from './pages/Vendors';
import PurchaseOrders from './pages/PurchaseOrders';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="upload" element={<Upload />} />
          <Route path="invoices" element={<InvoiceList />} />
          <Route path="invoices/:id" element={<InvoiceDetail />} />
          <Route path="review" element={<ReviewQueue />} />
          <Route path="review/:id" element={<ReviewDetail />} />
          <Route path="vendors" element={<Vendors />} />
          <Route path="purchase-orders" element={<PurchaseOrders />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
