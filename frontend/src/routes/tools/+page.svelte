<script lang="ts">
  const tools = [
    { name: 'calculate', category: 'utility', description: 'Perform mathematical calculations', mcp: true, sandbox: false, calls: 45 },
    { name: 'web_search', category: 'network', description: 'Search the web for information', mcp: true, sandbox: false, calls: 32 },
    { name: 'read_file', category: 'filesystem', description: 'Read contents of a file', mcp: true, sandbox: false, calls: 28 },
    { name: 'write_file', category: 'filesystem', description: 'Write content to a file', mcp: true, sandbox: false, calls: 24 },
    { name: 'run_code', category: 'developer', description: 'Execute code in sandboxed environment', mcp: true, sandbox: true, calls: 15 },
    { name: 'pidev_read', category: 'bridge', description: 'Pi-dev bridge: read files', mcp: false, sandbox: false, calls: 12 },
    { name: 'pidev_write', category: 'bridge', description: 'Pi-dev bridge: write files', mcp: false, sandbox: false, calls: 10 },
    { name: 'pidev_edit', category: 'bridge', description: 'Pi-dev bridge: edit files', mcp: false, sandbox: false, calls: 8 },
    { name: 'bash_exec', category: 'developer', description: 'Execute shell commands', mcp: true, sandbox: true, calls: 18 },
    { name: 'http_request', category: 'network', description: 'Make HTTP requests', mcp: true, sandbox: false, calls: 22 }
  ];
  
  const categories = [...new Set(tools.map(t => t.category))];
  let selectedCategory = 'all';
  
  $: filteredTools = selectedCategory === 'all' 
    ? tools 
    : tools.filter(t => t.category === selectedCategory);
  
  function getCategoryColor(category: string) {
    const colors: Record<string, string> = {
      utility: 'info',
      network: 'warning',
      filesystem: 'success',
      developer: 'danger',
      bridge: 'provider'
    };
    return colors[category] || 'info';
  }
</script>

<svelte:head>
  <title>Tools | Agent Tooling</title>
</svelte:head>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-xl font-semibold text-on_background">Tool Registry</h1>
      <p class="text-sm text-on_surface_alt">Manage and monitor registered tools</p>
    </div>
    <button class="btn-primary">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
      </svg>
      Register Tool
    </button>
  </div>

  <!-- Category Filter -->
  <div class="flex gap-2 flex-wrap">
    <button 
      on:click={() => selectedCategory = 'all'}
      class="badge {selectedCategory === 'all' ? 'badge-provider' : 'bg-surface_alt text-on_surface_alt'} cursor-pointer"
    >
      All ({tools.length})
    </button>
    {#each categories as category}
      <button 
        on:click={() => selectedCategory = category}
        class="badge {selectedCategory === category ? 'badge-' + getCategoryColor(category) : 'bg-surface_alt text-on_surface_alt'} cursor-pointer"
      >
        {category} ({tools.filter(t => t.category === category).length})
      </button>
    {/each}
  </div>

  <!-- Tools Grid -->
  <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
    {#each filteredTools as tool}
      <div class="card-hover">
        <div class="flex items-start justify-between mb-2">
          <div>
            <h3 class="font-mono font-semibold text-on_background">{tool.name}</h3>
            <span class="badge badge-{getCategoryColor(tool.category)}">{tool.category}</span>
          </div>
          <span class="text-sm text-on_surface_alt">{tool.calls} calls</span>
        </div>
        
        <p class="text-sm text-on_surface mb-3">{tool.description}</p>
        
        <div class="flex gap-2">
          {#if tool.mcp}
            <span class="badge badge-success">MCP</span>
          {/if}
          {#if tool.sandbox}
            <span class="badge badge-warning">Sandboxed</span>
          {/if}
        </div>
        
        <div class="divider"></div>
        
        <div class="flex gap-2">
          <button class="btn-secondary flex-1 text-sm">View Schema</button>
          <button class="btn-ghost text-sm">Test</button>
        </div>
      </div>
    {/each}
  </div>

  <!-- Code Example -->
  <div class="card">
    <h3 class="text-lg font-semibold text-on_background mb-4">Register a Tool</h3>
    <div class="code-block text-sm">
      <pre class="text-on_surface"><span class="text-warning">from</span> agent_tooling <span class="text-warning">import</span> tool

<span class="text-secondary">@tool</span>(name=<span class="text-success">"my_tool"</span>, category=<span class="text-success">"custom"</span>, mcp_enabled=<span class="text-warning">True</span>)
<span class="text-warning">def</span> <span class="text-secondary">my_tool</span>(param: <span class="text-warning">str</span>) -> <span class="text-warning">str</span>:
    <span class="text-on_surface_alt">"""Tool description here."""</span>
    <span class="text-warning">return</span> <span class="text-success">f"Result: {param}"</span></pre>
    </div>
  </div>
</div>
