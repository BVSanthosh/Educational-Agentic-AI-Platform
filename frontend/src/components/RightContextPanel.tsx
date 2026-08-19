import { useEffect, useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { X, FileText, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export default function RightPanel() {
  const { isRightPanelOpen, setRightPanelOpen, activeChat, token } = useAppStore();
  
  const [documentContent, setDocumentContent] = useState<string | null>(null);
  const [documentTitle, setDocumentTitle] = useState<string>("Research Report");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const fetchDocument = async () => {
      if (!activeChat?.activeDocumentId) return;
      
      setIsLoading(true);
      try {
        const res = await fetch(`http://localhost:8000/api/documents/${activeChat.activeDocumentId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (res.ok) {
          const data = await res.json();
          // Maps directly to your FastAPI DocumentResponse schema
          setDocumentContent(data.content);
          if (data.filename) {
            // Clean up the filename for display (e.g., remove the .md extension)
            setDocumentTitle(data.filename.replace('.md', '').replace(/_/g, ' '));
          }
        }
      } catch (err) {
        console.error("Failed to load document", err);
      } finally {
        setIsLoading(false);
      }
    };

    if (isRightPanelOpen && activeChat?.activeDocumentId) {
      fetchDocument();
    }
  }, [activeChat?.activeDocumentId, isRightPanelOpen, token]);

  if (!isRightPanelOpen) return null;

  return (
    <div className="w-96 border-l border-gray-200 bg-white flex flex-col h-full shadow-xl">
      <div className="flex items-center justify-between p-4 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center gap-2 text-gray-800 font-semibold truncate pr-4">
          <FileText size={18} className="text-blue-600 shrink-0" />
          <span className="truncate" title={documentTitle}>{documentTitle}</span>
        </div>
        <button 
          onClick={() => setRightPanelOpen(false)}
          className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-200 rounded-lg transition-colors shrink-0"
        >
          <X size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 space-y-3">
            <Loader2 size={24} className="animate-spin text-blue-500" />
            <span className="text-sm">Loading document from secure storage...</span>
          </div>
        ) : documentContent ? (
          <div className="prose prose-sm prose-blue max-w-none">
            <ReactMarkdown>{documentContent}</ReactMarkdown>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 text-sm text-center">
            No document generated yet. Ask the Deep Research agent to compile a report!
          </div>
        )}
      </div>
    </div>
  );
}