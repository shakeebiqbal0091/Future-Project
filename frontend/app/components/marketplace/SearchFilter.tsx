'use client'

import { Input } from '@/components/Input'

interface SearchFilterProps {
  value: string
  onChange: (value: string) => void
}

export function SearchFilter({ value, onChange }: SearchFilterProps) {
  return (
    <Input
      placeholder="Search agents..."
      value={value}
      onChange={onChange}
      className="w-full"
      leftIcon="🔍"
    />
  )
}