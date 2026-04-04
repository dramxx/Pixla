import React, { useEffect, useState } from "react";
import { Plus, X } from "lucide-react";
import { usePalettesStore } from "@/store/palettes";

export function Palettes() {
  const { palettes, fetchPalettes, createPalette, deletePalette, isLoading } = usePalettesStore();
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newColors, setNewColors] = useState("#000000");
  const [deletingId, setDeletingId] = useState<number | null>(null);

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

  const handleDelete = async () => {
    if (deletingId !== null) {
      await deletePalette(deletingId);
      setDeletingId(null);
    }
  };

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Palettes</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn btn-primary"
          style={{ width: 'auto', paddingLeft: '1rem', paddingRight: '1rem' }}
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
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Colors (comma-separated hex)</label>
              <input
                type="text"
                value={newColors}
                onChange={(e) => setNewColors(e.target.value)}
                placeholder="#000000, #FFFFFF, #FF0000"
                className="input"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                className="btn btn-primary"
              >
                Create
              </button>
              <button
                onClick={() => setShowForm(false)}
                className="btn btn-secondary"
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
            <div className="flex items-start justify-between mb-2">
              <div>
                <div className="font-medium">{palette.name}</div>
                <div className="text-xs text-muted-foreground">
                  {palette.colors.length} colors
                </div>
              </div>
              {palettes.length > 1 && (
                <button
                  onClick={() => setDeletingId(palette.id)}
                  className="btn btn-primary"
                  style={{ width: 'auto', padding: '0.25rem 0.5rem' }}
                  title="Delete palette"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-1">
              {palette.colors.map((color, i) => (
                <div
                  key={i}
                  className="rounded border border-border"
                  style={{ backgroundColor: color, width: '25px', height: '25px' }}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Delete Confirmation Modal */}
      {deletingId !== null && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-secondary rounded-lg border border-border p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Delete Palette?</h3>
            <p className="text-muted mb-6">Are you sure you want to delete this palette? This action cannot be undone.</p>
            <div className="flex gap-3">
              <button
                onClick={() => setDeletingId(null)}
                className="btn btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="btn btn-primary flex-1"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
