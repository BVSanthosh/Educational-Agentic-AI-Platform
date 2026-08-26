import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { User, Lock, ArrowRight } from 'lucide-react'; 
import { useAppStore } from '../store/useAppStore';
import toast from 'react-hot-toast'; 
import { API_BASE_URL } from '../api/config'

export default function Login() {
  const navigate = useNavigate();
  const { setToken, fetchSpaces } = useAppStore();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Check for Google OAuth code immediately on component mount
  const queryParams = new URLSearchParams(window.location.search);
  const code = queryParams.get('code');

  useEffect(() => {
    if (code) {
      const handleGoogleCallback = async () => {
        try {
          const response = await fetch(`${API_BASE_URL}/api/auth/google`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ code: code }),
          });

          if (!response.ok) {
            throw new Error('Google authentication failed');
          }

          const data = await response.json();
          
          // Save the access token and update stores
          setToken(data.access_token);
          await fetchSpaces();
          
          toast.success('Successfully signed in with Google!');
          // Clear query params from URL and navigate smoothly
          navigate('/workspace', { replace: true });
        } catch (err) {
          console.error("Google login error:", err);
          toast.error("Failed to sign in with Google. Please try again.");
          window.history.replaceState({}, document.title, window.location.pathname);
        }
      };

      handleGoogleCallback();
    }
  }, [code, navigate, setToken, fetchSpaces]);

  // If code is present in URL, render a clean loading screen immediately to prevent any login flash
  if (code) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col items-center justify-center text-gray-800 dark:text-gray-200 transition-colors">
        <div className="w-12 h-12 bg-blue-600 dark:bg-blue-500 rounded-xl flex items-center justify-center shadow-sm mb-4 animate-pulse">
          <span className="text-white font-bold text-2xl">E</span>
        </div>
        <p className="text-sm font-medium animate-pulse">Logging you in with Google...</p>
      </div>
    );
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }
      
      // Save the access_token to Zustand and localStorage
      setToken(data.access_token);
      
      toast.success('Welcome back!');
      // Navigate to the secure workspace
      navigate('/workspace');

    } catch (err) {
      console.error('Request error:', err);
      if (err instanceof Error) {
        toast.error(err.message);
      } else {
        toast.error('Failed to connect to the server');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8 transition-colors duration-200">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        
        {/* The Unified Box */}
        <div className="bg-white dark:bg-gray-900 py-10 px-4 shadow-xl shadow-gray-200/50 dark:shadow-none sm:rounded-2xl sm:px-10 border border-gray-100 dark:border-gray-800 transition-colors duration-200">
          
          {/* --- Headers --- */}
          <div className="flex justify-center">
            <div className="w-12 h-12 bg-blue-600 dark:bg-blue-500 rounded-xl flex items-center justify-center shadow-sm transition-colors">
              <span className="text-white font-bold text-2xl">E</span>
            </div>
          </div>
          <h2 className="mt-5 text-center text-2xl font-extrabold text-gray-900 dark:text-gray-100 tracking-tight transition-colors">
            Sign in to EduAgent
          </h2>
          <p className="mt-2 mb-8 text-center text-sm text-gray-600 dark:text-gray-400 transition-colors">
            Or{' '}
            <Link to="/register" className="font-medium text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300 transition-colors">
              create a new account
            </Link>
          </p>

          {/* --- Form --- */}
          <form className="space-y-6" onSubmit={handleLogin}>
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 dark:text-gray-300 transition-colors">
                Username
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <User className="h-5 w-5 text-gray-400 dark:text-gray-500" />
                </div>
                <input
                  id="username"
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 transition-colors"
                  placeholder="johndoe123"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 transition-colors">
                Password
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400 dark:text-gray-500" />
                </div>
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 transition-colors"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center items-center gap-2 py-2.5 px-4 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-gray-900 focus:ring-blue-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Signing in...' : 'Sign in'}
                {!isLoading && <ArrowRight size={16} />}
              </button>
            </div>
          </form>
          
          {/* --- Google OAuth Button --- */}
          <div className="mt-6">
            <button
              type="button"
              onClick={() => {
                const googleClientId = "431217733922-egs0645uss1bf7pbhlt85u22udrn7joh.apps.googleusercontent.com"; 
                const redirectUri = window.location.origin + "/login"; 
                const scope = "openid email profile";
                const url = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${googleClientId}&redirect_uri=${redirectUri}&response_type=code&scope=${scope}`;
                window.location.href = url;
              }}
              className="w-full flex justify-center items-center gap-3 py-2.5 px-4 border border-gray-300 dark:border-gray-700 rounded-xl shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-gray-900 focus:ring-blue-500 transition-all"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
              </svg>
              Continue with Google
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}