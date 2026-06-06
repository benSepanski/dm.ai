import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useSessionWebSocket } from './ws'
import { useGameStore } from '../store/gameStore'

// ---- Minimal WebSocket mock ----

class MockWebSocket {
  static instances: MockWebSocket[] = []
  url: string
  onmessage: ((evt: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: ((err: unknown) => void) | null = null
  closeCalled = false

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  send(_data: string) {}

  close() {
    this.closeCalled = true
  }

  /** Helper to simulate a server-push event. */
  emit(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) })
  }
}

const RESET = {
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
  MockWebSocket.instances = []
  vi.stubGlobal('WebSocket', MockWebSocket)
  useGameStore.setState(RESET)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('useSessionWebSocket', () => {
  it('does not open a connection when sessionId is null', () => {
    renderHook(() => useSessionWebSocket(null))
    expect(MockWebSocket.instances).toHaveLength(0)
  })

  it('opens a WebSocket to /ws/sessions/:id', () => {
    renderHook(() => useSessionWebSocket('sess-1'))
    expect(MockWebSocket.instances).toHaveLength(1)
    expect(MockWebSocket.instances[0].url).toBe('/ws/sessions/sess-1')
  })

  it('closes the WebSocket on unmount', () => {
    const { unmount } = renderHook(() => useSessionWebSocket('sess-1'))
    unmount()
    expect(MockWebSocket.instances[0].closeCalled).toBe(true)
  })

  it('adds an ai chat_message to the store', () => {
    renderHook(() => useSessionWebSocket('sess-1'))
    act(() => {
      MockWebSocket.instances[0].emit({
        type: 'chat_message',
        session_id: 'sess-1',
        role: 'ai',
        content: 'You see a dragon.',
      })
    })
    const messages = useGameStore.getState().messages
    expect(messages).toHaveLength(1)
    expect(messages[0].role).toBe('ai')
    expect(messages[0].content).toBe('You see a dragon.')
  })

  it('ignores chat_message events with non-ai roles', () => {
    renderHook(() => useSessionWebSocket('sess-1'))
    act(() => {
      MockWebSocket.instances[0].emit({
        type: 'chat_message',
        session_id: 'sess-1',
        role: 'system',
        content: 'Combat started.',
      })
    })
    expect(useGameStore.getState().messages).toHaveLength(0)
  })

  it('updates combat state on combat_update', () => {
    renderHook(() => useSessionWebSocket('sess-1'))
    act(() => {
      MockWebSocket.instances[0].emit({
        type: 'combat_update',
        session_id: 'sess-1',
        combat: {
          id: 'cbt-1',
          round_number: 3,
          current_turn_index: 1,
          initiative_order: [
            { character_id: 'char-a', name: 'Aragorn', initiative: 18 },
            { character_id: 'char-b', name: 'Goblin', initiative: 12 },
          ],
          combatants: [
            { id: 'char-a', name: 'Aragorn', hp_current: 40, hp_max: 50, ac: 18, speed: 30, level: 5, conditions: [], condition_durations: {} },
            { id: 'char-b', name: 'Goblin', hp_current: 5, hp_max: 7, ac: 13, speed: 30, level: 1, conditions: [], condition_durations: {} },
          ],
          combat_log: [],
          started_at: '',
          ended_at: null,
          session_id: 'sess-1',
          location_id: null,
        },
      })
    })
    const combat = useGameStore.getState().combat
    expect(combat).not.toBeNull()
    expect(combat!.id).toBe('cbt-1')
    expect(combat!.round_number).toBe(3)
    expect(combat!.combatants).toHaveLength(2)
    expect(combat!.combatants[1].is_current_turn).toBe(true)
    expect(combat!.combatants[0].is_current_turn).toBe(false)
  })

  it('fetches and stores a pending proposal on proposal_ready', async () => {
    const proposalData = {
      id: 'p1', session_id: 'sess-1', world_id: 'w1', type: 'character',
      content: { name: 'Bilbo' }, status: 'pending', dm_notes: null, created_at: '',
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(proposalData),
        text: () => Promise.resolve(''),
      }),
    )

    renderHook(() => useSessionWebSocket('sess-1'))
    await act(async () => {
      MockWebSocket.instances[0].emit({
        type: 'proposal_ready',
        session_id: 'sess-1',
        proposal_id: 'p1',
        proposal_type: 'character',
        status: 'pending',
      })
    })
    expect(useGameStore.getState().proposals).toHaveLength(1)
    expect(useGameStore.getState().proposals[0].id).toBe('p1')
  })

  it('updates an existing proposal status on non-pending proposal_ready', () => {
    useGameStore.setState({
      proposals: [{
        id: 'p1', session_id: 'sess-1', world_id: 'w1', type: 'character',
        content: null, status: 'pending', dm_notes: null, created_at: '',
      }],
    })
    renderHook(() => useSessionWebSocket('sess-1'))
    act(() => {
      MockWebSocket.instances[0].emit({
        type: 'proposal_ready',
        session_id: 'sess-1',
        proposal_id: 'p1',
        proposal_type: 'character',
        status: 'accepted',
      })
    })
    expect(useGameStore.getState().proposals[0].status).toBe('accepted')
  })

  it('silently drops malformed JSON messages', () => {
    renderHook(() => useSessionWebSocket('sess-1'))
    act(() => {
      MockWebSocket.instances[0].onmessage?.({ data: 'not valid json{{' })
    })
    expect(useGameStore.getState().messages).toHaveLength(0)
  })
})
