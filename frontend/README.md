# AI Agent Orchestration Platform - Frontend

A modern Next.js application for managing and orchestrating AI agents.

## Features

- **Next.js 14** with App Router
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **shadcn/ui** components
- **Authentication** with JWT tokens
- **Responsive design** with mobile support
- **Dark/light theme** support

## Tech Stack

- **Frontend**: Next.js 14, React 18, TypeScript
- **Styling**: Tailwind CSS, PostCSS
- **Components**: shadcn/ui (Radix UI)
- **HTTP Client**: Axios
- **Forms**: React Hook Form + Zod
- **Icons**: Lucide React

## Project Structure

```
frontend/
├── app/
│   ├── page.tsx                 # Main application page
│   ├── components/              # Reusable UI components
│   ├── features/               # Feature-specific components
│   ├── lib/                    # Utility functions and API client
│   └── hooks/                  # Custom React hooks
├── public/                     # Static assets
├── next.config.js              # Next.js configuration
├── tailwind.config.js          # Tailwind CSS configuration
├── tsconfig.json               # TypeScript configuration
└── package.json                # Dependencies and scripts
```

## Getting Started

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Set up environment variables:
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local with your API URL
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## Development

### Adding Components

Use the component generator to create new components:

```bash
npx create-next-app@latest --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
```

### API Integration

The API client is configured in `app/lib/api.ts`. Authentication tokens are automatically included in requests.

### Environment Variables

Key environment variables:

- `NEXT_PUBLIC_API_URL` - Backend API URL
- `NEXTAUTH_SECRET` - Authentication secret
- `NEXTAUTH_URL` - Application URL

## Authentication

- JWT tokens are stored in localStorage
- Automatic token refresh on 401 responses
- Protected routes redirect to login
- User state is managed with custom hooks

## Deployment

### Vercel

1. Connect your repository to Vercel
2. Set environment variables in Vercel dashboard
3. Deploy automatically on push to main branch

### Docker

```bash
# Build image
docker build -t ai-agent-platform-frontend .

# Run container
docker run -p 3000:3000 ai-agent-platform-frontend
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.