import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import LocationPanel from './LocationPanel'
import { useGameStore } from '../../store/gameStore'

const RESET = {
  sessionId: null, worldId: null, messages: [], isLoading: false,
  combat: null, currentLocation: null, characters: [], proposals: [],
}

beforeEach(() => {
  useGameStore.setState(RESET)
})

describe('LocationPanel', () => {
  it('shows placeholder when no location is set', () => {
    render(<LocationPanel />)
    expect(screen.getByText('No location set.')).toBeInTheDocument()
  })

  it('shows the location name and type badge', () => {
    useGameStore.setState({
      currentLocation: { id: 'l1', name: 'The Prancing Pony', type: 'building', description: null },
    })
    render(<LocationPanel />)
    expect(screen.getByText('The Prancing Pony')).toBeInTheDocument()
    expect(screen.getByText('building')).toBeInTheDocument()
  })

  it('renders description when present', () => {
    useGameStore.setState({
      currentLocation: { id: 'l1', name: 'Mirkwood', type: 'wilderness', description: 'Dark ancient forest.' },
    })
    render(<LocationPanel />)
    expect(screen.getByText('Dark ancient forest.')).toBeInTheDocument()
  })

  it('does not render a description element when description is null', () => {
    useGameStore.setState({
      currentLocation: { id: 'l1', name: 'The Shire', type: 'region', description: null },
    })
    render(<LocationPanel />)
    // Name and type are present; no description paragraph.
    expect(screen.getByText('The Shire')).toBeInTheDocument()
    const paragraphs = document.querySelectorAll('p')
    expect(paragraphs).toHaveLength(0)
  })
})
