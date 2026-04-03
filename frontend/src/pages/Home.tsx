import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Download } from "lucide-react";
import { ControlPanel } from "@/components/ControlPanel";
import { Canvas } from "@/components/Canvas";
import { usePalettesStore } from "@/store/palettes";
import { useGenerationsStore } from "@/store/generations";
import { generationsApi } from "@/lib/api";

export function Home() {
  const { palettes, fetchPalettes, currentPalette } = usePalettesStore();
  const { currentGeneration, fetchGenerations, isGenerating, getGeneration } = useGenerationsStore();
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
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

  useEffect(() => {
    if (currentGeneration?.image_path) {
      setPreviewUrl(`/api/generations/${currentGeneration.id}/download`);
    }
  }, [currentGeneration?.image_path]);

  const canGenerate = currentPalette && !isGenerating;
  const hasResult = currentGeneration?.status === "complete" && currentGeneration?.image_path;

  const handleDownload = () => {
    if (currentGeneration?.id) {
      window.open(`/api/generations/${currentGeneration.id}/download`, "_blank");
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
      >
        <ControlPanel />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="flex flex-col items-center justify-center"
      >
        <div className="bg-card rounded-lg border border-border p-6">
          <h3 className="text-lg font-semibold mb-4 text-center">Preview</h3>

          {isGenerating ? (
            <div className="w-[512px] h-[512px] bg-muted rounded-lg flex flex-col items-center justify-center gap-4">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="text-muted-foreground">{generationProgress || "Generating..."}</p>
            </div>
          ) : hasResult && currentGeneration?.pixel_data ? (
            <>
              <Canvas
                pixelData={currentGeneration.pixel_data}
                palette={currentPalette?.colors || []}
                size={currentGeneration.size || 16}
                scale={32}
              />
              <button
                onClick={handleDownload}
                className="mt-4 flex items-center justify-center gap-2 py-2 px-4 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80"
              >
                <Download className="w-4 h-4" />
                Download PNG
              </button>
            </>
          ) : canGenerate ? (
            <div className="w-[512px] h-[512px] bg-muted rounded-lg flex items-center justify-center">
              <p className="text-muted-foreground">Your sprite will appear here</p>
            </div>
          ) : (
            <div className="w-[512px] h-[512px] bg-muted rounded-lg flex items-center justify-center">
              <p className="text-muted-foreground">Select a palette to start</p>
            </div>
          )}

          {currentGeneration && !isGenerating && (
            <div className="mt-4 text-center text-sm text-muted-foreground">
              {currentGeneration.size}x{currentGeneration.size} • {currentGeneration.sprite_type} • {currentGeneration.status}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
