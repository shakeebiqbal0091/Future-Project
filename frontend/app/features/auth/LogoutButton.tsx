'use client'

import { User } from '@/lib/auth'
import { Button } from '@/components/Button'
import { useRouter } from 'next/navigation'
import { authService } from '@/lib/auth'

interface LogoutButtonProps {
  user?: User
  className?: string
}

export const LogoutButton = ({ user, className = '' }: LogoutButtonProps) => {
  const router = useRouter()

  const handleLogout = async () => {
    await authService.logout()
    router.push('/login')
  }

  return (
    <Button
      onClick={handleLogout}
      className={`text-sm ${className}`}
      variant="outline"
    >
      Logout
    </Button>
  )
}