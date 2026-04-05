import React, { useEffect, useState, useRef } from "react";
import { Download } from "lucide-react";
import { ControlPanel } from "@/components/ControlPanel";
import { Canvas } from "@/components/Canvas";
import { usePalettesStore } from "@/store/palettes";
import { useGenerationsStore } from "@/store/generations";
import { generationsApi } from "@/lib/api";

interface LogEntry {
  step: string;
  message: string;
  ts: string;
}

export function Home() {
  const { fetchPalettes, currentPalette } = usePalettesStore();
  const { currentGeneration, fetchGenerations, isGenerating, getGeneration } =
    useGenerationsStore();
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [generationProgress, setGenerationProgress] = useState<string>("");
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchPalettes();
    fetchGenerations();
  }, []);

  useEffect(() => {
    // Clear logs when starting new generation
    if (currentGeneration?.status === "generating") {
      setLogs([]);
    }
  }, [currentGeneration?.id]);

  useEffect(() => {
    // Re-subscribe to SSE stream when generation ID or status changes
    // This handles both initial generation AND edit mode (status changes to "generating")
    if (currentGeneration?.id && (currentGeneration.status === "generating" || currentGeneration.status === "complete")) {
      // Clear logs when starting a new generation (initial or edit)
      if (currentGeneration.status === "generating") {
        setLogs([]);
      }

      // Only connect to stream if actively generating
      if (currentGeneration.status !== "generating") {
        setGenerationProgress("");
        return;
      }

      setGenerationProgress("Starting generation...");

      const eventSource = generationsApi.stream(currentGeneration.id);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Update progress message
          setGenerationProgress(`Iteration ${data.iterations || 0}...`);
          
          // Append new logs
          if (data.logs && data.logs.length > 0) {
            setLogs((prev) => [...prev, ...data.logs]);
          }

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
  }, [currentGeneration?.id, currentGeneration?.status]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const getStepIcon = (step: string) => {
    switch (step) {
      case "thinking": return "🧠";
      case "tool_call": return "🔧";
      case "tool_result": return "✅";
      case "llm_response": return "💬";
      case "warning": return "⚠️";
      case "error": return "❌";
      default: return "📝";
    }
  };

  const getStepColor = (step: string) => {
    switch (step) {
      case "thinking": return "text-blue-400";
      case "tool_call": return "text-yellow-400";
      case "tool_result": return "text-green-400";
      case "llm_response": return "text-purple-400";
      case "warning": return "text-orange-400";
      case "error": return "text-red-400";
      default: return "text-gray-400";
    }
  };

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
        
        {/* Logs Display - show during generation and after completion */}
        {(currentGeneration?.status === "generating" || currentGeneration?.status === "complete") && logs.length > 0 && (
          <div className="mt-4 flex-1 min-h-0 pb-4">
            <div className="text-sm text-gray-400 mb-2">Generation Logs ({logs.length} steps)</div>
            <div className="bg-gray-900 rounded-lg p-2 h-48 overflow-y-auto font-mono text-xs space-y-1">
              {logs.map((log, i) => (
                <div key={i} className={getStepColor(log.step)}>
                  <span className="text-gray-600">[{log.ts}]</span>{" "}
                  <span>{getStepIcon(log.step)}</span>{" "}
                  <span className="text-gray-300">{log.step}:</span>{" "}
                  {log.message.length > 60 
                    ? log.message.slice(0, 60) + "..." 
                    : log.message}
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          </div>
        )}
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