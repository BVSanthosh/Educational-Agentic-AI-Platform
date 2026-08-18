import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Workspace from './pages/Workspace';
import Login from './pages/Login';
import Register from './pages/Register';
import Settings from './pages/Settings';
import ProtectedRoute from './components/ProtectedRoute';

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Auth Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        
        {/* Protected Application Routes */}
        <Route element={<ProtectedRoute />}>
          <Route path="/workspace" element={<Workspace />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        
        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/workspace" replace />} />
      </Routes>
    </Router>
  );
}