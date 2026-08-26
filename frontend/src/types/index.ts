// Define the core tools available in the application
export type ToolType = 'reference' | 'summary' | 'research';
export type UploadStatus = 'chat' | 'upload';

export interface ConfirmationModalProps {
  isOpen: boolean;
  title?: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isLoading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export interface LiveStreamState {
  isProcessing: boolean;
  progress: string | null;
  accumulatedText: string;
  messageId: string;
}

export interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  createdAt?: number; 
}

export interface DocumentMeta {
  id: string;
  filename: string;
}

// Represents an individual chat/workspace instance
export interface Session {
  id: string;
  title: string;
  createdAt: number;
  // Summary tool starts in an 'upload' state before moving to 'chat'
  state: UploadStatus;
}

// Chat Interface
export interface Chat {
  messages: Message[];
  summary?: string;
  status?: string;
  agentProgress?: string | null; 
  documents?: DocumentMeta[];
}

// Reference Interfaces
export interface Resource {
  title: string; 
  url: string;
}

export interface References {
  description: string;
  references: Resource[] | null;
}

// The shape of our global application state
export interface AppState {
  token: string | null;
  theme: 'light' | 'dark';
  activeTool: 'reference' | 'summary' | 'research';
  activeSessionId: string | null;
  activeDocumentId: string | null;
  
  // Track dynamic sessions for the tools that support them
  sessions: {
    summary: Session[];
    research: Session[];
  };
  
  // UI State
  activeChat: Chat | null;
  activeReferences: References | null;
  
  isLeftPanelOpen: boolean;
  isRightPanelOpen: boolean;
  isNewSpaceModalOpen: boolean;

  // Global Reference Tool State
  referenceSpaceId: string | null;

  liveStreams: Record<string, LiveStreamState>;
}