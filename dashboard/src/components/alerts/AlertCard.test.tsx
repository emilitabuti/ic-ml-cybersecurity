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

  it('trata predicao BENIGN da API real como trafego seguro', () => {
    render(
      <AlertCard
        prediction={{
          prediction: 'BENIGN',
          confidence: 0.99,
          model: 'random_forest',
          timestamp: '2026-07-29T13:00:00Z',
        }}
      />,
    )

    expect(screen.getByText('BENIGN')).toBeInTheDocument()
    expect(screen.getByText('Seguro')).toBeInTheDocument()
  })

  it('nao marca ataque de baixa confianca como seguro', () => {
    render(
      <AlertCard
        prediction={{
          prediction: 'Attack',
          confidence: 0.66,
          model: 'random_forest',
          timestamp: '2026-07-29T13:05:00Z',
        }}
      />,
    )

    expect(screen.getByText('Attack')).toBeInTheDocument()
    expect(screen.getByText('Informativo')).toBeInTheDocument()
  })
})
