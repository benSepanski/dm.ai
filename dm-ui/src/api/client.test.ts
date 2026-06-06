import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { api } from './client'

// Stub global fetch for each test.
function mockFetch(status: number, body: unknown): void {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      statusText: status === 200 ? 'OK' : 'Error',
      json: () => Promise.resolve(body),
      text: () => Promise.resolve(typeof body === 'string' ? body : JSON.stringify(body)),
    }),
  )
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('api error handling', () => {
  it('throws an Error with the response body on non-ok status', async () => {
    mockFetch(404, 'Not Found')
    await expect(api.getProposal('p1')).rejects.toThrow('Not Found')
  })

  it('falls back to "API <status>: <statusText>" when the body is empty', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.resolve({}),
        text: () => Promise.resolve(''),
      }),
    )
    await expect(api.getProposal('p1')).rejects.toThrow('API 500: Internal Server Error')
  })

  it('sends Content-Type: application/json header', async () => {
    mockFetch(200, { id: 'p1', status: 'pending' })
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ id: 'p1' }),
      text: () => Promise.resolve('{"id":"p1"}'),
    })
    vi.stubGlobal('fetch', fetchMock)
    await api.createWorld({ name: 'Faerun' })
    const [, opts] = fetchMock.mock.calls[0] as [string, RequestInit]
    const headers = opts.headers as Record<string, string>
    expect(headers['Content-Type']).toBe('application/json')
  })
})

describe('api.createWorld', () => {
  it('POSTs to /api/worlds/ and returns the id', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ id: 'world-1' }),
      text: () => Promise.resolve(''),
    })
    vi.stubGlobal('fetch', fetchMock)
    const result = await api.createWorld({ name: 'Faerun', setting_description: 'A magical realm' })
    expect(result).toEqual({ id: 'world-1' })
    const [url, opts] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/worlds/')
    expect(opts.method).toBe('POST')
    expect(JSON.parse(opts.body as string)).toEqual({ name: 'Faerun', setting_description: 'A magical realm' })
  })
})

describe('api.chat', () => {
  it('POSTs to /api/sessions/:id/chat with the message', async () => {
    const payload = { response: 'You enter the tavern.', proposal: null }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(payload),
      text: () => Promise.resolve(''),
    })
    vi.stubGlobal('fetch', fetchMock)
    const result = await api.chat('sess-1', 'Look around')
    expect(result).toEqual(payload)
    const [url, opts] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/sessions/sess-1/chat')
    expect(JSON.parse(opts.body as string)).toEqual({ message: 'Look around' })
  })
})

describe('api.acceptProposal', () => {
  it('POSTs to /api/ai/proposals/:id/accept with dm_notes', async () => {
    const response = { id: 'p1', status: 'accepted', dm_notes: 'Approved', world_id: 'w1', session_id: null, type: 'character', content: null, created_at: '' }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(response),
      text: () => Promise.resolve(''),
    })
    vi.stubGlobal('fetch', fetchMock)
    const result = await api.acceptProposal('p1', { dm_notes: 'Approved' })
    expect(result.status).toBe('accepted')
    const [url, opts] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/ai/proposals/p1/accept')
    expect(opts.method).toBe('POST')
    expect(JSON.parse(opts.body as string)).toEqual({ dm_notes: 'Approved' })
  })

  it('sends empty object body when called with no options', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ id: 'p1', status: 'accepted', dm_notes: null, world_id: 'w1', session_id: null, type: 'character', content: null, created_at: '' }),
      text: () => Promise.resolve(''),
    })
    vi.stubGlobal('fetch', fetchMock)
    await api.acceptProposal('p1')
    const [, opts] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(JSON.parse(opts.body as string)).toEqual({})
  })
})

describe('api.rejectProposal', () => {
  it('POSTs to /api/ai/proposals/:id/reject', async () => {
    const response = { id: 'p1', status: 'rejected', dm_notes: 'No thanks', world_id: 'w1', session_id: null, type: 'character', content: null, created_at: '' }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(response),
      text: () => Promise.resolve(''),
    })
    vi.stubGlobal('fetch', fetchMock)
    const result = await api.rejectProposal('p1', { dm_notes: 'No thanks' })
    expect(result.status).toBe('rejected')
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/ai/proposals/p1/reject')
  })
})

describe('api.startCombat', () => {
  it('POSTs to /api/sessions/:id/combat', async () => {
    const combatResponse = { id: 'cbt-1', session_id: 'sess-1', location_id: null, round_number: 1, current_turn_index: 0, initiative_order: [], combatants: [], combat_log: [], started_at: '', ended_at: null }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(combatResponse),
      text: () => Promise.resolve(''),
    })
    vi.stubGlobal('fetch', fetchMock)
    const result = await api.startCombat('sess-1')
    expect(result.id).toBe('cbt-1')
    const [url, opts] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/sessions/sess-1/combat')
    expect(opts.method).toBe('POST')
  })
})
