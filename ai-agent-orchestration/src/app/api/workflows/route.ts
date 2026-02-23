import { NextRequest, NextResponse } from 'next/server'

const mockWorkflows = [
  {
    id: '1',
    name: 'Content Generation Pipeline',
    description: 'Automated content creation workflow',
    status: 'active',
    agents: ['1', '2'],
    triggers: ['schedule', 'webhook'],
    created_at: '2024-01-20T08:30:00Z',
    updated_at: '2024-01-22T14:45:00Z'
  },
  {
    id: '2',
    name: 'Data Analysis Workflow',
    description: 'Automated data processing and analysis',
    status: 'active',
    agents: ['3'],
    triggers: ['schedule'],
    created_at: '2024-01-21T11:20:00Z',
    updated_at: '2024-01-21T11:20:00Z'
  },
  {
    id: '3',
    name: 'Customer Support Automation',
    description: 'Automated customer support workflow',
    status: 'inactive',
    agents: ['1', '2'],
    triggers: ['webhook', 'email'],
    created_at: '2024-01-22T16:10:00Z',
    updated_at: '2024-01-22T16:10:00Z'
  }
]

export async function GET(request: NextRequest) {
  try {
    const search = request.nextUrl.searchParams.get('search')
    const status = request.nextUrl.searchParams.get('status')
    const page = parseInt(request.nextUrl.searchParams.get('page') || '1')
    const limit = parseInt(request.nextUrl.searchParams.get('limit') || '10')

    let results = mockWorkflows

    if (search) {
      results = results.filter(workflow =
        workflow.name.toLowerCase().includes(search.toLowerCase()) ||
        workflow.description.toLowerCase().includes(search.toLowerCase())
      )
    }

    if (status) {
      results = results.filter(workflow => workflow.status === status)
    }

    const total = results.length
    const startIndex = (page - 1) * limit
    const endIndex = startIndex + limit
    const paginatedResults = results.slice(startIndex, endIndex)

    return NextResponse.json({
      workflows: paginatedResults,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit)
      }
    })
  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}