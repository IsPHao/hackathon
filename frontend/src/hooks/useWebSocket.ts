import { useEffect, useRef, useState, useCallback } from 'react'
import type { ProgressResponse } from '../types'

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 
  (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host

interface UseWebSocketOptions {
  taskId: string
  onMessage?: (data: ProgressResponse) => void
  enabled?: boolean
}

export function useWebSocket({ taskId, onMessage, enabled = true }: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const onMessageRef = useRef(onMessage)

  useEffect(() => {
    onMessageRef.current = onMessage
  }, [onMessage])

  const connect = useCallback(() => {
    if (!enabled || !taskId) return

    const wsUrl = `${WS_BASE_URL}/api/v1/novels/${taskId}/ws`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      console.log('WebSocket connected:', wsUrl)
    }

    ws.onmessage = (event) => {
      try {
        const data: ProgressResponse = JSON.parse(event.data)
        onMessageRef.current?.(data)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      setIsConnected(false)
      console.log('WebSocket disconnected')
    }
  }, [taskId, enabled])

  useEffect(() => {
    connect()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connect])

  return {
    isConnected,
  }
}
