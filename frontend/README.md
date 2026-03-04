# Agent Tooling Frontend

A modern dashboard for the Agent Tooling multi-provider LLM framework.

## Features

- **Provider Management**: Configure and monitor LLM providers (Ollama, Anthropic, OpenAI, Google, Mistral, Groq)
- **Tool Registry**: Browse and manage registered tools with MCP and sandboxing support
- **Workspace Configuration**: Manage execution environments (Local, Docker, Remote)
- **Interactive Chat**: Chat interface with multi-provider model selection
- **Execution Logs**: Real-time monitoring of tool executions and system events

## Tech Stack

- **Framework**: SvelteKit 2.0
- **Styling**: Tailwind CSS 3.4
- **Build**: Vite 5
- **TypeScript**: Full type safety

## Getting Started

```bash
# Install dependencies
pnpm install

# Development server
pnpm dev

# Production build
pnpm build

# Preview production build
pnpm preview
```

## Project Structure

```
frontend/
├── src/
│   ├── routes/
│   │   ├── +layout.svelte    # Main layout with sidebar
│   │   ├── +page.svelte      # Dashboard
│   │   ├── chat/             # Interactive chat
│   │   ├── providers/        # LLM provider management
│   │   ├── tools/            # Tool registry
│   │   ├── workspaces/       # Workspace configuration
│   │   └── logs/             # Execution logs
│   ├── lib/
│   │   ├── components/       # Reusable components
│   │   ├── stores/           # Svelte stores
│   │   └── api/              # API client
│   ├── app.css               # Global styles + Tailwind
│   └── app.html              # HTML template
├── tailwind.config.js        # Tailwind configuration
├── svelte.config.js          # SvelteKit configuration
└── vite.config.ts            # Vite configuration
```

## Design System

### Color Palette

| Color | Usage |
|-------|-------|
| `background` | Main background (#0a0a0f) |
| `surface` | Cards and panels (#12121a) |
| `primary` | Primary accent (#6366f1) |
| `secondary` | Secondary accent (#22d3ee) |
| `success` | Success states (#22c55e) |
| `warning` | Warning states (#eab308) |
| `danger` | Error states (#ef4444) |

### Provider Colors

| Provider | Color |
|----------|-------|
| Ollama | #00d4aa |
| Anthropic | #d97706 |
| OpenAI | #10b981 |
| Google | #4285f4 |
| Mistral | #ff7000 |
| Groq | #f43f5e |

### Typography

- **Font**: Inter (sans-serif)
- **Monospace**: JetBrains Mono (code)
- **Body**: 14px / 1.5 line-height

### Components

- `btn-primary`: Primary action buttons
- `btn-secondary`: Secondary action buttons
- `btn-ghost`: Ghost/text buttons
- `btn-icon`: Icon-only buttons
- `card`: Base card component
- `card-hover`: Interactive card with hover effects
- `input`: Form inputs
- `badge`: Status badges
- `code-block`: Code snippets

## Accessibility

- Minimum 44x44px touch targets
- Visible focus states with 2px ring
- ARIA labels on icon-only buttons
- Keyboard navigation support
- Reduced motion preference respected
- Skip-to-content link

## API Integration

Currently uses mock data. To connect to the backend:

1. Create API client in `src/lib/api/`
2. Add environment variables for backend URL
3. Replace mock data with API calls

Example:

```typescript
// src/lib/api/client.ts
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function getProviders() {
  const response = await fetch(`${API_URL}/api/providers`);
  return response.json();
}
```

## Development Notes

- All components follow accessibility guidelines
- Dark mode only (optimized for developer experience)
- Responsive design (mobile-first)
- No external icon libraries (inline SVG)

---

Built with SvelteKit + Tailwind CSS
