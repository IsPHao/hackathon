import { useEffect } from 'react'

interface KeyBinding {
  key: string
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  callback: () => void
}

export const useKeyboardShortcut = (bindings: KeyBinding[]) => {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      bindings.forEach(binding => {
        const ctrlMatch = binding.ctrl ? event.ctrlKey || event.metaKey : !event.ctrlKey && !event.metaKey
        const shiftMatch = binding.shift ? event.shiftKey : !event.shiftKey
        const altMatch = binding.alt ? event.altKey : !event.altKey
        const keyMatch = event.key.toLowerCase() === binding.key.toLowerCase()

        if (ctrlMatch && shiftMatch && altMatch && keyMatch) {
          event.preventDefault()
          binding.callback()
        }
      })
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [bindings])
}

export const SHORTCUTS = {
  REGENERATE: { key: 'r', ctrl: true, description: 'Ctrl+R: 重新生成' },
  SAVE: { key: 's', ctrl: true, description: 'Ctrl+S: 保存' },
  DOWNLOAD: { key: 'd', ctrl: true, description: 'Ctrl+D: 下载' },
  UNDO: { key: 'z', ctrl: true, description: 'Ctrl+Z: 撤销' },
  HELP: { key: '/', shift: true, description: 'Shift+/: 帮助' },
}
