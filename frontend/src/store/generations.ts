import { create } from "zustand";
import { Generation, CreateGenerationRequest } from "@/lib/types";
import { generationsApi } from "@/lib/api";

interface EditRegion {
  x1?: number;
  y1?: number;
  x2?: number;
  y2?: number;
  description?: string;
}

interface GenerationsStore {
  generations: Generation[];
  currentGeneration: Generation | null;
  isLoading: boolean;
  isGenerating: boolean;
  isEditing: boolean;
  error: string | null;

  fetchGenerations: () => Promise<void>;
  createGeneration: (data: CreateGenerationRequest) => Promise<Generation>;
  getGeneration: (id: number) => Promise<void>;
  updateGeneration: (updated: Generation) => void;
  clearCurrentGeneration: () => void;
  setEditingMode: (editing: boolean) => void;
  chatWithGeneration: (id: number, message: string, region?: EditRegion) => Promise<Generation>;
}

export const useGenerationsStore = create<GenerationsStore>((set) => ({
  generations: [],
  currentGeneration: null,
  isLoading: false,
  isGenerating: false,
  isEditing: false,
  error: null,

  fetchGenerations: async () => {
    set({ isLoading: true, error: null });
    try {
      const generations = await generationsApi.list();
      set({ generations, isLoading: false });
    } catch (error) {
      set({ error: String(error), isLoading: false });
    }
  },

  createGeneration: async (data) => {
    set({ isGenerating: true, isEditing: false, error: null });
    try {
      const generation = await generationsApi.create(data);
      set((state) => ({
        generations: [generation, ...state.generations],
        currentGeneration: generation,
        isGenerating: false,
      }));
      return generation;
    } catch (error) {
      set({ error: String(error), isGenerating: false });
      throw error;
    }
  },

  getGeneration: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const generation = await generationsApi.get(id);
      set({ currentGeneration: generation, isLoading: false, isEditing: false });
    } catch (error) {
      set({ error: String(error), isLoading: false });
    }
  },

  clearCurrentGeneration: () => set({ currentGeneration: null, isEditing: false }),

  setEditingMode: (editing) => set({ isEditing: editing }),

  chatWithGeneration: async (id, message, region) => {
    set({ isGenerating: true, error: null });
    try {
      const generation = await generationsApi.chat(id, message, region);
      set((state) => ({
        generations: state.generations.map((g) =>
          g.id === id ? generation : g
        ),
        currentGeneration: generation,
        isGenerating: false,
      }));
      return generation;
    } catch (error) {
      set({ error: String(error), isGenerating: false });
      throw error;
    }
  },

  updateGeneration: (updated) =>
    set((state) => ({
      generations: state.generations.map((g) =>
        g.id === updated.id ? updated : g
      ),
      currentGeneration:
        state.currentGeneration?.id === updated.id
          ? updated
          : state.currentGeneration,
    })),
}));
