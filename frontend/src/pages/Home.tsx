import React, { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { ControlPanel } from "@/components/ControlPanel";
import { Canvas } from "@/components/Canvas";
import { usePalettesStore } from "@/store/palettes";
import { useGenerationsStore } from "@/store/generations";
import { generationsApi } from "@/lib/api";

export function Home() {
  const { fetchPalettes, currentPalette } = usePalettesStore();
  const { currentGeneration, fetchGenerations, isGenerating, getGeneration } =
    useGenerationsStore();
  const [generationProgress, setGenerationProgress] = useState<string>("");

  useEffect(() => {
    fetchPalettes();
    fetchGenerations();
  }, []);

  useEffect(() => {
    if (currentGeneration?.status === "generating") {
      setGenerationProgress("Starting generation...");

      const eventSource = generationsApi.stream(currentGeneration.id);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setGenerationProgress(`Iteration ${data.iterations || 0}...`);

          if (data.status === "complete") {
            getGeneration(currentGeneration.id);
            eventSource.close();
            setGenerationProgress("");
          } else if (data.status === "error") {
            getGeneration(currentGeneration.id);
            eventSource.close();
            setGenerationProgress("Generation failed");
          }
        } catch (e) {
          console.error("SSE parse error:", e);
        }
      };

      return () => {
        eventSource.close();
        setGenerationProgress("");
      };
    }
  }, [currentGeneration?.id]);

  const canGenerate = currentPalette && !isGenerating;
  const hasResult =
    currentGeneration?.status === "complete" && currentGeneration?.image_path;

  const handleDownload = () => {
    if (currentGeneration?.id) {
      window.open(
        `/api/generations/${currentGeneration.id}/download`,
        "_blank",
      );
    }
  };

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Left Sidebar - Controls */}
      <div className="w-80 border-r border-border flex flex-col" style={{ backgroundColor: 'var(--bg-secondary)' }}>
        <div className="flex-1 overflow-y-auto">
          <ControlPanel />
        </div>
      </div>

      {/* Main Content - Canvas Display */}
      <div className="flex-1 flex flex-col bg-primary p-6 overflow-hidden" style={{ backgroundImage: 'linear-gradient(var(--grid) 1px, transparent 1px), linear-gradient(90deg, var(--grid) 1px, transparent 1px)', backgroundSize: '25px 25px', backgroundColor: 'var(--bg-primary)' }}>
        {/* Download Button */}
        <button
          onClick={handleDownload}
          disabled={!hasResult}
          className={hasResult ? "btn btn-primary mb-4" : "btn btn-secondary mb-4"}
          style={{ width: 'auto', paddingLeft: '1rem', paddingRight: '1rem', alignSelf: 'flex-end', flex: 'none' }}
        >
          <Download className="w-4 h-4" />
          Download PNG
        </button>

        {/* Canvas Content */}
        <div className="flex-1 flex items-center justify-center rounded-lg overflow-hidden" style={{ backgroundColor: 'transparent', minHeight: 0 }}>
          {isGenerating ? (
            <div className="flex flex-col items-center gap-4">
              <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="text-muted">
                {generationProgress || "Generating..."}
              </p>
            </div>
          ) : hasResult && currentGeneration?.pixel_data ? (
            <Canvas
              pixelData={currentGeneration.pixel_data}
              palette={currentPalette?.colors || []}
              size={currentGeneration.size || 16}
            />
          ) : canGenerate ? (
            <div />
          ) : (
            <div />
          )}
        </div>
      </div>
    </div>
  );
}
