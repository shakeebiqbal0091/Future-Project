'use client'

import { User } from '@/lib/auth'
import { Button } from '@/components/Button'
import { useRouter } from 'next/navigation'

interface LoginButtonProps {
  className?: string
}

export const LoginButton = ({ className = '' }: LoginButtonProps) => {
  const router = useRouter()

  const handleLogin = () => {
    router.push('/login')
  }

  return (
    <Button
      onClick={handleLogin}
      className={`text-sm ${className}`}
    >
      Login
    </Button>
  )
}