<script lang="ts">
  // Seed data. In production this comes from the agent-tooling API.
  const stats = {
    providers: 6,
    tools: 24,
    workspaces: 3,
    executions: 156
  };

  const providers = [
    { name: 'Ollama', model: 'qwen3-coder', status: 'up', color: 'ollama' },
    { name: 'Anthropic', model: 'claude-sonnet-4', status: 'up', color: 'anthropic' },
    { name: 'OpenAI', model: 'gpt-4o', status: 'down', color: 'openai' },
    { name: 'Google', model: 'gemini-pro', status: 'up', color: 'google' },
    { name: 'Mistral', model: 'mistral-large', status: 'down', color: 'mistral' },
    { name: 'Groq', model: 'llama-3.3-70b', status: 'up', color: 'groq' }
  ];

  const recentTools = [
    { name: 'calculate', category: 'utility', calls: 45, status: 'up' },
    { name: 'web_search', category: 'network', calls: 32, status: 'up' },
    { name: 'read_file', category: 'filesystem', calls: 28, status: 'up' },
    { name: 'run_code', category: 'developer', calls: 15, status: 'sandbox' },
    { name: 'pidev_edit', category: 'bridge', calls: 12, status: 'up' }
  ];

  const recentLogs = [
    { time: '03:45', message: 'Tool execution completed: calculate', level: 'ok' },
    { time: '03:40', message: 'Connected to Ollama at localhost:11434', level: 'ok' },
    { time: '03:38', message: 'Docker workspace initialized: python:3.12-slim', level: 'ok' },
    { time: '03:35', message: 'Pi-dev bridge tools imported: 5 tools', level: 'ok' },
    { time: '03:30', message: 'Rate limit warning: OpenAI API', level: 'warn' }
  ];

  // Per-provider hue survives as one 4px rule. Static classes so Tailwind emits them.
  const providerRule: Record<string, string> = {
    ollama: 'border-l-accent-ollama',
    anthropic: 'border-l-accent-anthropic',
    openai: 'border-l-accent-openai',
    google: 'border-l-accent-google',
    mistral: 'border-l-accent-mistral',
    groq: 'border-l-accent-groq'
  };
</script>

<svelte:head>
  <title>Dashboard | Agent Tooling</title>
</svelte:head>

<div class="space-y-6 animate-in">
  <div class="flex flex-wrap items-baseline justify-between gap-2">
    <h1 class="text-base font-medium text-on_background">Tooling overview</h1>
    <p class="font-mono text-xs text-on_surface_alt">seed data</p>
  </div>

  <!-- Counts: one panel, four cells, no icons. -->
  <div class="panel grid grid-cols-2 lg:grid-cols-4">
    <div class="px-5 py-4 border-b border-line lg:border-b-0 lg:border-r">
      <p class="text-xs text-on_surface_alt">Providers</p>
      <p class="mt-1 font-mono text-2xl tabular text-on_background">{stats.providers}</p>
    </div>
    <div class="px-5 py-4 border-b border-line lg:border-b-0 lg:border-r">
      <p class="text-xs text-on_surface_alt">Tools</p>
      <p class="mt-1 font-mono text-2xl tabular text-on_background">{stats.tools}</p>
    </div>
    <div class="px-5 py-4 border-b border-line lg:border-b-0 lg:border-r">
      <p class="text-xs text-on_surface_alt">Workspaces</p>
      <p class="mt-1 font-mono text-2xl tabular text-on_background">{stats.workspaces}</p>
    </div>
    <div class="px-5 py-4">
      <p class="text-xs text-on_surface_alt">Executions</p>
      <p class="mt-1 font-mono text-2xl tabular text-on_background">{stats.executions}</p>
    </div>
  </div>

  <div class="grid gap-6 lg:grid-cols-3">
    <!-- Providers -->
    <div class="lg:col-span-2 panel">
      <div class="panel-header">
        <h2 class="panel-title">Providers</h2>
        <a href="/providers" class="text-xs text-primary hover:text-primary_hover">All providers</a>
      </div>

      <div>
        {#each providers as provider}
          <div class="row row-hover border-l-2 {providerRule[provider.color]}">
            <span class="w-24 text-sm text-on_background">{provider.name}</span>
            <span class="flex-1 font-mono text-xs text-on_surface_alt truncate">{provider.model}</span>
            <span class={provider.status === 'up' ? 'state-up' : 'state-down'}>{provider.status}</span>
          </div>
        {/each}
      </div>
    </div>

    <!-- Activity -->
    <div class="panel">
      <div class="panel-header">
        <h2 class="panel-title">Activity</h2>
        <a href="/logs" class="text-xs text-primary hover:text-primary_hover">All logs</a>
      </div>

      <div>
        {#each recentLogs as log}
          <div class="row row-hover items-start">
            <div class="flex-1 min-w-0 py-3">
              <p class="text-sm text-on_surface leading-snug">{log.message}</p>
              <p class="mt-1 font-mono text-xs tabular text-on_surface_alt">{log.time}</p>
            </div>
            <span class={log.level === 'warn' ? 'state-warn' : 'state-down'}>{log.level}</span>
          </div>
        {/each}
      </div>
    </div>
  </div>

  <div class="grid gap-6 lg:grid-cols-2">
    <!-- Tools -->
    <div class="panel">
      <div class="panel-header">
        <h2 class="panel-title">Tool registry</h2>
        <a href="/tools" class="text-xs text-primary hover:text-primary_hover">All tools</a>
      </div>

      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-on_surface_alt border-b border-line">
            <th class="px-5 py-2 font-normal">Tool</th>
            <th class="px-5 py-2 font-normal">Category</th>
            <th class="px-5 py-2 font-normal text-right">Calls</th>
            <th class="px-5 py-2 font-normal text-right">State</th>
          </tr>
        </thead>
        <tbody>
          {#each recentTools as tool}
            <tr class="border-b border-line last:border-b-0 hover:bg-surface_alt">
              <td class="px-5 py-3 font-mono text-xs text-on_background">{tool.name}</td>
              <td class="px-5 py-3 text-xs text-on_surface_alt">{tool.category}</td>
              <td class="px-5 py-3 text-right font-mono text-xs tabular text-on_surface">{tool.calls}</td>
              <td class="px-5 py-3 text-right">
                <span class={tool.status === 'sandbox' ? 'state-warn' : 'state-up'}>{tool.status}</span>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <!-- Actions -->
    <div class="panel">
      <div class="panel-header">
        <h2 class="panel-title">Actions</h2>
      </div>

      <div class="p-5 space-y-2">
        <a href="/tools" class="btn btn-secondary w-full justify-start gap-3">Register a tool</a>
        <a href="/workspaces" class="btn btn-secondary w-full justify-start gap-3">Open a workspace</a>
        <a href="/providers" class="btn btn-secondary w-full justify-start gap-3">Add a provider</a>
      </div>

      <div class="px-5 pb-5">
        <p class="label">Quick start</p>
        <div class="code-block text-xs">
          <pre>agent-tooling --chat --model ollama/qwen3-coder</pre>
        </div>
      </div>
    </div>
  </div>
</div>
