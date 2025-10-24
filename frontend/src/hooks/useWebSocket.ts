import { useEffect, useRef, useState } from 'react'
import type { ProgressMessage } from '../types'

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 
  (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host

interface UseWebSocketOptions {
  projectId: string
  onMessage?: (message: ProgressMessage) => void
  enabled?: boolean
}

export function useWebSocket({ projectId, onMessage, enabled = true }: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<ProgressMessage | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!enabled || !projectId) return

    const ws = new WebSocket(`${WS_BASE_URL}/ws/projects/${projectId}`)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const message: ProgressMessage = JSON.parse(event.data)
        setLastMessage(message)
        onMessage?.(message)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      setIsConnected(false)
    }

    return () => {
      ws.close()
    }
  }, [projectId, enabled, onMessage])

  return {
    isConnected,
    lastMessage,
  }
}
