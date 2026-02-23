import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { email, password, name } = await request.json()

    // TODO: Implement actual user registration
    return NextResponse.json({
      user: {
        id: '1',
        email,
        name,
        role: 'user',
        token: 'mock-jwt-token'
      }
    })
  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}