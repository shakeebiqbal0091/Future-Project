import { NextRequest, NextResponse } from 'next/server'

const mockAgents = [
  {
    id: '1',
    name: 'GPT-4 Agent',
    description: 'Advanced language model agent',
    type: 'language-model',
    status: 'active',
    capabilities: ['text-generation', 'code-completion', 'chat'],
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z'
  },
  {
    id: '2',
    name: 'Image Analysis Agent',
    description: 'Computer vision agent',
    type: 'vision',
    status: 'active',
    capabilities: ['image-classification', 'object-detection', 'facial-recognition'],
    created_at: '2024-01-16T14:30:00Z',
    updated_at: '2024-01-16T14:30:00Z'
  },
  {
    id: '3',
    name: 'Data Processing Agent',
    description: 'Data analysis and processing',
    type: 'data',
    status: 'inactive',
    capabilities: ['data-cleaning', 'statistical-analysis', 'report-generation'],
    created_at: '2024-01-17T09:15:00Z',
    updated_at: '2024-01-17T09:15:00Z'
  }
]

export async function GET(request: NextRequest) {
  try {
    const search = request.nextUrl.searchParams.get('search')
    const type = request.nextUrl.searchParams.get('type')
    const status = request.nextUrl.searchParams.get('status')
    const page = parseInt(request.nextUrl.searchParams.get('page') || '1')
    const limit = parseInt(request.nextUrl.searchParams.get('limit') || '10')

    let results = mockAgents

    if (search) {
      results = results.filter(agent =>
        agent.name.toLowerCase().includes(search.toLowerCase()) ||
        agent.description.toLowerCase().includes(search.toLowerCase())
      )
    }

    if (type) {
      results = results.filter(agent => agent.type === type)
    }

    if (status) {
      results = results.filter(agent => agent.status === status)
    }

    const total = results.length
    const startIndex = (page - 1) * limit
    const endIndex = startIndex + limit
    const paginatedResults = results.slice(startIndex, endIndex)

    return NextResponse.json({
      agents: paginatedResults,
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