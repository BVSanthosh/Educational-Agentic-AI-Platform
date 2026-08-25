import { useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import Workspace from './pages/Workspace';
import Login from './pages/Login';
import Register from './pages/Register';
import Settings from './pages/Settings';
import ProtectedRoute from './components/ProtectedRoute';
import { useAppStore } from './store/useAppStore';


// 1. Helper component to keep logged-in users OUT of auth pages
const PublicRoute = () => {
  const { token } = useAppStore();
  // If they have a token, boot them to the workspace. Otherwise, let them see the page.
  return token ? <Navigate to="/workspace" replace /> : <Outlet />;
};

export default function App() {
  const { token, theme } = useAppStore();

  // Inject the dark class into the DOM when the theme changes
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  return (
    <Router>
      <Toaster 
        position="top-center" 
        toastOptions={{
          duration: 4000,
          style: {
            background: theme === 'dark' ? '#333' : '#fff',
            color: theme === 'dark' ? '#fff' : '#333',
            border: theme === 'dark' ? '1px solid #444' : '1px solid #eaeaea'
          },
        }} 
      />
      <Routes>
        {/* Auth Routes - Wrapped in our new PublicRoute */}
        <Route element={<PublicRoute />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Route>
        
        {/* Protected Application Routes - Managed by your existing component */}
        <Route element={<ProtectedRoute />}>
          <Route path="/workspace" element={<Workspace />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        
        {/* Default redirect: dynamically route based on auth status */}
        <Route 
          path="/" 
          element={<Navigate to={token ? "/workspace" : "/login"} replace />} 
        />
      </Routes>
    </Router>
  );
}