import React from 'react';
import { Route, Routes } from 'react-router-dom';

import { TooltipProvider } from '@/components/ui/tooltip';

import NotFound from './pages/NotFound/NotFound';
import { DashboardShell } from './dashboard/DashboardShell';
import { DashStyleProvider } from './dashboard/theme/DashStyleProvider';
import OverviewBoard from './pages/dashboard/OverviewBoard';
import StoresBoard from './pages/dashboard/StoresBoard';
import ProductsBoard from './pages/dashboard/ProductsBoard';
import MembersBoard from './pages/dashboard/MembersBoard';
import BigScreenBoard from './pages/dashboard/BigScreenBoard';
import SpecBoardPage from './pages/dashboard/SpecBoardPage';
import TemplateCenter from './pages/dashboard/TemplateCenter';

const RoutesComponent = () => {
  return (
    <DashStyleProvider defaultStyle="espresso">
      <TooltipProvider delayDuration={200}>
        <Routes>
          <Route element={<DashboardShell />}>
            <Route index element={<OverviewBoard />} />
            <Route path="stores" element={<StoresBoard />} />
            <Route path="products" element={<ProductsBoard />} />
            <Route path="members" element={<MembersBoard />} />
            <Route path="spec/:boardKey" element={<SpecBoardPage />} />
            <Route path="templates" element={<TemplateCenter />} />
          </Route>
          <Route path="bigscreen" element={<BigScreenBoard />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </TooltipProvider>
    </DashStyleProvider>
  );
};

export default RoutesComponent;
