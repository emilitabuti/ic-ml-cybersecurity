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

  it('injeta evento de demonstracao usando POST /history/demo', async () => {
    const event = {
      prediction: 'SYN Flood - High Intensity',
      confidence: 0.97,
      model: 'syn-flood-dashboard-demo-v1',
      timestamp: '2026-07-26T13:00:00Z',
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([event]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const history = await apiClient.pushDemoHistoryEvent(event)

    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/history/demo', {
      headers: { 'Content-Type': 'application/json' },
      method: 'POST',
      body: JSON.stringify(event),
    })
    expect(history).toEqual([event])
  })

  it('limpa eventos de demonstracao usando DELETE /history/demo', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const history = await apiClient.clearDemoHistory()

    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/history/demo', {
      headers: { 'Content-Type': 'application/json' },
      method: 'DELETE',
    })
    expect(history).toEqual([])
  })
})
