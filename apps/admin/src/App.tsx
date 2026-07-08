import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import BasicLayout from './layouts/BasicLayout';
import Dashboard from './pages/Dashboard';
import UserManagement from './pages/UserManagement';
import CharacterManagement from './pages/CharacterManagement';
import MemoryManagement from './pages/MemoryManagement';
import Operations from './pages/Operations';
import SystemConfig from './pages/SystemConfig';
import Login from './pages/Login';

function RequireAdmin({ children }: { children: JSX.Element }) {
  if (!localStorage.getItem('admin_token')) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<RequireAdmin><BasicLayout /></RequireAdmin>}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="users" element={<UserManagement />} />
          <Route path="characters" element={<CharacterManagement />} />
          <Route path="memories" element={<MemoryManagement />} />
          <Route path="operations" element={<Operations />} />
          <Route path="settings" element={<SystemConfig />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
