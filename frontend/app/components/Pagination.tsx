'use client'

import { Button } from '@/components/Button'
import { ChevronLeftIcon } from '@/components/icons/ChevronLeftIcon'
import { ChevronRightIcon } from '@/components/icons/ChevronRightIcon'

interface PaginationProps {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
}

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  const isFirstPage = currentPage === 1
  const isLastPage = currentPage === totalPages

  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages && page !== currentPage) {
      onPageChange(page)
    }
  }

  return (
    <div className="flex items-center justify-between p-4 bg-white rounded-lg shadow-sm">
      <div className="flex items-center space-x-4">
        <Button
          variant="outline"
          size="sm"
          disabled={isFirstPage}
          onClick={() => goToPage(currentPage - 1)}
        >
          <ChevronLeftIcon className="w-4 h-4" />
          Previous
        </Button>

        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-600">
            Page {currentPage} of {totalPages}
          </span>
        </div>

        <Button
          variant="outline"
          size="sm"
          disabled={isLastPage}
          onClick={() => goToPage(currentPage + 1)}
        >
          Next
          <ChevronRightIcon className="w-4 h-4" />
        </Button>
      </div>

      <div className="flex items-center space-x-4">
        <span className="text-sm text-gray-500">
          {totalPages > 1 ? 'Showing agents' : 'Showing agent'}
        </span>
      </div>
    </div>
  )
}