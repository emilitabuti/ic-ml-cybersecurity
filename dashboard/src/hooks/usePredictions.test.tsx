import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { POLLING_INTERVAL_MS } from '@/config'
import { apiClient } from '@/services/api'
import { usePredictions } from './usePredictions'

describe('usePredictions', () => {
  it('configura polling com POLLING_INTERVAL_MS', () => {
    const queryClient = new QueryClient()
    vi.spyOn(apiClient, 'getPredictionHistory').mockResolvedValue([])

    function wrapper({ children }: PropsWithChildren) {
      return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    }

    renderHook(() => usePredictions(), { wrapper })

    const query = queryClient.getQueryCache().find({ queryKey: ['predictions', 'history'] })
    const options = query?.options as { refetchInterval?: unknown } | undefined

    expect(options?.refetchInterval).toBe(POLLING_INTERVAL_MS)
  })
})
