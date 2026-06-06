import { describe, it, expect, beforeEach } from 'vitest'
import { useGameStore } from './gameStore'
import type { ChatMessage, CharacterData, ProposalData, ActiveCombat, LocationData } from './gameStore'

// Partial state reset — Zustand v5's overloaded setState has two signatures; using
// Partial avoids the Parameters<> trick picking the wrong (full-replace) overload.
const RESET: Partial<ReturnType<typeof useGameStore.getState>> = {
  sessionId: null,
  worldId: null,
  messages: [],
  isLoading: false,
  combat: null,
  currentLocation: null,
  characters: [],
  proposals: [],
}

beforeEach(() => {
  useGameStore.setState(RESET)
})

describe('setSession', () => {
  it('sets sessionId and worldId', () => {
    useGameStore.getState().setSession('sess-1', 'world-1')
    const { sessionId, worldId } = useGameStore.getState()
    expect(sessionId).toBe('sess-1')
    expect(worldId).toBe('world-1')
  })
})

describe('addMessage', () => {
  it('appends a message to the empty list', () => {
    const msg: ChatMessage = { id: 'm1', role: 'dm', content: 'Hello', timestamp: '2024-01-01T00:00:00Z' }
    useGameStore.getState().addMessage(msg)
    expect(useGameStore.getState().messages).toEqual([msg])
  })

  it('preserves existing messages', () => {
    const m1: ChatMessage = { id: 'm1', role: 'dm', content: 'A', timestamp: '2024-01-01T00:00:00Z' }
    const m2: ChatMessage = { id: 'm2', role: 'ai', content: 'B', timestamp: '2024-01-01T00:00:01Z' }
    useGameStore.getState().addMessage(m1)
    useGameStore.getState().addMessage(m2)
    expect(useGameStore.getState().messages).toHaveLength(2)
    expect(useGameStore.getState().messages[1]).toEqual(m2)
  })
})

describe('setLoading', () => {
  it('sets isLoading to true then false', () => {
    useGameStore.getState().setLoading(true)
    expect(useGameStore.getState().isLoading).toBe(true)
    useGameStore.getState().setLoading(false)
    expect(useGameStore.getState().isLoading).toBe(false)
  })
})

describe('setCombat', () => {
  it('sets active combat', () => {
    const combat: ActiveCombat = {
      id: 'c1',
      round_number: 2,
      current_turn_index: 0,
      combatants: [],
    }
    useGameStore.getState().setCombat(combat)
    expect(useGameStore.getState().combat).toEqual(combat)
  })

  it('clears combat when set to null', () => {
    const combat: ActiveCombat = { id: 'c1', round_number: 1, current_turn_index: 0, combatants: [] }
    useGameStore.getState().setCombat(combat)
    useGameStore.getState().setCombat(null)
    expect(useGameStore.getState().combat).toBeNull()
  })
})

describe('setLocation', () => {
  it('sets the current location', () => {
    const loc: LocationData = { id: 'l1', name: 'Tavern', type: 'building', description: 'A cozy inn.' }
    useGameStore.getState().setLocation(loc)
    expect(useGameStore.getState().currentLocation).toEqual(loc)
  })

  it('clears location when set to null', () => {
    const loc: LocationData = { id: 'l1', name: 'Tavern', type: 'building', description: null }
    useGameStore.getState().setLocation(loc)
    useGameStore.getState().setLocation(null)
    expect(useGameStore.getState().currentLocation).toBeNull()
  })
})

describe('setCharacters', () => {
  it('replaces the entire characters list', () => {
    const chars: CharacterData[] = [
      { id: 'c1', name: 'Frodo', char_class: 'Ranger', race: 'Hobbit', level: 5, hp_current: 30, hp_max: 30, ac: 14, stats: null },
    ]
    useGameStore.getState().setCharacters(chars)
    expect(useGameStore.getState().characters).toEqual(chars)
  })
})

describe('upsertCharacter', () => {
  const base: CharacterData = {
    id: 'c1', name: 'Gandalf', char_class: 'Wizard', race: 'Istari', level: 20,
    hp_current: 80, hp_max: 80, ac: 12, stats: null,
  }

  it('adds a new character when not present', () => {
    useGameStore.getState().upsertCharacter(base)
    expect(useGameStore.getState().characters).toEqual([base])
  })

  it('updates an existing character in-place by id', () => {
    useGameStore.getState().upsertCharacter(base)
    const updated = { ...base, hp_current: 40 }
    useGameStore.getState().upsertCharacter(updated)
    expect(useGameStore.getState().characters).toHaveLength(1)
    expect(useGameStore.getState().characters[0].hp_current).toBe(40)
  })

  it('does not affect other characters when updating', () => {
    const other: CharacterData = { ...base, id: 'c2', name: 'Aragorn' }
    useGameStore.getState().upsertCharacter(base)
    useGameStore.getState().upsertCharacter(other)
    useGameStore.getState().upsertCharacter({ ...base, hp_current: 10 })
    const chars = useGameStore.getState().characters
    expect(chars).toHaveLength(2)
    expect(chars.find((c) => c.id === 'c1')?.hp_current).toBe(10)
    expect(chars.find((c) => c.id === 'c2')?.name).toBe('Aragorn')
  })
})

describe('addProposal', () => {
  const proposal: ProposalData = {
    id: 'p1', session_id: 's1', world_id: 'w1', type: 'character',
    content: { name: 'Bilbo' }, status: 'pending', dm_notes: null, created_at: '2024-01-01T00:00:00Z',
  }

  it('adds a new proposal', () => {
    useGameStore.getState().addProposal(proposal)
    expect(useGameStore.getState().proposals).toEqual([proposal])
  })

  it('replaces an existing proposal with the same id', () => {
    useGameStore.getState().addProposal(proposal)
    const updated = { ...proposal, status: 'accepted' as const }
    useGameStore.getState().addProposal(updated)
    expect(useGameStore.getState().proposals).toHaveLength(1)
    expect(useGameStore.getState().proposals[0].status).toBe('accepted')
  })
})

describe('updateProposal', () => {
  const proposal: ProposalData = {
    id: 'p1', session_id: 's1', world_id: 'w1', type: 'location',
    content: null, status: 'pending', dm_notes: null, created_at: '2024-01-01T00:00:00Z',
  }

  it('merges partial updates into the matching proposal', () => {
    useGameStore.getState().addProposal(proposal)
    useGameStore.getState().updateProposal('p1', { status: 'rejected', dm_notes: 'Not needed' })
    const p = useGameStore.getState().proposals[0]
    expect(p.status).toBe('rejected')
    expect(p.dm_notes).toBe('Not needed')
    expect(p.type).toBe('location')
  })

  it('leaves other proposals untouched', () => {
    const other: ProposalData = { ...proposal, id: 'p2', status: 'pending' }
    useGameStore.getState().addProposal(proposal)
    useGameStore.getState().addProposal(other)
    useGameStore.getState().updateProposal('p1', { status: 'accepted' })
    const p2 = useGameStore.getState().proposals.find((p) => p.id === 'p2')
    expect(p2?.status).toBe('pending')
  })

  it('is a no-op when the id does not exist', () => {
    useGameStore.getState().addProposal(proposal)
    useGameStore.getState().updateProposal('does-not-exist', { status: 'accepted' })
    expect(useGameStore.getState().proposals[0].status).toBe('pending')
  })
})
