import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AlertCard } from './AlertCard'

describe('AlertCard', () => {
  it('exibe tipo de ameaca, confianca, timestamp e severidade textual acessivel', () => {
    render(
      <AlertCard
        prediction={{
          prediction: 'DDoS',
          confidence: 0.97,
          model: 'mock-cyclic-v1',
          timestamp: '2026-07-26T13:00:00Z',
        }}
      />,
    )

    expect(screen.getByText('DDoS')).toBeInTheDocument()
    expect(screen.getByText('97%')).toBeInTheDocument()
    expect(screen.getByText('2026-07-26T13:00:00Z')).toBeInTheDocument()
    expect(screen.getByText('Crítico')).toBeInTheDocument()
  })
})
