import { create } from 'zustand';

interface SystemStatus {
  modelAvailable: boolean;
  llmAvailable: boolean;
  storageWritable: boolean;
  loading: boolean;
  checkStatus: () => Promise<void>;
}

export const useSystemStatusStore = create<SystemStatus>((set) => ({
  modelAvailable: false,
  llmAvailable: false,
  storageWritable: false,
  loading: true,

  checkStatus: async () => {
    set({ loading: true });
    try {
      const res = await fetch('/api/models');
      const models = await res.json();
      
      let llmAvailable = false;
      try {
        const health = await fetch('/health');
        const healthData = await health.json();
        llmAvailable = healthData.status === 'ok';
      } catch {
        // LLM not available is fine
      }
      
      set({ 
        modelAvailable: models.length > 0,
        llmAvailable,
        storageWritable: true,
        loading: false 
      });
    } catch {
      set({ 
        modelAvailable: false, 
        llmAvailable: false,
        storageWritable: false,
        loading: false 
      });
    }
  },
}));
