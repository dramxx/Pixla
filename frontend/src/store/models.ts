import { create } from "zustand";
import { ModelConfig, LoRAConfig } from "@/lib/types";
import { modelsApi, lorasApi } from "@/lib/api";

interface ModelsStore {
  models: ModelConfig[];
  loras: LoRAConfig[];
  currentModel: ModelConfig | null;
  currentLoras: LoRAConfig[];
  isLoading: boolean;
  error: string | null;

  fetchModels: () => Promise<void>;
  fetchLoras: () => Promise<void>;
  setCurrentModel: (model: ModelConfig) => void;
  toggleLora: (lora: LoRAConfig) => void;
  setLoraScale: (loraId: string, scale: number) => void;
}

export const useModelsStore = create<ModelsStore>((set, get) => ({
  models: [],
  loras: [],
  currentModel: null,
  currentLoras: [],
  isLoading: false,
  error: null,

  fetchModels: async () => {
    set({ isLoading: true, error: null });
    try {
      const models = await modelsApi.list();
      const currentModel = models.length > 0 ? models[0] : null;
      set({ 
        models, 
        currentModel,
        isLoading: false 
      });
    } catch (error) {
      set({ error: String(error), isLoading: false });
    }
  },

  fetchLoras: async () => {
    try {
      const loras = await lorasApi.list();
      set({ loras });
    } catch (error) {
      console.error("Failed to fetch LoRAs:", error);
    }
  },

  setCurrentModel: (model) => set({ currentModel: model }),

  toggleLora: (lora) => {
    const { currentLoras } = get();
    const isEnabled = currentLoras.some((l) => l.id === lora.id);
    
    if (isEnabled) {
      set({ 
        currentLoras: currentLoras.filter((l) => l.id !== lora.id) 
      });
    } else {
      set({ 
        currentLoras: [...currentLoras, { ...lora, scale: 1.0 }] 
      });
    }
  },

  setLoraScale: (loraId, scale) => {
    const { currentLoras } = get();
    set({
      currentLoras: currentLoras.map((l) => 
        l.id === loraId ? { ...l, scale } : l
      ),
    });
  },
}));
