import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store/useAppStore';
import { 
  Plus, 
  BookOpen, 
  MessageSquare, 
  FileText, 
  ChevronRight, 
  ChevronDown,
  MessageCircle,
  LogOut,
  Trash2,
  Settings as SettingsIcon,
  Sun,
  Moon
} from 'lucide-react';
import toast from 'react-hot-toast';
import ConfirmationModal from './ConfirmationModal';

interface SpaceToDelete {
  id: string;
  tool: 'summary' | 'research';
}
 
export default function LeftNavigation() {
  const navigate = useNavigate();

  const { 
    activeTool, 
    setActiveTool, 
    activeSessionId, 
    setActiveSessionId, 
    sessions, 
    setNewSpaceModalOpen,
    logout,
    deleteSpace,
    theme,          
    toggleTheme
  } = useAppStore();

  const [spaceToDelete, setSpaceToDelete] = useState<SpaceToDelete | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Local state to manage which accordions are open
  const [expanded, setExpanded] = useState({
    summary: true,
    research: true,
  });

  const toggleExpand = (tool: 'summary' | 'research', e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent triggering the parent button's onClick
    setExpanded(prev => ({ ...prev, [tool]: !prev[tool] }));
  };

  // Always clear the active session when clicking a main tool category!
  const handleToolSelect = (tool: 'reference' | 'summary' | 'research') => {
    setActiveTool(tool);
    setActiveSessionId(null); 
  };

  const handleSessionSelect = (tool: 'summary' | 'research', sessionId: string) => {
    setActiveTool(tool);
    setActiveSessionId(sessionId);
  };

  const handleDeleteClick = (id: string, tool: 'summary' | 'research', e: React.MouseEvent) => {
    e.stopPropagation();
    setSpaceToDelete({ id, tool });
  };

  const handleConfirmDelete = async () => {
    if (!spaceToDelete) return;

    setIsDeleting(true);
    try {
      await deleteSpace(spaceToDelete.id, spaceToDelete.tool);
      toast.success('Space deleted successfully');
    } catch {
      toast.error('Failed to delete space');
    } finally {
      setIsDeleting(false);
      setSpaceToDelete(null);
    }
  };

  const handleLogout = async () => {
    try {
      // Hit the backend logout endpoint to clear the HttpOnly cookie
      await fetch('http://localhost:8000/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch {
      toast.error('Logout error');
    } finally {
      // Clear local Zustand state & localStorage, then redirect
      logout();
      navigate('/login');
    }
  };

  return (
    <>
      <div className="flex flex-col h-full w-full">
        
        {/* Create New Space Button - Pinned at the top */}
        <div className="mb-6">
          <button 
            onClick={() => setNewSpaceModalOpen(true)}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2.5 px-4 rounded-lg font-medium transition-colors shadow-sm"
          >
            <Plus size={18} />
            Create New Space
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 space-y-4">
          
          {/* 1. Reference Generation (Static) */}
          <div>
            <button
              onClick={() => handleToolSelect('reference')}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                activeTool === 'reference' 
                  ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 font-medium' 
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
            >
              <BookOpen size={18} className={activeTool === 'reference' ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'} />
              <span>Reference Generation</span>
            </button>
          </div>

          {/* 2. Summarise & QnA (Collapsible) */}
          <div>
            <button
              onClick={() => handleToolSelect('summary')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors group ${
                activeTool === 'summary' && !activeSessionId
                  ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 font-medium' 
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
            > 
              <div className="flex items-center gap-3">
                <MessageSquare size={18} className={activeTool === 'summary' && !activeSessionId ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'} />
                <span>Document Summary</span>
              </div>
              <div 
                onClick={(e) => toggleExpand('summary', e)}
                className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors"
              >
                {expanded.summary ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              </div>
            </button>
            
            {/* Summary Sessions List */}
            {expanded.summary && sessions.summary.length > 0 && (
              <div className="mt-1 flex flex-col gap-1 ml-4 pl-4 border-l border-gray-200 dark:border-gray-800">
                {sessions.summary.map((session) => (
                  <div key={session.id} className="group relative flex items-center rounded-md">
                    <button
                      onClick={() => handleSessionSelect('summary', session.id)}
                      className={`flex-1 flex items-center gap-2 px-3 py-1.5 pr-8 rounded-md text-sm transition-colors text-left truncate ${
                        activeSessionId === session.id
                          ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 font-medium'
                          : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-200'
                      }`}
                    >
                      <MessageCircle size={14} className="shrink-0" />
                      <span className="truncate">{session.title}</span>
                    </button>
                    
                    {/* Delete Button */}
                    <button
                      onClick={(e) => handleDeleteClick(session.id, 'summary', e)}
                      className="absolute right-1 p-1 text-gray-400 dark:text-gray-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/50 rounded opacity-0 group-hover:opacity-100 transition-all z-10"
                      title="Delete Space"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 3. Research Report (Collapsible) */}
          <div>
            <button
              onClick={() => handleToolSelect('research')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors group ${
                activeTool === 'research' && !activeSessionId
                  ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 font-medium' 
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
            >
              <div className="flex items-center gap-3">
                <FileText size={18} className={activeTool === 'research' && !activeSessionId ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'} />
                <span>Research Report</span>
              </div>
              <div 
                onClick={(e) => toggleExpand('research', e)}
                className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors"
              >
                {expanded.research ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              </div>
            </button>

            {/* Research Sessions List */}
            {expanded.research && sessions.research.length > 0 && (
              <div className="mt-1 flex flex-col gap-1 ml-4 pl-4 border-l border-gray-200 dark:border-gray-800">
                {sessions.research.map((session) => (
                  <div key={session.id} className="group relative flex items-center rounded-md">
                    <button
                      onClick={() => handleSessionSelect('research', session.id)}
                      className={`flex-1 flex items-center gap-2 px-3 py-1.5 pr-8 rounded-md text-sm transition-colors text-left truncate ${
                        activeSessionId === session.id
                          ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 font-medium'
                          : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-200'
                      }`}
                    >
                      <MessageCircle size={14} className="shrink-0" />
                      <span className="truncate">{session.title}</span>
                    </button>
                    
                    {/* Delete Button */}
                    <button
                      onClick={(e) => handleDeleteClick(session.id, 'research', e)}
                      className="absolute right-1 p-1 text-gray-400 dark:text-gray-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/50 rounded opacity-0 group-hover:opacity-100 transition-all z-10"
                      title="Delete Space"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </nav>

        {/* Bottom Actions */}
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-800 space-y-1"> 
          <button
            onClick={toggleTheme}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <div className="flex items-center gap-3">
              {theme === 'dark' ? <Moon size={18} className="text-blue-400" /> : <Sun size={18} className="text-orange-400" />}
              <span>{theme === 'dark' ? 'Dark Mode' : 'Light Mode'}</span>
            </div>
            <div className={`w-8 h-4 rounded-full p-0.5 transition-colors ${theme === 'dark' ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-700'}`}>
              <div className={`w-3 h-3 bg-white rounded-full transition-transform duration-300 ${theme === 'dark' ? 'translate-x-4' : 'translate-x-0'}`} />
            </div>
          </button>

          <button
            onClick={() => navigate('/settings')}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <SettingsIcon size={18} className="text-gray-500 dark:text-gray-400" />
            <span>Settings</span>
          </button>
            
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/50 transition-colors"
          >
            <LogOut size={18} className="text-red-500 dark:text-red-400" />
            <span>Log out</span>
          </button>
        </div>
      </div>

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={Boolean(spaceToDelete)}
        title="Delete Space"
        message="Are you sure you want to delete this space? All associated documents and chat history will be permanently removed."
        confirmLabel="Delete Space"
        isLoading={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setSpaceToDelete(null)}
      />
    </>
  );
}