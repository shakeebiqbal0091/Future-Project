import { useState, useEffect } from 'react'

interface ThemeState {
  theme: 'light' | 'dark'
  toggleTheme: () => void
}

export const useTheme = (): ThemeState => {
  const [theme, setTheme] = useState<'light' | 'dark'>('light')

  const setMode = (mode: 'light' | 'dark') => {
    window.localStorage.setItem('theme', mode)
    setTheme(mode)
  }

  const toggleTheme = () => {
    if (theme === 'light') {
      setMode('dark')
    } else {
      setMode('light')
    }
  }

  useEffect(() => {
    const localTheme = window.localStorage.getItem('theme') as 'light' | 'dark' | null
    if (localTheme) {
      setTheme(localTheme)
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      setMode('dark')
    } else {
      setMode('light')
    }
  }, [])

  return { theme, toggleTheme }
}