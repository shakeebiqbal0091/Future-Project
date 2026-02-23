import { useState, useEffect } from 'react'
import { authService, getAuthToken } from '@/lib/auth'
import { useRouter } from 'next/navigation'

interface User {
  id: string
  email: string
  name: string
  role: string
  createdAt: string
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
}

export const useAuth = (): AuthState => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  })
  const router = useRouter()

  useEffect(() => {
    const checkAuth = async () => {
      const token = getAuthToken()
      if (token) {
        try {
          const user = await authService.getCurrentUser()
          setAuthState({
            user,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error) {
          setAuthState({
            user: null,
            isAuthenticated: false,
            isLoading: false,
          })
        }
      } else {
        setAuthState(prev => ({
          ...prev,
          isLoading: false,
        }))
      }
    }

    checkAuth()
  }, [])

  return authState
}