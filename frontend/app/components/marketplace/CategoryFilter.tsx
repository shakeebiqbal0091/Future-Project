'use client'

import { useState } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/Select'

interface CategoryFilterProps {
  selectedCategory: string
  onCategoryChange: (category: string) => void
}

export function CategoryFilter({ selectedCategory, onCategoryChange }: CategoryFilterProps) {
  const categories = [
    { id: 'all', name: 'All Categories' },
    { id: 'sales', name: 'Sales & Marketing' },
    { id: 'support', name: 'Customer Support' },
    { id: 'operations', name: 'Operations' },
    { id: 'hr', name: 'HR & Recruiting' },
    { id: 'finance', name: 'Finance & Accounting' },
    { id: 'it', name: 'IT & Development' },
    { id: 'analytics', name: 'Analytics & Data' },
    { id: 'productivity', name: 'Productivity' },
    { id: 'custom', name: 'Custom Solutions' },
  ]

  const handleChange = (category: string) => {
    onCategoryChange(category)
  }

  return (
    <Select value={selectedCategory} onValueChange={handleChange}>
      <SelectTrigger className="w-full">
        <SelectValue placeholder="All Categories" />
      </SelectTrigger>
      <SelectContent className="w-60">
        {categories.map((category) => (
          <SelectItem
            key={category.id}
            value={category.id}
            className="capitalize"
          >
            {category.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}