<script lang="ts">
  const providers = [
    { 
      name: 'Ollama', 
      models: ['qwen3-coder', 'mistral-small3.2', 'llama3.2', 'codellama'],
      status: 'connected',
      color: 'ollama',
      env: 'OLLAMA_BASE_URL',
      default: 'http://localhost:11434',
      description: 'Local Ollama models - no API key required'
    },
    { 
      name: 'Anthropic', 
      models: ['claude-sonnet-4-20250514', 'claude-opus-4', 'claude-3.5-sonnet'],
      status: 'connected',
      color: 'anthropic',
      env: 'ANTHROPIC_API_KEY',
      description: 'Anthropic Claude models'
    },
    { 
      name: 'OpenAI', 
      models: ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'],
      status: 'disconnected',
      color: 'openai',
      env: 'OPENAI_API_KEY',
      description: 'OpenAI GPT models'
    },
    { 
      name: 'Google', 
      models: ['gemini-pro', 'gemini-1.5-pro', 'gemini-1.5-flash'],
      status: 'connected',
      color: 'google',
      env: 'GOOGLE_API_KEY',
      description: 'Google Gemini models'
    },
    { 
      name: 'Mistral', 
      models: ['mistral-large-latest', 'mistral-medium', 'codestral-latest'],
      status: 'disconnected',
      color: 'mistral',
      env: 'MISTRAL_API_KEY',
      description: 'Mistral AI models'
    },
    { 
      name: 'Groq', 
      models: ['llama-3.3-70b-versatile', 'mixtral-8x7b-32768', 'gemma2-9b-it'],
      status: 'connected',
      color: 'groq',
      env: 'GROQ_API_KEY',
      description: 'Groq - ultra-fast inference'
    }
  ];
</script>

<svelte:head>
  <title>Providers | Agent Tooling</title>
</svelte:head>

<div class="space-y-6">
  <div>
    <h1 class="text-xl font-semibold text-on_background">LLM Providers</h1>
    <p class="text-sm text-on_surface_alt">Configure and manage multi-provider LLM support</p>
  </div>

  <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
    {#each providers as provider}
      <div class="card-hover">
        <div class="flex items-start justify-between mb-3">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-accent-{provider.color}/20 flex items-center justify-center">
              <div class="w-3 h-3 rounded-full bg-accent-{provider.color}"></div>
            </div>
            <div>
              <h3 class="font-semibold text-on_background">{provider.name}</h3>
              <span class="badge badge-{provider.status === 'connected' ? 'success' : 'danger'}">
                {provider.status}
              </span>
            </div>
          </div>
        </div>
        
        <p class="text-sm text-on_surface_alt mb-3">{provider.description}</p>
        
        <div class="space-y-2">
          <div class="flex items-center gap-2 text-sm">
            <span class="text-on_surface_alt">Env:</span>
            <code class="text-xs bg-background px-2 py-1 rounded text-on_background font-mono">{provider.env}</code>
          </div>
          
          <div class="text-sm">
            <span class="text-on_surface_alt">Models:</span>
            <div class="flex flex-wrap gap-1 mt-1">
              {#each provider.models.slice(0, 3) as model}
                <span class="text-xs bg-surface_alt px-2 py-0.5 rounded text-on_surface">{model}</span>
              {/each}
              {#if provider.models.length > 3}
                <span class="text-xs text-on_surface_alt">+{provider.models.length - 3} more</span>
              {/if}
            </div>
          </div>
        </div>
        
        <div class="divider"></div>
        
        <div class="flex gap-2">
          <button class="btn-secondary flex-1 text-sm">Configure</button>
          <button class="btn-ghost text-sm">Test</button>
        </div>
      </div>
    {/each}
  </div>

  <!-- CLI Reference -->
  <div class="card">
    <h3 class="text-lg font-semibold text-on_background mb-4">CLI Reference</h3>
    <div class="code-block text-sm space-y-2">
      <div><span class="text-on_surface_alt"># Chat with any provider</span></div>
      <div><span class="text-secondary">agent-tooling</span> --chat --model <span class="text-warning">ollama/qwen3-coder</span></div>
      <div><span class="text-secondary">agent-tooling</span> --chat --model <span class="text-warning">anthropic/claude-sonnet-4</span></div>
      <div><span class="text-secondary">agent-tooling</span> --chat --model <span class="text-warning">openai/gpt-4o</span></div>
      <div class="mt-4"><span class="text-on_surface_alt"># List all providers</span></div>
      <div><span class="text-secondary">agent-tooling</span> --providers</div>
    </div>
  </div>
</div>
