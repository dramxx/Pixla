import React, { useEffect, useState } from "react";
import { Play, Edit2 } from "lucide-react";
import { usePalettesStore } from "@/store/palettes";
import { useGenerationsStore } from "@/store/generations";
import { useModelsStore } from "@/store/models";

export function ControlPanel() {
  const [prompt, setPrompt] = useState("");
  const [editMessage, setEditMessage] = useState("");
  const [regionX1, setRegionX1] = useState<number | "">("");
  const [regionY1, setRegionY1] = useState<number | "">("");
  const [regionX2, setRegionX2] = useState<number | "">("");
  const [regionY2, setRegionY2] = useState<number | "">("");
  const [regionDescription, setRegionDescription] = useState("");
  const [size, setSize] = useState(16);
  const [spriteType, setSpriteType] = useState("block");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [numInferenceSteps, setNumInferenceSteps] = useState(25);
  const [guidanceScale, setGuidanceScale] = useState(8.0);
  const [showLoraSettings, setShowLoraSettings] = useState(false);

  const { palettes, currentPalette } = usePalettesStore();
  const {
    createGeneration,
    isGenerating,
    currentGeneration,
    isEditing,
    setEditingMode,
    chatWithGeneration,
    clearCurrentGeneration,
  } = useGenerationsStore();
  const {
    models,
    loras,
    currentModel,
    currentLoras,
    fetchModels,
    fetchLoras,
    setCurrentModel,
    toggleLora,
    setLoraScale,
  } = useModelsStore();

  // Sync prompt when currentGeneration changes (for edit mode)
  useEffect(() => {
    if (currentGeneration && isEditing) {
      setPrompt(currentGeneration.prompt);
    }
  }, [currentGeneration, isEditing]);

  useEffect(() => {
    fetchModels();
    fetchLoras();
  }, []);

  const handleGenerate = async () => {
    if (!prompt.trim() || !currentPalette) return;

    const loras = currentLoras.map((l: any) => ({
      id: l.id,
      path: l.path,
      scale: l.scale,
    }));

    try {
      setEditingMode(false);
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

  const handleEdit = async () => {
    if (!editMessage.trim() || !currentGeneration) return;

    const region = (regionX1 !== "" && regionY1 !== "" && regionX2 !== "" && regionY2 !== "")
      ? {
          x1: regionX1 as number,
          y1: regionY1 as number,
          x2: regionX2 as number,
          y2: regionY2 as number,
          description: regionDescription || undefined,
        }
      : regionDescription
        ? { description: regionDescription }
        : undefined;

    try {
      await chatWithGeneration(currentGeneration.id, editMessage.trim(), region);
      setEditMessage("");
    } catch (error) {
      console.error("Failed to edit:", error);
    }
  };

  const handleToggleMode = () => {
    if (isEditing) {
      // Switching to new generation - clear current
      setEditingMode(false);
      setPrompt("");
      clearCurrentGeneration();
      // Clear region fields
      setRegionX1("");
      setRegionY1("");
      setRegionX2("");
      setRegionY2("");
      setRegionDescription("");
    } else if (currentGeneration) {
      // Switching to edit mode
      setEditingMode(true);
      setPrompt(currentGeneration.prompt);
    }
  };

  const hasExistingGeneration =
    currentGeneration && currentGeneration.status === "complete";

  return (
    <div className="p-6 flex flex-col h-full justify-between">
      <div className="flex-1 flex flex-col" style={{ gap: "1rem" }}>
        {/* Mode Section - shown when generation exists */}
        {hasExistingGeneration && (
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">MODE</span>
            <label className="flex items-center gap-2 cursor-pointer">
              <span className={`text-sm ${isEditing ? "text-purple-400" : "text-muted"}`}>
                Edit
              </span>
              <input
                type="checkbox"
                checked={isEditing}
                onChange={(e) => {
                  if (e.target.checked) {
                    setEditingMode(true);
                    setPrompt(currentGeneration.prompt);
                  } else {
                    setEditingMode(false);
                    setPrompt("");
                    clearCurrentGeneration();
                  }
                }}
                disabled={isGenerating}
                className="accent-purple-500 w-4 h-4"
              />
            </label>
          </div>
        )}

        {/* Edit Mode Message Input */}
        {isEditing && (
          <div>
            <label className="block text-sm font-medium mb-2">
              EDIT CURRENT IMAGE
            </label>
            <textarea
              value={editMessage}
              onChange={(e) => setEditMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.ctrlKey && e.key === "Enter") {
                  e.preventDefault();
                  if (editMessage.trim() && !isGenerating) {
                    handleEdit();
                  }
                }
              }}
              placeholder="e.g., Add more details to the handle, Change the blade color to silver..."
              rows={2}
              className="input textarea"
              disabled={isGenerating}
            />
            
            {/* Region targeting inputs */}
            <div className="mt-3">
              <label className="block text-sm font-medium mb-2">
                FOCUS REGION (optional)
              </label>
              <div className="grid grid-cols-2 gap-2 mb-2">
                <div>
                  <span className="text-xs text-muted">X1</span>
                  <input
                    type="number"
                    value={regionX1}
                    onChange={(e) => setRegionX1(e.target.value === "" ? "" : Math.max(0, parseInt(e.target.value) || 0))}
                    placeholder="0"
                    min={0}
                    className="input"
                    disabled={isGenerating}
                  />
                </div>
                <div>
                  <span className="text-xs text-muted">Y1</span>
                  <input
                    type="number"
                    value={regionY1}
                    onChange={(e) => setRegionY1(e.target.value === "" ? "" : Math.max(0, parseInt(e.target.value) || 0))}
                    placeholder="0"
                    min={0}
                    className="input"
                    disabled={isGenerating}
                  />
                </div>
                <div>
                  <span className="text-xs text-muted">X2</span>
                  <input
                    type="number"
                    value={regionX2}
                    onChange={(e) => setRegionX2(e.target.value === "" ? "" : Math.max(0, parseInt(e.target.value) || 0))}
                    placeholder="16"
                    min={0}
                    className="input"
                    disabled={isGenerating}
                  />
                </div>
                <div>
                  <span className="text-xs text-muted">Y2</span>
                  <input
                    type="number"
                    value={regionY2}
                    onChange={(e) => setRegionY2(e.target.value === "" ? "" : Math.max(0, parseInt(e.target.value) || 0))}
                    placeholder="16"
                    min={0}
                    className="input"
                    disabled={isGenerating}
                  />
                </div>
              </div>
              <input
                type="text"
                value={regionDescription}
                onChange={(e) => setRegionDescription(e.target.value)}
                placeholder="e.g., handle, blade, center (optional)"
                className="input"
                disabled={isGenerating}
              />
            </div>
          </div>
        )}

        {/* Prompt Input (New Generation mode) */}
        {!isEditing && (
          <div>
            <label className="block text-sm font-medium mb-2">PROMPT</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.ctrlKey && e.key === "Enter") {
                  e.preventDefault();
                  if (prompt.trim() && currentPalette && !isGenerating) {
                    handleGenerate();
                  }
                }
              }}
              placeholder="a medieval iron sword with wooden handle..."
              rows={3}
              className="input textarea"
              disabled={isGenerating}
            />
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium mb-2">Size</label>
            <select
              value={size}
              onChange={(e) => setSize(Number(e.target.value))}
              className="input select"
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
              className="input select"
              disabled={isGenerating}
            >
              <option value="block">Block (Tile)</option>
              <option value="icon">Item Icon</option>
              <option value="entity">Character</option>
              <option value="autotile">Autotile</option>
            </select>
          </div>
        </div>

        {/* Model Selection */}
        <div>
          <label className="block text-sm font-medium mb-2">MODEL</label>
          <select
            value={currentModel?.id || ""}
            onChange={(e) => {
              const model = models.find((m: any) => m.id === e.target.value);
              if (model) setCurrentModel(model);
            }}
            className="input select"
            disabled={isGenerating}
          >
            {models.map((model: any) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>
        </div>

        {/* LoRA Selection */}
        <div>
          <label className="block text-sm font-medium mb-2">LORA</label>
          <button
            onClick={() => setShowLoraSettings(!showLoraSettings)}
            className="input"
          >
            + Add LoRA ({currentLoras.length} active)
          </button>

          {showLoraSettings && (
            <div className="mt-2 p-3 rounded-md space-y-2">
              {loras.length === 0 ? (
                <p className="text-sm text-muted">
                  No LoRAs found. Place LoRA files in storage/loras/ folder.
                </p>
              ) : (
                loras.map((lora: any) => {
                  const isEnabled = currentLoras.some(
                    (l: any) => l.id === lora.id,
                  );
                  const enabledLora = currentLoras.find(
                    (l: any) => l.id === lora.id,
                  );

                  return (
                    <div key={lora.id} className="flex items-center gap-1">
                      <input
                        type="checkbox"
                        checked={isEnabled}
                        onChange={() => toggleLora(lora)}
                        disabled={isGenerating}
                      />
                      <span className="text-sm flex-1 whitespace-nowrap">
                        {lora.name}
                      </span>
                      {isEnabled && (
                        <div className="flex items-center gap-2">
                          <input
                            type="range"
                            min="0"
                            max="2"
                            step="0.1"
                            value={enabledLora?.scale || 1}
                            onChange={(e) =>
                              setLoraScale(lora.id, parseFloat(e.target.value))
                            }
                            className="w-full"
                          />
                          <span className="text-sm text-muted">
                            {(enabledLora?.scale || 1).toFixed(1)}
                          </span>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>

        {/* Sampling Settings */}
        <div>
          <label className="block text-sm font-medium mb-2">SAMPLING</label>
          <div className="space-y-3">
            {/* Steps Stepper */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm">Steps</span>
                <span className="text-sm text-muted">{numInferenceSteps}</span>
              </div>
              <input
                type="range"
                min="1"
                max="100"
                value={numInferenceSteps}
                onChange={(e) => setNumInferenceSteps(Number(e.target.value))}
                className="w-full"
                disabled={isGenerating}
              />
            </div>

            {/* Guidance Stepper */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm">Guidance</span>
                <span className="text-sm text-muted">{guidanceScale}</span>
              </div>
              <input
                type="range"
                min="1"
                max="20"
                step="0.5"
                value={guidanceScale}
                onChange={(e) => setGuidanceScale(Number(e.target.value))}
                className="w-full"
                disabled={isGenerating}
              />
            </div>
          </div>
        </div>

        {/* Palette Selection and Display */}
        <div>
          <label className="block text-sm font-medium mb-2">PALETTE</label>
          <select
            value={currentPalette?.id || ""}
            onChange={(e) => {
              const palette = palettes.find(
                (p: any) => p.id === Number(e.target.value),
              );
              if (palette) {
                usePalettesStore.getState().setCurrentPalette(palette);
              }
            }}
            className="input select mb-2"
            disabled={isGenerating}
          >
            <option value="">Select palette</option>
            {palettes.map((palette: any) => (
              <option key={palette.id} value={palette.id}>
                {palette.name} ({palette.colors.length} colors)
              </option>
            ))}
          </select>

          {currentPalette && (
            <div className="flex flex-wrap gap-2">
              {currentPalette.colors.map((color: any, index: number) => (
                <div
                  key={index}
                  className="rounded border border-border"
                  style={{
                    backgroundColor: color,
                    width: "25px",
                    height: "25px",
                  }}
                  title={color}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Action Button */}
      {isEditing ? (
        <button
          onClick={handleEdit}
          disabled={!editMessage.trim() || isGenerating}
          className="btn btn-primary"
        >
          <Edit2 className="w-4 h-4" />
          {isGenerating ? "Editing..." : "Apply Edit"}
        </button>
      ) : (
        <button
          onClick={handleGenerate}
          disabled={!prompt.trim() || !currentPalette || isGenerating}
          className="btn btn-primary"
        >
          <Play className="w-4 h-4" />
          {isGenerating ? "Generating..." : "Generate"}
        </button>
      )}
    </div>
  );
}
