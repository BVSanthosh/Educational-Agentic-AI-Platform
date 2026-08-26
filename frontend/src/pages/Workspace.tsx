import { useEffect } from 'react';
import { Menu, PanelRight, X } from 'lucide-react'; 
import { useAppStore } from '../store/useAppStore';
import NewSpaceModal from '../components/NewSpaceModal';
import LeftNavigation from '../components/LeftNavigation';
import CentreWorkspace from '../components/CentreWorkSpace';
import RightContextPanel from '../components/RightContextPanel';

export default function Workspace() {
  const { 
    activeTool, 
    activeSessionId,
    sessions,
    isLeftPanelOpen, 
    setLeftPanelOpen, 
    isRightPanelOpen, 
    setRightPanelOpen,
    fetchSpaces, 
    token
  } = useAppStore();

  useEffect(() => {
    if (token) {
      fetchSpaces();
    }
  }, [token, fetchSpaces]);

  // Find the currently active session
  const activeSession = activeTool !== 'reference' && activeSessionId
    ? sessions[activeTool]?.find(s => s.id === activeSessionId)
    : null;

  // Derive the dynamic title for the header
  const getHeaderTitle = () => {
    if (activeTool === 'reference') {
      return 'Reference Generator';
    }
    if (activeSession) {
      return activeSession.title;
    }
    // Fallback if no space is active
    return activeTool === 'summary' ? 'Document Summarizer' : 'Deep Research';
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 transition-colors duration-200">
      
      {/* 1. Left Navigation Panel (Collapsible) */}
      {isLeftPanelOpen && (
        <aside className="w-72 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex flex-col shrink-0 transition-colors duration-200">
          {/* ✅ UPDATED: Flex container with Title and Close 'X' Button */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between transition-colors duration-200">
            <h1 className="font-bold text-xl tracking-tight text-blue-600 dark:text-blue-400 transition-colors">EduAgent</h1>
            <button 
              onClick={() => setLeftPanelOpen(false)}
              className="p-1.5 text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              title="Close Sidebar"
            >
              <X size={20} />
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4">
            <LeftNavigation />
          </div>
        </aside>
      )}

      {/* 2. Center Workspace */}
      <main className="flex-1 flex flex-col relative bg-white dark:bg-gray-900 min-w-0 transition-colors duration-200">
        {/* Header with Toggle Buttons */}
        <header className="h-16 px-4 border-b border-gray-100 dark:border-gray-800/60 flex justify-between items-center bg-white/80 dark:bg-gray-900/80 backdrop-blur-md shrink-0 z-10 transition-colors duration-200">
          <div className="flex items-center gap-3">
            {/* 1. Only show Menu button if left panel is CLOSED */}
            {!isLeftPanelOpen && (
              <button 
                onClick={() => setLeftPanelOpen(true)}
                className="p-2 -ml-2 text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                title="Open Sidebar"
              >
                <Menu size={20} />
              </button>
            )}
            
            {/* Dynamic Title & Tool Badge */}
            <div className="flex items-center gap-2.5">
              <h2 className="font-semibold text-lg text-gray-900 dark:text-gray-100 truncate transition-colors">
                {getHeaderTitle()}
              </h2>
              {activeTool !== 'reference' && activeSession && (
                <span className="text-[11px] font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/40 border border-blue-100 dark:border-blue-800/60 px-2 py-0.5 rounded-full capitalize tracking-wide transition-colors">
                  {activeTool}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center">
            {/* 2. Only show Right Panel toggle if panel is CLOSED and NOT in reference tool */}
            {activeTool !== 'reference' && !isRightPanelOpen && (
              <button 
                onClick={() => setRightPanelOpen(true)}
                className="p-2 -mr-2 text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                title="Open Document Viewer"
              >
                <PanelRight size={20} />
              </button>
            )}
          </div>
        </header>
        
        {/* Chat Interface */}
        <CentreWorkspace />
      </main>

      {/* 3. Right Context Panel */}
      <RightContextPanel />
      
      {/* 4. Global Modal */}
      <NewSpaceModal />
      
    </div>
  );
}