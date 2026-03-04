<script lang="ts">
  // Mock data - in production this would come from API
  const stats = {
    providers: 6,
    tools: 24,
    workspaces: 3,
    executions: 156
  };
  
  const providers = [
    { name: 'Ollama', model: 'qwen3-coder', status: 'connected', color: 'ollama', env: 'OLLAMA_BASE_URL' },
    { name: 'Anthropic', model: 'claude-sonnet-4', status: 'connected', color: 'anthropic', env: 'ANTHROPIC_API_KEY' },
    { name: 'OpenAI', model: 'gpt-4o', status: 'disconnected', color: 'openai', env: 'OPENAI_API_KEY' },
    { name: 'Google', model: 'gemini-pro', status: 'connected', color: 'google', env: 'GOOGLE_API_KEY' },
    { name: 'Mistral', model: 'mistral-large', status: 'disconnected', color: 'mistral', env: 'MISTRAL_API_KEY' },
    { name: 'Groq', model: 'llama-3.3-70b', status: 'connected', color: 'groq', env: 'GROQ_API_KEY' }
  ];
  
  const recentTools = [
    { name: 'calculate', category: 'utility', calls: 45, status: 'active' },
    { name: 'web_search', category: 'network', calls: 32, status: 'active' },
    { name: 'read_file', category: 'filesystem', calls: 28, status: 'active' },
    { name: 'run_code', category: 'developer', calls: 15, status: 'sandboxed' },
    { name: 'pidev_edit', category: 'bridge', calls: 12, status: 'active' }
  ];
  
  const recentLogs = [
    { time: '2 min ago', message: 'Tool execution completed: calculate', type: 'success' },
    { time: '5 min ago', message: 'Connected to Ollama at localhost:11434', type: 'info' },
    { time: '8 min ago', message: 'Docker workspace initialized: python:3.12-slim', type: 'info' },
    { time: '15 min ago', message: 'Pi-dev bridge tools imported: 5 tools', type: 'success' },
    { time: '22 min ago', message: 'Rate limit warning: OpenAI API', type: 'warning' }
  ];
  
  function getStatusColor(status: string) {
    return status === 'connected' ? 'success' : status === 'active' ? 'success' : status === 'sandboxed' ? 'info' : 'danger';
  }
  
  function getProviderColor(color: string) {
    return `bg-accent-${color}`;
  }
</script>

<svelte:head>
  <title>Dashboard | Agent Tooling</title>
</svelte:head>

<div class="space-y-6">
  <!-- Stats Grid -->
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
    <div class="stat-card">
      <div class="flex items-center gap-2 text-primary">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
        </svg>
        <span class="stat-label">Providers</span>
      </div>
      <span class="stat-value">{stats.providers}</span>
    </div>
    
    <div class="stat-card">
      <div class="flex items-center gap-2 text-secondary">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
        </svg>
        <span class="stat-label">Tools</span>
      </div>
      <span class="stat-value">{stats.tools}</span>
    </div>
    
    <div class="stat-card">
      <div class="flex items-center gap-2 text-warning">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
        </svg>
        <span class="stat-label">Workspaces</span>
      </div>
      <span class="stat-value">{stats.workspaces}</span>
    </div>
    
    <div class="stat-card">
      <div class="flex items-center gap-2 text-success">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
        </svg>
        <span class="stat-label">Executions</span>
      </div>
      <span class="stat-value">{stats.executions}</span>
    </div>
  </div>

  <!-- Main Grid -->
  <div class="grid lg:grid-cols-3 gap-6">
    <!-- Providers -->
    <div class="lg:col-span-2">
      <div class="card">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-on_background">LLM Providers</h3>
          <a href="/providers" class="text-sm text-primary hover:text-primary_hover">View all</a>
        </div>
        
        <div class="grid sm:grid-cols-2 gap-3">
          {#each providers as provider}
            <div class="card-hover flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-accent-{provider.color}/20 flex items-center justify-center">
                <div class="w-3 h-3 rounded-full bg-accent-{provider.color}"></div>
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-on_background">{provider.name}</span>
                  <span class="badge badge-{getStatusColor(provider.status)}">{provider.status}</span>
                </div>
                <p class="text-sm text-on_surface_alt truncate">{provider.model}</p>
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>

    <!-- Recent Logs -->
    <div>
      <div class="card h-full">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-on_background">Recent Activity</h3>
          <a href="/logs" class="text-sm text-primary hover:text-primary_hover">View all</a>
        </div>
        
        <div class="space-y-3">
          {#each recentLogs as log}
            <div class="flex items-start gap-3">
              <div class="w-2 h-2 mt-2 rounded-full bg-{log.type} flex-shrink-0"></div>
              <div class="flex-1 min-w-0">
                <p class="text-sm text-on_surface">{log.message}</p>
                <p class="text-xs text-on_surface_alt">{log.time}</p>
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  </div>

  <!-- Tools & Quick Actions -->
  <div class="grid lg:grid-cols-2 gap-6">
    <!-- Recent Tools -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-on_background">Tool Registry</h3>
        <a href="/tools" class="text-sm text-primary hover:text-primary_hover">View all</a>
      </div>
      
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="text-left text-sm text-on_surface_alt border-b border-outline">
              <th class="pb-3 font-medium">Tool</th>
              <th class="pb-3 font-medium">Category</th>
              <th class="pb-3 font-medium text-right">Calls</th>
              <th class="pb-3 font-medium text-right">Status</th>
            </tr>
          </thead>
          <tbody class="text-sm">
            {#each recentTools as tool}
              <tr class="border-b border-outline/50">
                <td class="py-3 font-mono text-on_background">{tool.name}</td>
                <td class="py-3 text-on_surface_alt">{tool.category}</td>
                <td class="py-3 text-right text-on_surface">{tool.calls}</td>
                <td class="py-3 text-right">
                  <span class="badge badge-{getStatusColor(tool.status)}">{tool.status}</span>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="card">
      <h3 class="text-lg font-semibold text-on_background mb-4">Quick Actions</h3>
      
      <div class="grid grid-cols-2 gap-3">
        <a href="/chat" class="card-hover flex flex-col items-center gap-2 py-4">
          <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
          </svg>
          <span class="text-sm font-medium text-on_background">Start Chat</span>
        </a>
        
        <button class="card-hover flex flex-col items-center gap-2 py-4 cursor-pointer">
          <svg class="w-6 h-6 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
          </svg>
          <span class="text-sm font-medium text-on_background">New Tool</span>
        </button>
        
        <button class="card-hover flex flex-col items-center gap-2 py-4 cursor-pointer">
          <svg class="w-6 h-6 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
          </svg>
          <span class="text-sm font-medium text-on_background">Workspace</span>
        </button>
        
        <button class="card-hover flex flex-col items-center gap-2 py-4 cursor-pointer">
          <svg class="w-6 h-6 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
          </svg>
          <span class="text-sm font-medium text-on_background">Pi-dev Bridge</span>
        </button>
      </div>
      
      <div class="divider"></div>
      
      <div class="code-block text-xs">
        <span class="text-on_surface_alt"># Quick start</span><br>
        <span class="text-secondary">agent-tooling</span> --chat --model ollama/qwen3-coder
      </div>
    </div>
  </div>
</div>
