import React, { useRef, useEffect, useState } from "react";

interface CanvasProps {
  pixelData?: number[][];
  palette: string[];
  size: number;
  scale?: number;
  showGrid?: boolean;
}

export function Canvas({
  pixelData,
  palette,
  size,
  scale = 32,
  showGrid = true,
}: CanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!pixelData || !palette.length) {
      ctx.fillStyle = "#1a1a1a";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      return;
    }

    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const colorIndex = pixelData[y]?.[x];
        if (colorIndex !== undefined && colorIndex >= 0 && colorIndex < palette.length) {
          ctx.fillStyle = palette[colorIndex];
          ctx.fillRect(x * scale, y * scale, scale, scale);
        } else if (colorIndex === -1) {
          ctx.fillStyle = "transparent";
          ctx.clearRect(x * scale, y * scale, scale, scale);
        }
      }
    }

    if (showGrid) {
      ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
      ctx.lineWidth = 1;
      for (let i = 0; i <= size; i++) {
        ctx.beginPath();
        ctx.moveTo(i * scale, 0);
        ctx.lineTo(i * scale, size * scale);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, i * scale);
        ctx.lineTo(size * scale, i * scale);
        ctx.stroke();
      }
    }
  }, [pixelData, palette, size, scale, showGrid]);

  return (
    <canvas
      ref={canvasRef}
      width={size * scale}
      height={size * scale}
      className="border border-border canvas-grid"
      style={{ imageRendering: "pixelated" }}
    />
  );
}
