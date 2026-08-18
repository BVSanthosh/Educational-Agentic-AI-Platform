import { create } from 'zustand';
import type { AppState, ToolType, Session, Message } from '../types';

interface AppStore extends AppState {
  token: string | null;
  setToken: (token: string | null) => void; 
  logout: () => void;
  setActiveTool: (tool: ToolType) => void;
  setActiveSessionId: (id: string | null) => void;
  setLeftPanelOpen: (isOpen: boolean) => void;
  setRightPanelOpen: (isOpen: boolean) => void;
  setNewSpaceModalOpen: (isOpen: boolean) => void;
  createNewSpace: (tool: 'summary' | 'research', name: string) => Promise<void>;
  updateSessionState: (tool: 'summary' | 'research', id: string, newState: 'upload' | 'chat') => void;
  addMessage: (tool: 'summary' | 'research', sessionId: string, message: Message) => void;
}
 
export const useAppStore = create<AppStore>((set, get) => ({
  token: localStorage.getItem('token'),
  activeTool: 'reference',
  referenceSpaceId: null,
  activeSessionId: null,
  sessions: {
    summary: [],
    research: [],
  },
  isLeftPanelOpen: true,
  isRightPanelOpen: false,
  isNewSpaceModalOpen: false,

  // --- Auth Actions ---
  setToken: (token) => {
    if (token) {
      localStorage.setItem('token', token);
    } else {
      localStorage.removeItem('token');
    }
    set({ token });
  },
  
  logout: () => {
    localStorage.removeItem('token');
    set({ 
      token: null, 
      activeSessionId: null,
      activeTool: 'reference', // Reset UI state on logout
      sessions: { summary: [], research: [] } 
    });
  },
  // --------------------
  
  setActiveTool: (tool) => set({ activeTool: tool }),
  setActiveSessionId: (id) => set({ activeSessionId: id }),
  setLeftPanelOpen: (isOpen) => set({ isLeftPanelOpen: isOpen }),
  setRightPanelOpen: (isOpen) => set({ isRightPanelOpen: isOpen }),
  setNewSpaceModalOpen: (isOpen) => set({ isNewSpaceModalOpen: isOpen }),

  createNewSpace: async (tool, name) => {
    try {
      const response = await fetch('http://localhost:8000/api/space/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // Adjust these keys if your Pydantic schema expects different names
        body: JSON.stringify({ tool: tool, title: name }) 
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      const newSession: Session = {
        id: data.id,
        title: data.name, // Map backend 'name' to frontend 'title'
        createdAt: data.created_at ? new Date(data.created_at).getTime() : Date.now(),
        state: tool === 'summary' ? 'upload' : 'chat', 
        messages: [],
      };

      // Update the state with the confirmed backend data
      set((state) => ({
        sessions: {
          ...state.sessions,
          [tool]: [newSession, ...state.sessions[tool]],
        },
        activeTool: tool,
        activeSessionId: newSession.id,
        isNewSpaceModalOpen: false,
      }));

    } catch (error) {
      console.error("Failed to create space in backend:", error);
    }
  }, 

  ensureReferenceSpaceExists: async () => {
    const state = get();
    if (state.referenceSpaceId) return state.referenceSpaceId;

    try {
      // 1. Try to fetch all spaces to see if one already exists for this user
      // (Assumes you have a GET /space/ endpoint to retrieve user spaces)
      const fetchRes = await fetch('http://localhost:8000/api/space/?tool=reference', {
        headers: { 'Authorization': `Bearer ${state.token}` }
      });

      if (fetchRes.ok) {
        const spaces = await fetchRes.json();
        // Look for the singleton reference space
        const existingRef = spaces.find((s: { id: string; name: string, tool: string, created_at: string }) => s.tool === 'reference');
        if (existingRef) {
          set({ referenceSpaceId: existingRef.id });
          return existingRef.id;
        }
      }

      // 2. If it doesn't exist, silently create it!
      const createRes = await fetch('http://localhost:8000/api/space/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${state.token}`
        },
        body: JSON.stringify({ tool: 'reference', name: 'Global Reference' })
      });

      if (!createRes.ok) throw new Error("Failed to create reference space");
      const newSpace = await createRes.json();

      set({ referenceSpaceId: newSpace.id });
      return newSpace.id;

    } catch (error) {
      console.error("Reference space initialization failed:", error);
      return null;
    }
  },

  updateSessionState: (tool, id, newState) => set((state) => ({
    sessions: {
      ...state.sessions,
      [tool]: state.sessions[tool].map(session => 
        session.id === id ? { ...session, state: newState } : session
      )
    }
  })),

  addMessage: (tool, sessionId, message) => set((state) => ({
    sessions: {
      ...state.sessions,
      [tool]: state.sessions[tool].map((session) => 
        session.id === sessionId 
          ? { ...session, messages: [...(session.messages || []), message] }
          : session
      ),
    },
  })),
}));