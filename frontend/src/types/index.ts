// Define the core tools available in the application
export type ToolType = 'reference' | 'summary' | 'research';

export interface Message {
  id: string;
  sender: 'user' | 'agent';
  content: string;
  createdAt?: number; 
}

// Represents an individual chat/workspace instance
export interface Session {
  id: string;
  title: string;
  createdAt: number;
  // Summary tool starts in an 'upload' state before moving to 'chat'
  state?: 'upload' | 'chat';
  messages?: Message[]; 
}

// The shape of our global application state
export interface AppState {
  activeTool: ToolType;
  activeSessionId: string | null;
  
  // Track dynamic sessions for the tools that support them
  sessions: {
    summary: Session[];
    research: Session[];
  };
  
  // UI State
  isLeftPanelOpen: boolean;
  isRightPanelOpen: boolean;
  isNewSpaceModalOpen: boolean;

  // Global Reference Tool State
  referenceSpaceId: string | null;
  ensureReferenceSpaceExists: () => Promise<string | null>;
}