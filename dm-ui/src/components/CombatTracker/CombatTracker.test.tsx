import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CombatTracker from './CombatTracker'
import { api } from '../../api/client'
import { useGameStore } from '../../store/gameStore'
import type { ActiveCombat } from '../../store/gameStore'
import type { CombatStateResponse } from '../../api/client'

vi.mock('../../api/client', () => ({
  api: {
    startCombat: vi.fn(),
    endCombat: vi.fn(),
    submitAction: vi.fn(),
    nextTurn: vi.fn(),
  },
}))

const RESET = {
  sessionId: 'sess-1', worldId: 'world-1', messages: [], isLoading: false,
  combat: null, currentLocation: null, characters: [], proposals: [],
}

function makeCombatResponse(overrides: Partial<CombatStateResponse> = {}): CombatStateResponse {
  return {
    id: 'cbt-1',
    session_id: 'sess-1',
    location_id: null,
    round_number: 1,
    current_turn_index: 0,
    initiative_order: [
      { character_id: 'char-a', name: 'Aragorn', initiative: 18 },
      { character_id: 'char-b', name: 'Goblin', initiative: 10 },
    ],
    combatants: [
      { id: 'char-a', name: 'Aragorn', hp_current: 50, hp_max: 50, ac: 17, speed: 30, level: 5, conditions: [], condition_durations: {} },
      { id: 'char-b', name: 'Goblin', hp_current: 7, hp_max: 7, ac: 13, speed: 30, level: 1, conditions: [], condition_durations: {} },
    ],
    combat_log: [],
    started_at: '',
    ended_at: null,
    ...overrides,
  }
}

function makeActiveCombat(): ActiveCombat {
  return {
    id: 'cbt-1',
    round_number: 1,
    current_turn_index: 0,
    combatants: [
      { char_id: 'char-a', name: 'Aragorn', hp_current: 50, hp_max: 50, ac: 17, initiative: 18, is_current_turn: true },
      { char_id: 'char-b', name: 'Goblin', hp_current: 7, hp_max: 7, ac: 13, initiative: 10, is_current_turn: false },
    ],
  }
}

beforeEach(() => {
  useGameStore.setState(RESET)
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('CombatTracker — no active combat', () => {
  it('shows "No active combat." message', () => {
    render(<CombatTracker />)
    expect(screen.getByText('No active combat.')).toBeInTheDocument()
  })

  it('shows Start Combat button when session is active', () => {
    render(<CombatTracker />)
    expect(screen.getByText('Start Combat')).toBeInTheDocument()
  })

  it('calls api.startCombat and updates store when Start Combat is clicked', async () => {
    vi.mocked(api.startCombat).mockResolvedValue(makeCombatResponse())
    const user = userEvent.setup()
    render(<CombatTracker />)
    await user.click(screen.getByText('Start Combat'))
    await waitFor(() => {
      expect(api.startCombat).toHaveBeenCalledWith('sess-1')
      expect(useGameStore.getState().combat).not.toBeNull()
      expect(useGameStore.getState().combat?.id).toBe('cbt-1')
    })
  })
})

describe('CombatTracker — active combat', () => {
  beforeEach(() => {
    useGameStore.setState({ combat: makeActiveCombat() })
  })

  it('shows round number in header', () => {
    render(<CombatTracker />)
    expect(screen.getByText(/Round 1/)).toBeInTheDocument()
  })

  it('renders all combatants', () => {
    const { container } = render(<CombatTracker />)
    // Use toHaveTextContent since the current-turn span renders "▶ Aragorn"
    expect(container).toHaveTextContent('Aragorn')
    expect(container).toHaveTextContent('Goblin')
  })

  it('highlights the current-turn combatant with "▶"', () => {
    const { container } = render(<CombatTracker />)
    // The current turn row prepends "▶ " before the combatant name
    expect(container.textContent).toMatch(/▶\s*Aragorn/)
  })

  it('shows HP and AC for each combatant', () => {
    render(<CombatTracker />)
    expect(screen.getByText('HP 50/50 · AC 17')).toBeInTheDocument()
    expect(screen.getByText('HP 7/7 · AC 13')).toBeInTheDocument()
  })

  it('calls api.endCombat and clears store when End is clicked', async () => {
    vi.mocked(api.endCombat).mockResolvedValue(makeCombatResponse({ ended_at: '2024-01-01T00:01:00Z' }))
    const user = userEvent.setup()
    render(<CombatTracker />)
    await user.click(screen.getByText('End'))
    await waitFor(() => {
      expect(api.endCombat).toHaveBeenCalledWith('sess-1')
      expect(useGameStore.getState().combat).toBeNull()
    })
  })

  it('shows action buttons (Attack, Dash, Dodge)', () => {
    render(<CombatTracker />)
    expect(screen.getByText('Attack')).toBeInTheDocument()
    expect(screen.getByText('Dash')).toBeInTheDocument()
    expect(screen.getByText('Dodge')).toBeInTheDocument()
  })

  it('calls api.submitAction with actor and action type', async () => {
    vi.mocked(api.submitAction).mockResolvedValue(makeCombatResponse())
    const user = userEvent.setup()
    render(<CombatTracker />)
    await user.click(screen.getByText('Attack'))
    await waitFor(() => {
      expect(api.submitAction).toHaveBeenCalledWith('sess-1', {
        actor_id: 'char-a',
        action_type: 'Attack',
      })
    })
  })

  it('calls api.nextTurn and updates combat on Next Turn click', async () => {
    const nextRound = makeCombatResponse({ round_number: 2, current_turn_index: 1 })
    vi.mocked(api.nextTurn).mockResolvedValue(nextRound)
    const user = userEvent.setup()
    render(<CombatTracker />)
    await user.click(screen.getByText('Next Turn ▶'))
    await waitFor(() => {
      expect(api.nextTurn).toHaveBeenCalledWith('sess-1')
      expect(useGameStore.getState().combat?.round_number).toBe(2)
    })
  })
})

describe('CombatTracker — combat with no combatants', () => {
  it('disables action buttons when combatant list is empty', () => {
    useGameStore.setState({
      combat: { id: 'cbt-1', round_number: 1, current_turn_index: 0, combatants: [] },
    })
    render(<CombatTracker />)
    const attackBtn = screen.getByText('Attack')
    expect(attackBtn).toBeDisabled()
  })
})
