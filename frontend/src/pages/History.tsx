import React, { useEffect, useState } from "react";
import { X, Download, MessageSquare, Loader2 } from "lucide-react";
import { useGenerationsStore } from "@/store/generations";
import { usePalettesStore } from "@/store/palettes";
import { generationsApi } from "@/lib/api";
import { Generation, TilesetResponse } from "@/lib/types";
import { Canvas } from "@/components/Canvas";

interface ChatModalProps {
  generation: Generation;
  onClose: () => void;
  onComplete: (updated: Generation) => void;
}

function ChatModal({ generation, onClose, onComplete }: ChatModalProps) {
  const { updateGeneration } = useGenerationsStore();
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const updated = await generationsApi.chat(generation.id, message);
      updateGeneration(updated);
      onComplete(updated);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-card rounded-lg border border-border max-w-md w-full">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold">Edit: {generation.prompt}</h2>
          <button onClick={onClose} className="p-2 hover:bg-accent rounded-md">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Describe your edit</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="e.g., Make the eyes bigger, change the color to blue..."
              className="w-full h-24 px-3 py-2 bg-background border border-input rounded-md resize-none"
              disabled={isLoading}
            />
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-input rounded-md hover:bg-accent"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !message.trim()}
              className="btn btn-primary flex items-center gap-2"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              Send to Agent
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface TilesetModalProps {
  generation: Generation;
  onClose: () => void;
}

function TilesetModal({ generation, onClose }: TilesetModalProps) {
  const [tileset, setTileset] = useState<TilesetResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const tilesetName = `tileset_${generation.id}`;

  useEffect(() => {
    const abortController = new AbortController();
    
    generationsApi.tileset(generation.id, tilesetName)
      .then(setTileset)
      .catch((err) => {
        if (err instanceof Error && err.name !== 'AbortError') {
          setError(err instanceof Error ? err.message : "Failed to generate tileset");
        }
      })
      .finally(() => setIsLoading(false));
    
    return () => {
      abortController.abort();
    };
  }, [generation.id, tilesetName]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-card rounded-lg border border-border max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold">Tileset: {generation.prompt}</h2>
          <button onClick={onClose} className="p-2 hover:bg-accent rounded-md">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : error ? (
            <p className="text-red-500">{error}</p>
          ) : tileset ? (
            <div className="grid grid-cols-4 gap-4">
              {tileset.files.map((filename) => (
                <div key={filename} className="space-y-2">
                  <img
                    src={`/api/generations/${generation.id}/tileset/${tilesetName}/${filename}`}
                    alt={filename}
                    className="w-full aspect-square object-contain bg-muted rounded"
                  />
                  <p className="text-xs text-center text-muted-foreground">{filename}</p>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

interface GenerationDetailModalProps {
  generation: Generation | null;
  onClose: () => void;
}

function GenerationDetailModal({ generation, onClose }: GenerationDetailModalProps) {
  const { palettes } = usePalettesStore();
  const [isLoading, setIsLoading] = useState(true);
  const [fullGeneration, setFullGeneration] = useState<Generation | null>(null);
  const [showChat, setShowChat] = useState(false);
  const [showTileset, setShowTileset] = useState(false);

  const handleUpdateGeneration = (updated: Generation) => {
    setFullGeneration(updated);
  };

  useEffect(() => {
    if (!generation) return;
    
    const abortController = new AbortController();
    
    setIsLoading(true);
    generationsApi.get(generation.id, { signal: abortController.signal })
      .then((gen) => {
        setFullGeneration(gen);
        setIsLoading(false);
      })
      .catch((err) => {
        if (err instanceof Error && err.name !== 'AbortError') {
          setIsLoading(false);
        }
      });
    
    return () => {
      abortController.abort();
    };
  }, [generation]);

  if (!generation) return null;

  const palette = palettes.find((p) => JSON.stringify(p.colors) === JSON.stringify(generation.colors));

  const handleDownload = () => {
    window.open(generationsApi.download(generation.id), "_blank");
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-card rounded-lg border border-border max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold">Generation Details</h2>
          <button onClick={onClose} className="p-2 hover:bg-accent rounded-md">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <>
              <div className="flex justify-center">
                {fullGeneration?.pixel_data && palette ? (
                  <Canvas
                    pixelData={fullGeneration.pixel_data}
                    palette={palette.colors}
                    size={fullGeneration.size}
                    scale={Math.min(32, 384 / fullGeneration.size)}
                  />
                ) : (
                  <div className="w-64 h-64 bg-muted rounded-lg flex items-center justify-center">
                    No preview available
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <h3 className="font-medium">{fullGeneration?.prompt}</h3>
                <div className="text-sm text-muted-foreground">
                  <p>Size: {fullGeneration?.size}x{fullGeneration?.size}</p>
                  <p>Type: {fullGeneration?.sprite_type}</p>
                  <p>Status: {fullGeneration?.status}</p>
                  <p>Created: {new Date(fullGeneration?.created_at || "").toLocaleString()}</p>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={handleDownload}
                  className="btn btn-primary"
                  style={{ width: 'auto', paddingLeft: '1rem', paddingRight: '1rem' }}
                >
                  <Download className="w-4 h-4" />
                  Download PNG
                </button>
                {generation.sprite_type === "block" && (
                  <button
                    onClick={() => setShowTileset(true)}
                    className="btn btn-secondary flex-1"
                  >
                    View Tileset
                  </button>
                )}
                <button
                  onClick={() => setShowChat(true)}
                  className="btn btn-secondary flex-1"
                >
                  <MessageSquare className="w-4 h-4" />
                  Edit
                </button>
              </div>
            </>
          )}
        </div>

        {showChat && fullGeneration && (
          <ChatModal
            generation={fullGeneration}
            onClose={() => setShowChat(false)}
            onComplete={handleUpdateGeneration}
          />
        )}

        {showTileset && fullGeneration && (
          <TilesetModal
            generation={fullGeneration}
            onClose={() => setShowTileset(false)}
          />
        )}
      </div>
    </div>
  );
}

export function History() {
  const { generations, fetchGenerations, isLoading } = useGenerationsStore();
  const [selectedGeneration, setSelectedGeneration] = useState<Generation | null>(null);

  useEffect(() => {
    fetchGenerations();
  }, []);

  const handleDownload = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    window.open(generationsApi.download(id), "_blank");
  };

  return (
    <div className="flex-1 overflow-auto p-6">
      <h1 className="text-2xl font-bold mb-6">History</h1>

      {isLoading ? (
        <p className="text-muted-foreground">Loading...</p>
      ) : generations.length === 0 ? (
        <p className="text-muted-foreground">No generations yet.</p>
      ) : (
        <div className="space-y-4">
          {generations.map((gen) => (
            <div
              key={gen.id}
              onClick={() => setSelectedGeneration(gen)}
              className="bg-card rounded-lg border border-border p-4 flex items-center gap-4 cursor-pointer hover:bg-accent/50 transition-colors"
            >
              <div className="w-16 h-16 bg-muted rounded flex items-center justify-center">
                {gen.status === "complete" ? (
                  <span className="text-2xl">🖼️</span>
                ) : gen.status === "error" ? (
                  <span className="text-2xl">❌</span>
                ) : (
                  <span className="text-2xl">⏳</span>
                )}
              </div>
              <div className="flex-1">
                <div className="font-medium">{gen.prompt}</div>
                <div className="text-sm text-muted-foreground">
                  {gen.size}x{gen.size} • {gen.sprite_type} • {gen.status}
                </div>
              </div>
              {gen.status === "complete" && gen.image_path && (
                <button
                  onClick={(e) => handleDownload(gen.id, e)}
                  className="btn btn-primary"
                  style={{ width: 'auto', paddingLeft: '1rem', paddingRight: '1rem' }}
                >
                  <Download className="w-4 h-4" />
                  Download
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <GenerationDetailModal
        generation={selectedGeneration}
        onClose={() => setSelectedGeneration(null)}
      />
    </div>
  );
}
