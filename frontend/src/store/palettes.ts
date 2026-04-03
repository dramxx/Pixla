import { create } from "zustand";
import { Palette, CreatePaletteRequest } from "@/lib/types";
import { palettesApi } from "@/lib/api";

interface PalettesStore {
  palettes: Palette[];
  currentPalette: Palette | null;
  isLoading: boolean;
  error: string | null;

  fetchPalettes: () => Promise<void>;
  createPalette: (data: CreatePaletteRequest) => Promise<Palette>;
  updatePalette: (id: number, data: CreatePaletteRequest) => Promise<Palette>;
  deletePalette: (id: number) => Promise<void>;
  setCurrentPalette: (palette: Palette | null) => void;
}

export const usePalettesStore = create<PalettesStore>((set, get) => ({
  palettes: [],
  currentPalette: null,
  isLoading: false,
  error: null,

  fetchPalettes: async () => {
    set({ isLoading: true, error: null });
    try {
      const palettes = await palettesApi.list();
      set({ palettes, isLoading: false });
      if (palettes.length > 0 && !get().currentPalette) {
        set({ currentPalette: palettes[0] });
      }
    } catch (error) {
      set({ error: String(error), isLoading: false });
    }
  },

  createPalette: async (data) => {
    const palette = await palettesApi.create(data);
    set((state) => ({ palettes: [palette, ...state.palettes] }));
    return palette;
  },

  updatePalette: async (id, data) => {
    const palette = await palettesApi.update(id, data);
    set((state) => ({
      palettes: state.palettes.map((p) => (p.id === id ? palette : p)),
      currentPalette:
        state.currentPalette?.id === id ? palette : state.currentPalette,
    }));
    return palette;
  },

  deletePalette: async (id) => {
    await palettesApi.delete(id);
    set((state) => ({
      palettes: state.palettes.filter((p) => p.id !== id),
      currentPalette:
        state.currentPalette?.id === id ? null : state.currentPalette,
    }));
  },

  setCurrentPalette: (palette) => set({ currentPalette: palette }),
}));
