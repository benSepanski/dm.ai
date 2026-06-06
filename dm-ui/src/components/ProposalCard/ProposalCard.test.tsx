import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ProposalCard from './ProposalCard'
import { api } from '../../api/client'
import { useGameStore } from '../../store/gameStore'
import type { ProposalData } from '../../store/gameStore'

vi.mock('../../api/client', () => ({
  api: {
    acceptProposal: vi.fn(),
    rejectProposal: vi.fn(),
  },
}))

const RESET = {
  sessionId: 'sess-1', worldId: 'world-1', messages: [], isLoading: false,
  combat: null, currentLocation: null, characters: [], proposals: [],
}

const pendingProposal: ProposalData = {
  id: 'p1',
  session_id: 'sess-1',
  world_id: 'world-1',
  type: 'character',
  content: { name: 'Gandalf', race: 'Istari', description: 'A wizard.' },
  status: 'pending',
  dm_notes: null,
  created_at: '2024-01-01T00:00:00Z',
}

function accepted(): ProposalData {
  return { ...pendingProposal, status: 'accepted', dm_notes: 'Looks good' }
}

function rejected(): ProposalData {
  return { ...pendingProposal, status: 'rejected', dm_notes: 'Not needed' }
}

beforeEach(() => {
  useGameStore.setState({ ...RESET, proposals: [pendingProposal] })
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ProposalCard — pending state', () => {
  it('shows Accept and Reject buttons', () => {
    render(<ProposalCard proposal={pendingProposal} />)
    expect(screen.getByText('Accept')).toBeInTheDocument()
    expect(screen.getByText('Reject')).toBeInTheDocument()
  })

  it('shows the proposal type label', () => {
    render(<ProposalCard proposal={pendingProposal} />)
    expect(screen.getByText('Character')).toBeInTheDocument()
  })

  it('renders content fields (name, race, description)', () => {
    render(<ProposalCard proposal={pendingProposal} />)
    expect(screen.getByText('Gandalf')).toBeInTheDocument()
    expect(screen.getByText('Istari')).toBeInTheDocument()
    expect(screen.getByText('A wizard.')).toBeInTheDocument()
  })

  it('does not show a status badge for pending proposals', () => {
    render(<ProposalCard proposal={pendingProposal} />)
    expect(screen.queryByText('Accepted')).not.toBeInTheDocument()
    expect(screen.queryByText('Rejected')).not.toBeInTheDocument()
  })
})

describe('ProposalCard — accept flow', () => {
  it('calls api.acceptProposal with the proposal id', async () => {
    vi.mocked(api.acceptProposal).mockResolvedValue(accepted())
    const user = userEvent.setup()
    render(<ProposalCard proposal={pendingProposal} />)
    await user.click(screen.getByText('Accept'))
    expect(api.acceptProposal).toHaveBeenCalledWith('p1', { dm_notes: undefined })
  })

  it('passes trimmed DM notes to acceptProposal', async () => {
    vi.mocked(api.acceptProposal).mockResolvedValue(accepted())
    const user = userEvent.setup()
    render(<ProposalCard proposal={pendingProposal} />)
    await user.type(screen.getByPlaceholderText(/DM notes/), '  Great NPC  ')
    await user.click(screen.getByText('Accept'))
    expect(api.acceptProposal).toHaveBeenCalledWith('p1', { dm_notes: 'Great NPC' })
  })

  it('updates the store after successful accept', async () => {
    vi.mocked(api.acceptProposal).mockResolvedValue(accepted())
    const user = userEvent.setup()
    render(<ProposalCard proposal={pendingProposal} />)
    await user.click(screen.getByText('Accept'))
    await waitFor(() => {
      expect(useGameStore.getState().proposals[0].status).toBe('accepted')
    })
  })

  it('shows an error message if acceptProposal throws', async () => {
    vi.mocked(api.acceptProposal).mockRejectedValue(new Error('Server down'))
    const user = userEvent.setup()
    render(<ProposalCard proposal={pendingProposal} />)
    await user.click(screen.getByText('Accept'))
    await waitFor(() => {
      expect(screen.getByText('Server down')).toBeInTheDocument()
    })
  })
})

describe('ProposalCard — reject flow', () => {
  it('calls api.rejectProposal with the proposal id', async () => {
    vi.mocked(api.rejectProposal).mockResolvedValue(rejected())
    const user = userEvent.setup()
    render(<ProposalCard proposal={pendingProposal} />)
    await user.click(screen.getByText('Reject'))
    expect(api.rejectProposal).toHaveBeenCalledWith('p1', { dm_notes: undefined })
  })

  it('shows an error message if rejectProposal throws', async () => {
    vi.mocked(api.rejectProposal).mockRejectedValue(new Error('Network error'))
    const user = userEvent.setup()
    render(<ProposalCard proposal={pendingProposal} />)
    await user.click(screen.getByText('Reject'))
    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })
})

describe('ProposalCard — resolved states', () => {
  it('shows "Accepted" badge and hides action buttons for accepted proposal', () => {
    render(<ProposalCard proposal={accepted()} />)
    expect(screen.getByText('Accepted')).toBeInTheDocument()
    expect(screen.queryByText('Accept')).not.toBeInTheDocument()
    expect(screen.queryByText('Reject')).not.toBeInTheDocument()
  })

  it('shows "Rejected" badge for rejected proposal', () => {
    render(<ProposalCard proposal={rejected()} />)
    expect(screen.getByText('Rejected')).toBeInTheDocument()
  })

  it('shows DM notes for resolved proposals', () => {
    render(<ProposalCard proposal={accepted()} />)
    expect(screen.getByText(/Looks good/)).toBeInTheDocument()
  })

  it('shows "Modified" badge for modified proposals', () => {
    const modified: ProposalData = { ...pendingProposal, status: 'modified', dm_notes: 'Changed name' }
    render(<ProposalCard proposal={modified} />)
    expect(screen.getByText('Modified')).toBeInTheDocument()
  })

  it('renders null content gracefully', () => {
    render(<ProposalCard proposal={{ ...pendingProposal, content: null }} />)
    expect(screen.getByText('No content.')).toBeInTheDocument()
  })
})
