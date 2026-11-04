<script lang="ts">
  // Seed data. In production this comes from the agent-tooling API.
  const providers = [
    {
      name: 'Ollama',
      models: ['qwen3-coder', 'mistral-small3.2', 'llama3.2', 'codellama'],
      status: 'up',
      color: 'ollama',
      env: 'OLLAMA_BASE_URL',
      default: 'http://localhost:11434'
    },
    {
      name: 'Anthropic',
      models: ['claude-sonnet-4-20250514', 'claude-opus-4', 'claude-3.5-sonnet'],
      status: 'up',
      color: 'anthropic',
      env: 'ANTHROPIC_API_KEY'
    },
    {
      name: 'OpenAI',
      models: ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'],
      status: 'down',
      color: 'openai',
      env: 'OPENAI_API_KEY'
    },
    {
      name: 'Google',
      models: ['gemini-pro', 'gemini-1.5-pro', 'gemini-1.5-flash'],
      status: 'up',
      color: 'google',
      env: 'GOOGLE_API_KEY'
    },
    {
      name: 'Mistral',
      models: ['mistral-large-latest', 'mistral-medium', 'codestral-latest'],
      status: 'down',
      color: 'mistral',
      env: 'MISTRAL_API_KEY'
    },
    {
      name: 'Groq',
      models: ['llama-3.3-70b-versatile', 'mixtral-8x7b-32768', 'gemma2-9b-it'],
      status: 'up',
      color: 'groq',
      env: 'GROQ_API_KEY'
    }
  ];

  // Static classes so Tailwind emits one rule per provider.
  const providerRule: Record<string, string> = {
    ollama: 'border-l-accent-ollama',
    anthropic: 'border-l-accent-anthropic',
    openai: 'border-l-accent-openai',
    google: 'border-l-accent-google',
    mistral: 'border-l-accent-mistral',
    groq: 'border-l-accent-groq'
  };

  $: upCount = providers.filter((p) => p.status === 'up').length;
</script>

<svelte:head>
  <title>Providers | Agent Tooling</title>
</svelte:head>

<div class="space-y-6 animate-in">
  <div class="flex flex-wrap items-baseline justify-between gap-2">
    <div>
      <h1 class="text-base font-medium text-on_background">Providers</h1>
      <p class="mt-1 text-sm text-on_surface">{providers.length} configured, {upCount} reachable</p>
    </div>
    <p class="font-mono text-xs text-on_surface_alt">seed data</p>
  </div>

  <div class="panel">
    {#each providers as provider}
      <div class="flex flex-wrap items-center gap-4 px-5 py-4 border-t border-line first:border-t-0 border-l-2 {providerRule[provider.color]}">
        <div class="w-28">
          <p class="text-sm text-on_background">{provider.name}</p>
          <p class={provider.status === 'up' ? 'state-up' : 'state-down'}>{provider.status}</p>
        </div>

        <div class="flex-1 min-w-[200px]">
          <p class="font-mono text-xs text-on_surface_alt">{provider.env}</p>
          <p class="mt-1 font-mono text-xs text-on_surface truncate">
            {provider.models.slice(0, 2).join(' · ')}{provider.models.length > 2
              ? ` +${provider.models.length - 2}`
              : ''}
          </p>
        </div>

        <div class="flex items-center gap-2">
          <button class="btn btn-secondary text-xs">Configure</button>
          <button class="btn btn-ghost text-xs">Test</button>
        </div>
      </div>
    {/each}
  </div>

  <div class="panel">
    <div class="panel-header">
      <h2 class="panel-title">CLI</h2>
    </div>
    <div class="p-5">
      <div class="code-block text-xs">
        <pre># chat with any provider
agent-tooling --chat --model ollama/qwen3-coder
agent-tooling --chat --model anthropic/claude-sonnet-4
agent-tooling --chat --model openai/gpt-4o

# list all providers
agent-tooling --providers</pre>
      </div>
    </div>
  </div>
</div>
