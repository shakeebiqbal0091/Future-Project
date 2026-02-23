'use client'

import { useState } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/Select'

interface PriceFilterProps {
  selectedPriceRange: string
  onPriceChange: (priceRange: string) => void
}

export function PriceFilter({ selectedPriceRange, onPriceChange }: PriceFilterProps) {
  const priceRanges = [
    { id: 'all', name: 'All Prices' },
    { id: 'free', name: 'Free' },
    { id: 'low', name: '$1 - $50' },
    { id: 'medium', name: '$51 - $200' },
    { id: 'high', name: '$201 - $500' },
    { id: 'premium', name: '$500+' },
  ]

  const handleChange = (priceRange: string) => {
    onPriceChange(priceRange)
  }

  return (
    <Select value={selectedPriceRange} onValueChange={handleChange}>
      <SelectTrigger className="w-full">
        <SelectValue placeholder="All Prices" />
      </SelectTrigger>
      <SelectContent className="w-48">
        {priceRanges.map((range) => (
          <SelectItem key={range.id} value={range.id}>
            {range.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}