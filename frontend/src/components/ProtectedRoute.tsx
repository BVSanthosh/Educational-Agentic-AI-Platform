import { Navigate, Outlet } from 'react-router-dom';
import { useAppStore } from '../store/useAppStore';

export default function ProtectedRoute() {
  const { token } = useAppStore();

  // If there is no token, redirect to the login page
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  // If authenticated, render the child routes
  return <Outlet />;
}