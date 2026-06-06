import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import CharacterCard from './CharacterCard'
import { useGameStore } from '../../store/gameStore'
import type { CharacterData } from '../../store/gameStore'

const RESET = {
  sessionId: null, worldId: null, messages: [], isLoading: false,
  combat: null, currentLocation: null, characters: [], proposals: [],
}

const makeChar = (overrides: Partial<CharacterData> = {}): CharacterData => ({
  id: 'c1',
  name: 'Aragorn',
  char_class: 'Ranger',
  race: 'Human',
  level: 10,
  hp_current: 80,
  hp_max: 100,
  ac: 17,
  stats: null,
  ...overrides,
})

beforeEach(() => {
  useGameStore.setState(RESET)
})

describe('CharacterCard', () => {
  it('shows empty-state message when there are no characters', () => {
    render(<CharacterCard />)
    expect(screen.getByText('No characters loaded.')).toBeInTheDocument()
  })

  it('shows the party size in the header', () => {
    useGameStore.setState({ characters: [makeChar(), makeChar({ id: 'c2', name: 'Legolas' })] })
    render(<CharacterCard />)
    expect(screen.getByText(/Party \(2\)/)).toBeInTheDocument()
  })

  it('renders name, race, class and level for each character', () => {
    useGameStore.setState({ characters: [makeChar()] })
    render(<CharacterCard />)
    expect(screen.getByText('Aragorn')).toBeInTheDocument()
    expect(screen.getByText(/Human/)).toBeInTheDocument()
    expect(screen.getByText(/Ranger/)).toBeInTheDocument()
    expect(screen.getByText(/Lvl 10/)).toBeInTheDocument()
  })

  it('renders HP and AC stats', () => {
    useGameStore.setState({ characters: [makeChar()] })
    render(<CharacterCard />)
    expect(screen.getByText(/80\/100/)).toBeInTheDocument()
    expect(screen.getByText(/AC 17/)).toBeInTheDocument()
  })

  it('handles null hp_current and hp_max gracefully', () => {
    useGameStore.setState({ characters: [makeChar({ hp_current: null, hp_max: null })] })
    render(<CharacterCard />)
    expect(screen.getByText(/HP –\/–/)).toBeInTheDocument()
  })

  it('renders ability scores when stats are provided', () => {
    const stats = {
      ability_scores: {
        strength: 18, dexterity: 14, constitution: 16,
        intelligence: 10, wisdom: 12, charisma: 8,
      },
    }
    useGameStore.setState({ characters: [makeChar({ stats })] })
    render(<CharacterCard />)
    expect(screen.getByText('18')).toBeInTheDocument()
    expect(screen.getByText('+4')).toBeInTheDocument()
  })

  it('shows "–" for ability scores when stats is null', () => {
    useGameStore.setState({ characters: [makeChar({ stats: null })] })
    render(<CharacterCard />)
    const dashes = screen.getAllByText('–')
    expect(dashes.length).toBeGreaterThanOrEqual(6)
  })
})
