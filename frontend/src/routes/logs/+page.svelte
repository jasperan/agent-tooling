<script lang="ts">
  const logs = [
    { time: '03:45:22', level: 'success', message: 'Tool execution completed: calculate', source: 'executor' },
    { time: '03:45:18', level: 'info', message: 'Invoking tool: calculate with params {"expression": "2+2"}', source: 'registry' },
    { time: '03:40:15', level: 'info', message: 'Connected to Ollama at localhost:11434', source: 'provider' },
    { time: '03:38:42', level: 'success', message: 'Docker workspace initialized: python:3.12-slim', source: 'workspace' },
    { time: '03:35:10', level: 'info', message: 'Pi-dev bridge tools imported: 5 tools', source: 'bridge' },
    { time: '03:30:05', level: 'warning', message: 'Rate limit warning: OpenAI API (retry in 30s)', source: 'provider' },
    { time: '03:25:33', level: 'error', message: 'Tool execution failed: run_code - sandbox timeout', source: 'executor' },
    { time: '03:20:18', level: 'info', message: 'MCP server started on stdio', source: 'mcp' },
    { time: '03:15:00', level: 'success', message: 'Agent session initialized with model: ollama/qwen3-coder', source: 'agent' }
  ];
  
  let filterLevel = 'all';
  
  $: filteredLogs = filterLevel === 'all' 
    ? logs 
    : logs.filter(l => l.level === filterLevel);
  
  function getLevelColor(level: string) {
    const colors: Record<string, string> = {
      success: 'text-success',
      info: 'text-info',
      warning: 'text-warning',
      error: 'text-danger'
    };
    return colors[level] || 'text-on_surface';
  }
</script>

<svelte:head>
  <title>Logs | Agent Tooling</title>
</svelte:head>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-xl font-semibold text-on_background">Execution Logs</h1>
      <p class="text-sm text-on_surface_alt">Tool execution and system events</p>
    </div>
    <div class="flex gap-2">
      <button 
        on:click={() => filterLevel = 'all'}
        class="badge {filterLevel === 'all' ? 'badge-provider' : 'bg-surface_alt text-on_surface_alt'} cursor-pointer"
      >
        All
      </button>
      <button 
        on:click={() => filterLevel = 'success'}
        class="badge {filterLevel === 'success' ? 'badge-success' : 'bg-surface_alt text-on_surface_alt'} cursor-pointer"
      >
        Success
      </button>
      <button 
        on:click={() => filterLevel = 'warning'}
        class="badge {filterLevel === 'warning' ? 'badge-warning' : 'bg-surface_alt text-on_surface_alt'} cursor-pointer"
      >
        Warning
      </button>
      <button 
        on:click={() => filterLevel = 'error'}
        class="badge {filterLevel === 'error' ? 'badge-danger' : 'bg-surface_alt text-on_surface_alt'} cursor-pointer"
      >
        Error
      </button>
    </div>
  </div>

  <div class="card overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full">
        <thead>
          <tr class="text-left text-sm text-on_surface_alt border-b border-outline bg-surface_alt">
            <th class="px-4 py-3 font-medium">Time</th>
            <th class="px-4 py-3 font-medium">Level</th>
            <th class="px-4 py-3 font-medium">Source</th>
            <th class="px-4 py-3 font-medium">Message</th>
          </tr>
        </thead>
        <tbody class="text-sm font-mono">
          {#each filteredLogs as log}
            <tr class="border-b border-outline/50 hover:bg-surface_alt/50">
              <td class="px-4 py-3 text-on_surface_alt">{log.time}</td>
              <td class="px-4 py-3">
                <span class="{getLevelColor(log.level)} uppercase text-xs font-semibold">{log.level}</span>
              </td>
              <td class="px-4 py-3 text-secondary">{log.source}</td>
              <td class="px-4 py-3 text-on_background">{log.message}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>

  <!-- Stats -->
  <div class="grid grid-cols-4 gap-4">
    <div class="stat-card">
      <span class="stat-value text-success">{logs.filter(l => l.level === 'success').length}</span>
      <span class="stat-label">Success</span>
    </div>
    <div class="stat-card">
      <span class="stat-value text-info">{logs.filter(l => l.level === 'info').length}</span>
      <span class="stat-label">Info</span>
    </div>
    <div class="stat-card">
      <span class="stat-value text-warning">{logs.filter(l => l.level === 'warning').length}</span>
      <span class="stat-label">Warnings</span>
    </div>
    <div class="stat-card">
      <span class="stat-value text-danger">{logs.filter(l => l.level === 'error').length}</span>
      <span class="stat-label">Errors</span>
    </div>
  </div>
</div>
