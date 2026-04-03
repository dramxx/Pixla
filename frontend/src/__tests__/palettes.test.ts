import { describe, it, expect, beforeEach } from 'vitest'
import { usePalettesStore } from '@/store/palettes'

describe('usePalettesStore', () => {
  beforeEach(() => {
    usePalettesStore.setState({
      palettes: [],
      currentPalette: null,
      isLoading: false,
      error: null,
    })
  })

  it('initial state is empty', () => {
    const state = usePalettesStore.getState()
    expect(state.palettes).toEqual([])
    expect(state.currentPalette).toBeNull()
    expect(state.isLoading).toBe(false)
    expect(state.error).toBeNull()
  })

  it('setCurrentPalette updates current palette', () => {
    const palette = { id: 1, name: 'Test', colors: ['#FF0000'], created_at: '', updated_at: '' }

    usePalettesStore.getState().setCurrentPalette(palette)

    const state = usePalettesStore.getState()
    expect(state.currentPalette).toEqual(palette)
  })

  it('setCurrentPalette to null clears current', () => {
    usePalettesStore.setState({
      currentPalette: { id: 1, name: 'Test', colors: ['#FF0000'], created_at: '', updated_at: '' },
    })

    usePalettesStore.getState().setCurrentPalette(null)

    const state = usePalettesStore.getState()
    expect(state.currentPalette).toBeNull()
  })

  it('state is accessible via getState', () => {
    usePalettesStore.setState({
      palettes: [
        { id: 1, name: 'Test', colors: ['#FF0000'], created_at: '', updated_at: '' },
      ],
    })

    const state = usePalettesStore.getState()
    expect(state.palettes).toHaveLength(1)
  })
})
