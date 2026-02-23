'use client'

import { User } from '@/lib/auth'
import { Button } from '@/components/Button'
import { useRouter } from 'next/navigation'

interface RegisterButtonProps {
  className?: string
}

export const RegisterButton = ({ className = '' }: RegisterButtonProps) => {
  const router = useRouter()

  const handleRegister = () => {
    router.push('/register')
  }

  return (
    <Button
      onClick={handleRegister}
      className={`text-sm ${className}`}
    >
      Sign Up
    </Button>
  )
}