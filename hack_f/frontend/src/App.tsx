import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import 'dayjs/locale/ru';

import Layout from './components/Layout.tsx';
import Dashboard from './pages/Dashboard.tsx';
import FlightsList from './pages/FlightsList.tsx';
import Analytics from './pages/Analytics.tsx';
import Reports from './pages/Reports.tsx';
import Upload from './pages/Upload.tsx';
import Regions from './pages/Regions.tsx';

import './App.css';

const App: React.FC = () => {
  return (
    <ConfigProvider locale={ruRU}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/flights" element={<FlightsList />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/regions" element={<Regions />} />
          </Routes>
        </Layout>
      </Router>
    </ConfigProvider>
  );
};

export default App;
