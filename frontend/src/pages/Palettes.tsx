import React, { useEffect, useState } from "react";
import { Plus, Trash2, Edit2 } from "lucide-react";
import { usePalettesStore } from "@/store/palettes";

export function Palettes() {
  const { palettes, fetchPalettes, createPalette, deletePalette, isLoading } = usePalettesStore();
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newColors, setNewColors] = useState("#000000");

  useEffect(() => {
    fetchPalettes();
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    const colors = newColors.split(",").map((c) => c.trim()).filter((c) => c.startsWith("#"));
    if (colors.length === 0) return;
    
    await createPalette({ name: newName.trim(), colors });
    setShowForm(false);
    setNewName("");
    setNewColors("#000000");
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Palettes</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md"
        >
          <Plus className="w-4 h-4" />
          New Palette
        </button>
      </div>

      {showForm && (
        <div className="bg-card rounded-lg border border-border p-6 mb-6">
          <h3 className="font-semibold mb-4">Create Palette</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="My Palette"
                className="w-full p-2 border border-input rounded-md bg-background"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Colors (comma-separated hex)</label>
              <input
                type="text"
                value={newColors}
                onChange={(e) => setNewColors(e.target.value)}
                placeholder="#000000, #FFFFFF, #FF0000"
                className="w-full p-2 border border-input rounded-md bg-background"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md"
              >
                Create
              </button>
              <button
                onClick={() => setShowForm(false)}
                className="px-4 py-2 border border-input rounded-md"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {palettes.map((palette) => (
          <div
            key={palette.id}
            className="bg-card rounded-lg border border-border p-4"
          >
            <div className="font-medium mb-2">{palette.name}</div>
            <div className="flex flex-wrap gap-1 mb-3">
              {palette.colors.map((color, i) => (
                <div
                  key={i}
                  className="w-6 h-6 rounded border border-border"
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
            <div className="text-xs text-muted-foreground">
              {palette.colors.length} colors
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
