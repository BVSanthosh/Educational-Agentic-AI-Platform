import { useState, useEffect, useRef } from 'react';
import { useAppStore } from '../store/useAppStore';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function RightPanel() {
  const { 
    isRightPanelOpen, 
    setRightPanelOpen, 
    activeDocumentId, 
    setActiveDocument, 
    activeChat, 
    token,
    activeTool
  } = useAppStore();
  
  const [content, setContent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [panelWidth, setPanelWidth] = useState(450); 
  
  const isResizing = useRef(false);

  // 1. Fetch document content ONLY when a specific document is clicked
  useEffect(() => {
    // If no document is selected, just do nothing. The UI handles hiding the content.
    if (!activeDocumentId || !token) return;

    const fetchContent = async () => {
      setIsLoading(true);
      setContent(null); // Clear the OLD content right before fetching the new one
      
      try {
        const res = await fetch(`http://localhost:8000/api/documents/${activeDocumentId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (res.ok) {
          const data = await res.json();
          setContent(data.content);
        }
      } catch (error) {
        console.error("Failed to load document", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchContent();
  }, [activeDocumentId, token]);

  // 2. Resizing Logic
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing.current) return;
      const newWidth = window.innerWidth - e.clientX;
      if (newWidth > 300 && newWidth < 1000) {
        setPanelWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      isResizing.current = false;
      document.body.style.cursor = 'default';
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const handleDownload = async (docId: string, filename: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevents the main row click from firing (so it doesn't open the viewer)
    
    if (!token) return;
    
    try {
      const res = await fetch(`http://localhost:8000/api/documents/${docId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const data = await res.json();
        
        // Convert the markdown string into a downloadable Blob
        const blob = new Blob([data.content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        
        // Programmatically trigger the browser download
        const a = document.createElement('a');
        a.href = url;
        a.download = filename; // e.g., "Research_Report.md"
        document.body.appendChild(a);
        a.click();
        
        // Clean up
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error("Failed to download document", error);
    }
  };

  if (!isRightPanelOpen) return null;

  const listTitle = activeTool === 'summary' ? 'Generated Summary' : 'Generated Report';
  const documents = activeChat?.documents || [];
  console.log(documents)

  return (
    <div 
      className="flex h-full bg-white border-l border-gray-200 shadow-xl relative"
      style={{ width: panelWidth }}
    >
      {/* Drag Handle */}
      <div 
        className="absolute left-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-blue-400 hover:bg-opacity-50 transition-colors z-10"
        onMouseDown={(e) => {
          e.preventDefault();
          isResizing.current = true;
          document.body.style.cursor = 'col-resize';
        }}
      />

      <div className="flex-1 overflow-y-auto p-6 ml-2 flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center mb-6 pb-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            {/* Show Back Button only if viewing a document */}
            {activeDocumentId && (
              <button 
                onClick={() => setActiveDocument(null)}
                className="text-sm px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 transition-colors"
              >
                ← Back
              </button>
            )}
            <h2 className="text-lg font-semibold text-gray-800">
              {activeDocumentId ? "Document Viewer" : listTitle}
            </h2>
          </div>
          <button 
            onClick={() => setRightPanelOpen(false)}
            className="text-gray-400 hover:text-gray-800 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* View 1: List View (No document selected) */}
        {!activeDocumentId && (
          <div className="flex flex-col gap-3">
            {documents.length === 0 ? (
              <p className="text-gray-500 text-sm">No documents found for this session.</p>
            ) : (
              documents.map((doc) => (
                <div
                  key={doc.id}
                  onClick={() => setActiveDocument(doc.id)}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-xl hover:border-blue-400 hover:bg-blue-50 transition-all group cursor-pointer"
                >
                  {/* Left Side: Icon and Title */}
                  <div className="flex items-center gap-3">
                    <span className="text-2xl group-hover:scale-110 transition-transform">📄</span>
                    <span className="text-sm font-medium text-gray-700 group-hover:text-blue-700">
                      {doc.filename.replace('.md', '').replace(/_/g, ' ')}
                    </span>
                  </div>

                  {/* Right Side: Download Icon Button */}
                  <button
                    onClick={(e) => handleDownload(doc.id, doc.filename, e)}
                    className="p-2 text-gray-400 hover:text-blue-700 hover:bg-blue-100 rounded-lg transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                    title="Download Markdown"
                  >
                    <svg 
                      xmlns="http://www.w3.org/2000/svg" 
                      fill="none" 
                      viewBox="0 0 24 24" 
                      strokeWidth={2} 
                      stroke="currentColor" 
                      className="w-5 h-5"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                    </svg>
                  </button>
                </div>
              ))
            )}
          </div>
        )}

        {/* View 2: Content View (Document is selected and fetching/fetched) */}
        {activeDocumentId && (
          <div className="flex-1">
            {isLoading ? (
              <div className="animate-pulse flex flex-col gap-4">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="h-4 bg-gray-200 rounded w-full"></div>
                <div className="h-4 bg-gray-200 rounded w-5/6"></div>
                <div className="h-4 bg-gray-200 rounded w-full mt-4"></div>
                <div className="h-4 bg-gray-200 rounded w-4/5"></div>
              </div>
            ) : (
              <div className="prose prose-sm md:prose-base max-w-none text-gray-800">
                {content ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {content}
                  </ReactMarkdown>
                ) : (
                  <p className="text-red-500">Failed to load content.</p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}