import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import BasicLayout from './layouts/BasicLayout';
import Dashboard from './pages/Dashboard';
import UserManagement from './pages/UserManagement';
import CharacterManagement from './pages/CharacterManagement';
import MemoryManagement from './pages/MemoryManagement';
import SystemConfig from './pages/SystemConfig';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<BasicLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="users" element={<UserManagement />} />
          <Route path="characters" element={<CharacterManagement />} />
          <Route path="memories" element={<MemoryManagement />} />
          <Route path="settings" element={<SystemConfig />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
