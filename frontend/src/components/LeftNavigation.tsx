import { useState, useEffect } from 'react';
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
  Settings as SettingsIcon,
  LogOut,
  Trash2
} from 'lucide-react';
 
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
    fetchSpaces,
    token,
    deleteSpace
  } = useAppStore();

  // Local state to manage which accordions are open
  const [expanded, setExpanded] = useState({
    summary: true,
    research: true,
  });

  useEffect(() => {
    // Only attempt to fetch if the user is authenticated
    if (token) {
      fetchSpaces();
    }
  }, [token, fetchSpaces]);

  const toggleExpand = (tool: 'summary' | 'research', e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent triggering the parent button's onClick
    setExpanded(prev => ({ ...prev, [tool]: !prev[tool] }));
  };

  const handleToolSelect = (tool: 'reference' | 'summary' | 'research') => {
    setActiveTool(tool);
    // When switching to reference, clear the active session since it's a static tool
    if (tool === 'reference') {
      setActiveSessionId(null);
    }
  };

  const handleSessionSelect = (tool: 'summary' | 'research', sessionId: string) => {
    setActiveTool(tool);
    setActiveSessionId(sessionId);
  };

  const handleLogout = async () => {
    try {
      // Hit the backend logout endpoint to clear the HttpOnly cookie
      await fetch('http://localhost:8000/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local Zustand state & localStorage, then redirect
      logout();
      navigate('/login');
    }
  };

  return (
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
                ? 'bg-blue-50 text-blue-700 font-medium' 
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            <BookOpen size={18} className={activeTool === 'reference' ? 'text-blue-600' : 'text-gray-500'} />
            <span>Reference Generation</span>
          </button>
        </div>

        {/* 2. Summarise & QnA (Collapsible) */}
        <div>
          <button
            onClick={() => handleToolSelect('summary')}
            className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors group ${
              activeTool === 'summary' && !activeSessionId
                ? 'bg-blue-50 text-blue-700 font-medium' 
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            <div className="flex items-center gap-3">
              <MessageSquare size={18} className={activeTool === 'summary' ? 'text-blue-600' : 'text-gray-500'} />
              <span>Document Summary</span>
            </div>
            <div 
              onClick={(e) => toggleExpand('summary', e)}
              className="p-1 rounded hover:bg-gray-200 text-gray-400 group-hover:text-gray-600 transition-colors"
            >
              {expanded.summary ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </div>
          </button>
          
          {/* Summary Sessions List */}
          {expanded.summary && sessions.summary.length > 0 && (
            <div className="mt-1 flex flex-col gap-1 ml-4 pl-4 border-l border-gray-200">
              {sessions.summary.map((session) => (
                <div key={session.id} className="group relative flex items-center rounded-md">
                  <button
                    onClick={() => handleSessionSelect('summary', session.id)}
                    className={`flex-1 flex items-center gap-2 px-3 py-1.5 pr-8 rounded-md text-sm transition-colors text-left truncate ${
                      activeSessionId === session.id
                        ? 'bg-blue-50 text-blue-700 font-medium'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`}
                  >
                    <MessageCircle size={14} className="shrink-0" />
                    <span className="truncate">{session.title}</span>
                  </button>
                  
                  {/* Delete Button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteSpace(session.id, 'summary');
                    }}
                    className="absolute right-1 p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded opacity-0 group-hover:opacity-100 transition-all z-10"
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
                ? 'bg-blue-50 text-blue-700 font-medium' 
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            <div className="flex items-center gap-3">
              <FileText size={18} className={activeTool === 'research' ? 'text-blue-600' : 'text-gray-500'} />
              <span>Research Report</span>
            </div>
            <div 
              onClick={(e) => toggleExpand('research', e)}
              className="p-1 rounded hover:bg-gray-200 text-gray-400 group-hover:text-gray-600 transition-colors"
            >
              {expanded.research ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </div>
          </button>

          {/* Research Sessions List */}
          {expanded.research && sessions.research.length > 0 && (
            <div className="mt-1 flex flex-col gap-1 ml-4 pl-4 border-l border-gray-200">
              {sessions.research.map((session) => (
                <div key={session.id} className="group relative flex items-center rounded-md">
                  <button
                    onClick={() => handleSessionSelect('research', session.id)}
                    className={`flex-1 flex items-center gap-2 px-3 py-1.5 pr-8 rounded-md text-sm transition-colors text-left truncate ${
                      activeSessionId === session.id
                        ? 'bg-blue-50 text-blue-700 font-medium'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`}
                  >
                    <MessageCircle size={14} className="shrink-0" />
                    <span className="truncate">{session.title}</span>
                  </button>
                  
                  {/* Delete Button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteSpace(session.id, 'research');
                    }}
                    className="absolute right-1 p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded opacity-0 group-hover:opacity-100 transition-all z-10"
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
      <div className="mt-4 pt-4 border-t border-gray-200 space-y-1">
        <button
          onClick={() => navigate('/settings')}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
        >
          <SettingsIcon size={18} className="text-gray-500" />
          <span>Settings</span>
        </button>
        
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-red-600 hover:bg-red-50 transition-colors"
        >
          <LogOut size={18} className="text-red-500" />
          <span>Log out</span>
        </button>
      </div>
    </div>
  );
}