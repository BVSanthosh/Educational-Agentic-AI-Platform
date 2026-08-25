import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Trash2, AlertTriangle } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import toast from 'react-hot-toast'; 

export default function Settings() {
  const navigate = useNavigate();
  const { token, logout } = useAppStore();
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteAccount = async () => {
    // 1. Prompt the user to confirm this destructive action
    const confirmed = window.confirm(
      "Are you absolutely sure you want to delete your account? This action cannot be undone and will permanently delete all your spaces, documents, and chat history."
    );
    
    if (!confirmed) return;
    
    setIsDeleting(true);
    
    try {
      // 2. Call the backend API to delete the user
      const response = await fetch('http://localhost:8000/api/auth/delete-account', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete account');
      }
      
      // 3. Clear Zustand state, clear localStorage, and kick to login
      logout();
      toast.success('Your account has been permanently deleted.');
      navigate('/login');
    } catch (err) {
      if (err instanceof Error) {
        toast.error(err.message);
      } else {
        toast.error('An error occurred while deleting your account.');
      }
      
      setIsDeleting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col transition-colors duration-200">
      {/* Header */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-6 py-4 flex items-center gap-4 transition-colors duration-200">
        <button 
          onClick={() => navigate('/workspace')}
          className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
        >
          <ArrowLeft size={20} />
        </button>
        <h1 className="text-xl font-semibold">Account Settings</h1>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-3xl w-full mx-auto py-12 px-6">
        <div className="bg-white dark:bg-gray-900 border border-red-200 dark:border-red-900/50 rounded-2xl shadow-sm p-6 md:p-8 transition-colors duration-200">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-red-50 dark:bg-red-950/50 text-red-600 dark:text-red-400 rounded-full shrink-0 transition-colors">
              <AlertTriangle size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2 transition-colors">Delete Account</h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6 leading-relaxed transition-colors">
                Permanently delete your account and all of its associated data from the EduAgent platform. 
                This includes all of your workspaces, uploaded documents, and chat histories. 
                <strong className="text-gray-900 dark:text-gray-200 transition-colors"> This action is not reversible.</strong>
              </p>

              <button
                onClick={handleDeleteAccount}
                disabled={isDeleting}
                className="flex items-center gap-2 bg-red-600 dark:bg-red-600 hover:bg-red-700 dark:hover:bg-red-500 text-white px-5 py-2.5 rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Trash2 size={18} />
                {isDeleting ? 'Deleting Account...' : 'Delete My Account'}
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}