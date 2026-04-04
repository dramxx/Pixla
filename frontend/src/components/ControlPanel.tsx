import React, { useEffect, useState } from "react";
import { Play, Download, Settings } from "lucide-react";
import { usePalettesStore } from "@/store/palettes";
import { useGenerationsStore } from "@/store/generations";
import { useModelsStore } from "@/store/models";

interface ControlPanelProps {
  onDownload?: () => void;
}

export function ControlPanel({ onDownload }: ControlPanelProps) {
  const [prompt, setPrompt] = useState("");
  const [size, setSize] = useState(16);
  const [spriteType, setSpriteType] = useState("block");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [numInferenceSteps, setNumInferenceSteps] = useState(25);
  const [guidanceScale, setGuidanceScale] = useState(8.0);
  const [showLoraSettings, setShowLoraSettings] = useState(false);

  const { palettes, currentPalette } = usePalettesStore();
  const { createGeneration, isGenerating, currentGeneration } = useGenerationsStore();
  const { models, loras, currentModel, currentLoras, fetchModels, fetchLoras, setCurrentModel, toggleLora, setLoraScale } = useModelsStore();

  useEffect(() => {
    fetchModels();
    fetchLoras();
  }, []);

  const handleGenerate = async () => {
    if (!prompt.trim() || !currentPalette) return;

    const loras = currentLoras.map((l) => ({
      id: l.id,
      path: l.path,
      scale: l.scale,
    }));

    try {
      await createGeneration({
        prompt: prompt.trim(),
        colors: currentPalette.colors,
        size,
        sprite_type: spriteType,
        system_prompt: systemPrompt.trim() || undefined,
        model: currentModel?.path,
        loras: loras.length > 0 ? loras : undefined,
        num_inference_steps: numInferenceSteps,
        guidance_scale: guidanceScale,
      });
    } catch (error) {
      console.error("Failed to generate:", error);
    }
  };

  const handleDownload = () => {
    if (currentGeneration?.id) {
      window.open(`/api/generations/${currentGeneration.id}/download`, "_blank");
    }
    onDownload?.();
  };

  const hasResult = currentGeneration?.status === "complete" && currentGeneration?.image_path;

  return (
    <div className="bg-card rounded-lg border border-border p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-4">Generate Sprite</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Prompt</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="a medieval iron sword with wooden handle..."
              rows={4}
              className="w-full p-3 border border-input rounded-md bg-background text-sm resize-none"
              disabled={isGenerating}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Size</label>
              <select
                value={size}
                onChange={(e) => setSize(Number(e.target.value))}
                className="w-full p-2 border border-input rounded-md bg-background"
                disabled={isGenerating}
              >
                <option value={8}>8x8</option>
                <option value={16}>16x16</option>
                <option value={32}>32x32</option>
                <option value={64}>64x64</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Type</label>
              <select
                value={spriteType}
                onChange={(e) => setSpriteType(e.target.value)}
                className="w-full p-2 border border-input rounded-md bg-background"
                disabled={isGenerating}
              >
                <option value="block">Block (Tile)</option>
                <option value="icon">Item Icon</option>
                <option value="entity">Character</option>
                <option value="autotile">Autotile</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Model</label>
            <select
              value={currentModel?.id || ""}
              onChange={(e) => {
                const model = models.find((m) => m.id === e.target.value);
                if (model) setCurrentModel(model);
              }}
              className="w-full p-2 border border-input rounded-md bg-background"
              disabled={isGenerating}
            >
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
            {currentModel?.description && (
              <p className="text-xs text-muted-foreground mt-1">{currentModel.description}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Steps</label>
              <input
                type="number"
                value={numInferenceSteps}
                onChange={(e) => setNumInferenceSteps(Number(e.target.value))}
                min={1}
                max={100}
                className="w-full p-2 border border-input rounded-md bg-background"
                disabled={isGenerating}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Guidance</label>
              <input
                type="number"
                value={guidanceScale}
                onChange={(e) => setGuidanceScale(Number(e.target.value))}
                min={1}
                max={20}
                step={0.5}
                className="w-full p-2 border border-input rounded-md bg-background"
                disabled={isGenerating}
              />
            </div>
          </div>

          <div>
            <button
              type="button"
              onClick={() => setShowLoraSettings(!showLoraSettings)}
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
            >
              <Settings className="w-4 h-4" />
              LoRA Settings ({currentLoras.length} active)
            </button>
            
            {showLoraSettings && (
              <div className="mt-2 p-3 border border-border rounded-md bg-muted/30 space-y-2">
                {loras.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No LoRAs found. Place LoRA files in storage/loras/ folder.
                  </p>
                ) : (
                  loras.map((lora) => {
                    const isEnabled = currentLoras.some((l) => l.id === lora.id);
                    const enabledLora = currentLoras.find((l) => l.id === lora.id);
                    
                    return (
                      <div key={lora.id} className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={isEnabled}
                          onChange={() => toggleLora(lora)}
                          className="rounded border-border"
                          disabled={isGenerating}
                        />
                        <span className="text-sm flex-1">{lora.name}</span>
                        {isEnabled && (
                          <input
                            type="range"
                            min="0"
                            max="2"
                            step="0.1"
                            value={enabledLora?.scale || 1}
                            onChange={(e) => setLoraScale(lora.id, parseFloat(e.target.value))}
                            className="w-20"
                          />
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Palette</label>
            <select
              value={currentPalette?.id || ""}
              onChange={(e) => {
                const palette = palettes.find((p) => p.id === Number(e.target.value));
                if (palette) {
                  usePalettesStore.getState().setCurrentPalette(palette);
                }
              }}
              className="w-full p-2 border border-input rounded-md bg-background"
              disabled={isGenerating}
            >
              <option value="">Select palette</option>
              {palettes.map((palette) => (
                <option key={palette.id} value={palette.id}>
                  {palette.name} ({palette.colors.length} colors)
                </option>
              ))}
            </select>

            {currentPalette && (
              <div className="mt-2 flex flex-wrap gap-1">
                {currentPalette.colors.map((color, index) => (
                  <div
                    key={index}
                    className="w-6 h-6 rounded border border-border"
                    style={{ backgroundColor: color }}
                    title={color}
                  />
                ))}
              </div>
            )}
          </div>

          <button
            onClick={handleGenerate}
            disabled={!prompt.trim() || !currentPalette || isGenerating}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className="w-4 h-4" />
            {isGenerating ? "Generating..." : "Generate"}
          </button>

          {hasResult && (
            <button
              onClick={handleDownload}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80"
            >
              <Download className="w-4 h-4" />
              Download PNG
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
