import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Canvas } from '@/components/Canvas'

// Mock canvas getContext for jsdom
const mockCanvasContext = {
  clearRect: vi.fn(),
  fillStyle: '',
  fillRect: vi.fn(),
  strokeStyle: '',
  lineWidth: 0,
  beginPath: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  stroke: vi.fn(),
}

Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
  writable: true,
  value: vi.fn().mockReturnValue(mockCanvasContext),
})

Object.defineProperty(HTMLCanvasElement.prototype, 'width', {
  writable: true,
  value: 0,
  configurable: true,
})

Object.defineProperty(HTMLCanvasElement.prototype, 'height', {
  writable: true,
  value: 0,
  configurable: true,
})

describe('Canvas', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders canvas element', () => {
    render(
      <Canvas
        palette={['#FF0000', '#00FF00']}
        size={4}
        scale={32}
      />
    )

    const canvas = document.querySelector('canvas')
    expect(canvas).toBeTruthy()
    expect(canvas?.tagName).toBe('CANVAS')
  })

  it('sets correct dimensions based on size and scale', () => {
    render(
      <Canvas
        palette={['#FF0000']}
        size={8}
        scale={16}
      />
    )

    const canvas = document.querySelector('canvas') as HTMLCanvasElement
    expect(canvas?.width).toBe(128)
    expect(canvas?.height).toBe(128)
  })

  it('renders empty canvas when no pixel data', () => {
    render(
      <Canvas
        palette={['#FF0000']}
        size={4}
        scale={32}
      />
    )

    const canvas = document.querySelector('canvas') as HTMLCanvasElement
    expect(canvas?.width).toBe(128)
    expect(canvas?.height).toBe(128)
  })

  it('renders without grid when showGrid is false', () => {
    const pixelData = [[0]]

    render(
      <Canvas
        pixelData={pixelData}
        palette={['#FF0000']}
        size={1}
        scale={32}
        showGrid={false}
      />
    )

    const canvas = document.querySelector('canvas')
    expect(canvas).toBeTruthy()
  })

  it('has pixelated styling', () => {
    render(
      <Canvas
        palette={['#FF0000']}
        size={4}
        scale={32}
      />
    )

    const canvas = document.querySelector('canvas')
    expect(canvas?.style.imageRendering).toBe('pixelated')
  })

  it('handles out of bounds color index gracefully', () => {
    const pixelData = [[99, 0], [0, 99]]
    const palette = ['#FF0000']

    render(
      <Canvas
        pixelData={pixelData}
        palette={palette}
        size={2}
        scale={32}
      />
    )

    const canvas = document.querySelector('canvas')
    expect(canvas).toBeTruthy()
  })

  it('has correct CSS classes', () => {
    render(
      <Canvas
        palette={['#FF0000']}
        size={4}
        scale={32}
      />
    )

    const canvas = document.querySelector('canvas')
    expect(canvas?.className).toContain('border')
    expect(canvas?.className).toContain('canvas-grid')
  })
})
