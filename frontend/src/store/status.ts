import { create } from 'zustand';

interface SystemStatus {
  isReady: boolean;
  loading: boolean;
  checkStatus: () => Promise<void>;
}

export const useSystemStatusStore = create<SystemStatus>((set) => ({
  isReady: false,
  loading: true,

  checkStatus: async () => {
    set({ loading: true });
    try {
      const response = await fetch('/api/models');
      if (!response.ok) {
        throw new Error('Failed to fetch models');
      }
      const models = await response.json();
      const hasModels = Array.isArray(models) && models.length > 0;
      
      // If we got a valid response but no models, still consider it "ready" 
      // (just means no model installed, but system is functional)
      set({ 
        isReady: hasModels,
        loading: false 
      });
    } catch (e) {
      console.error('Status check failed:', e);
      set({ 
        isReady: false, 
        loading: false 
      });
    }
  },
}));
