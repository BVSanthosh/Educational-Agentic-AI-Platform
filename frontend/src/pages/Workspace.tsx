import { Menu, PanelRight } from 'lucide-react'; // Make sure to import these
import { useAppStore } from '../store/useAppStore';
import NewSpaceModal from '../components/NewSpaceModal';
import LeftNavigation from '../components/LeftNavigation';
import CentreWorkspace from '../components/CentreWorkSpace';
import RightContextPanel from '../components/RightContextPanel';

export default function Workspace() {
  const { 
    activeTool, 
    isLeftPanelOpen, 
    setLeftPanelOpen, 
    isRightPanelOpen, 
    setRightPanelOpen 
  } = useAppStore();

  return (
    <div className="flex h-screen w-full overflow-hidden bg-gray-50 text-gray-900">
      
      {/* 1. Left Navigation Panel (Collapsible) */}
      {isLeftPanelOpen && (
        <aside className="w-72 border-r border-gray-200 bg-white flex flex-col shrink-0">
          <div className="p-4 border-b border-gray-200">
            <h1 className="font-bold text-xl tracking-tight text-blue-600">EduAgent AI</h1>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4">
            <LeftNavigation />
          </div>
        </aside>
      )}

      {/* 2. Center Workspace */}
      <main className="flex-1 flex flex-col relative bg-white min-w-0">
        {/* Header with Toggle Buttons */}
        <header className="h-16 px-4 border-b border-gray-100 flex justify-between items-center bg-white shrink-0">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setLeftPanelOpen(!isLeftPanelOpen)}
              className="p-2 -ml-2 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
              title="Toggle Sidebar"
            >
              <Menu size={20} />
            </button>
            <h2 className="font-semibold text-lg capitalize">{activeTool} Space</h2>
          </div>

          <div className="flex items-center">
            {/* Only show Right Panel toggle if NOT in reference tool */}
            {activeTool !== 'reference' && (
              <button 
                onClick={() => setRightPanelOpen(!isRightPanelOpen)}
                className={`p-2 -mr-2 rounded-lg transition-colors ${
                  isRightPanelOpen 
                    ? 'text-blue-600 bg-blue-50' 
                    : 'text-gray-500 hover:text-gray-800 hover:bg-gray-100'
                }`}
                title="Toggle Document Viewer"
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