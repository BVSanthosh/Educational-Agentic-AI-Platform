import { useAppStore } from '../store/useAppStore';
import { X, Download, FileText, File } from 'lucide-react';

export default function RightContextPanel() {
  const { activeTool, activeSessionId, isRightPanelOpen, setRightPanelOpen, sessions } = useAppStore();

  // If panel is closed or reference tool is active, don't render anything
  if (!isRightPanelOpen || activeTool === 'reference') return null;

  // Find the active session to display relevant data
  const activeSession = activeSessionId 
    ? sessions[activeTool].find((s) => s.id === activeSessionId)
    : null;

  const handleDownload = () => {
    if (!activeSession) return;
    console.log(`Triggering download for: ${activeSession.title}`);
    // You will wire this up to your FastAPI backend later to fetch the blob
  };

  return (
    <aside className="w-80 border-l border-gray-200 bg-gray-50 flex flex-col shrink-0">
      
      {/* Header */}
      <div className="h-16 px-4 border-b border-gray-200 flex justify-between items-center bg-white shrink-0">
        <div className="flex items-center gap-2">
          <FileText size={18} className="text-blue-600" />
          <h3 className="font-semibold text-gray-800">
            {activeTool === 'summary' ? 'Source Document' : 'Research Report'}
          </h3>
        </div>
        <button 
          onClick={() => setRightPanelOpen(false)}
          className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
          title="Close Panel"
        >
          <X size={18} />
        </button>
      </div>
      
      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col">
        
        {/* State: No Session or Still Uploading */}
        {!activeSession || activeSession.state === 'upload' ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center opacity-50">
            <File size={32} className="mb-2 text-gray-400" />
            <p className="text-sm text-gray-500">
              {activeSession?.state === 'upload' 
                ? 'Upload a document to view it here.' 
                : 'Select a space to view its document.'}
            </p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
            
            {/* Document Toolbar */}
            <div className="p-2 border-b border-gray-100 flex justify-between items-center bg-gray-50">
              <span className="text-xs font-medium text-gray-500 truncate px-2">
                {activeSession.title}
              </span>
              <button
                onClick={handleDownload}
                className="text-gray-500 hover:text-blue-600 transition-colors p-1.5 rounded hover:bg-gray-200 flex items-center gap-1"
                title="Download"
              >
                <Download size={14} />
              </button>
            </div>

            {/* Document Viewer Mockup */}
            <div className="p-4 text-sm text-gray-700 space-y-4 overflow-y-auto flex-1">
              {activeTool === 'summary' ? (
                // PDF Viewer Placeholder
                <div className="space-y-3">
                  <div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse"></div>
                  <div className="h-4 bg-gray-200 rounded w-full animate-pulse"></div>
                  <div className="h-4 bg-gray-200 rounded w-5/6 animate-pulse"></div>
                  <div className="h-32 bg-gray-100 rounded mt-4 border border-dashed border-gray-300 flex items-center justify-center">
                    <span className="text-gray-400 text-xs">PDF Render Canvas</span>
                  </div>
                </div>
              ) : (
                // Research Report Placeholder
                <div className="prose prose-sm">
                  <h4 className="font-bold text-lg border-b pb-2 mb-3">Executive Summary</h4>
                  <p className="mb-2">This is a structural mockup of the generated research report.</p>
                  <p className="text-gray-500 italic">Detailed analysis, structured data, and citations will stream into this view as your FastAPI backend compiles the information.</p>
                </div>
              )}
            </div>

          </div>
        )}
      </div>
    </aside>
  );
}