import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './api'

describe('apiClient', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('busca historico de predicoes usando GET /history', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            prediction: 'DDoS',
            confidence: 0.97,
            model: 'mock-cyclic-v1',
            timestamp: '2026-07-26T13:00:00Z',
          },
        ]),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    const history = await apiClient.getPredictionHistory()

    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/history', {
      headers: { 'Content-Type': 'application/json' },
    })
    expect(history).toHaveLength(1)
    expect(history[0]).toMatchObject({ prediction: 'DDoS', confidence: 0.97 })
  })
})
