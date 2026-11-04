<script lang="ts">
  // Seed data. In production this comes from the agent-tooling API.
  const tools = [
    { name: 'calculate', category: 'utility', description: 'Arithmetic over numbers and units', mcp: true, sandbox: false, calls: 45 },
    { name: 'web_search', category: 'network', description: 'Query a search endpoint', mcp: true, sandbox: false, calls: 32 },
    { name: 'read_file', category: 'filesystem', description: 'Read a file from the workspace', mcp: true, sandbox: false, calls: 28 },
    { name: 'write_file', category: 'filesystem', description: 'Write a file into the workspace', mcp: true, sandbox: false, calls: 24 },
    { name: 'run_code', category: 'developer', description: 'Execute code in a sandbox', mcp: true, sandbox: true, calls: 15 },
    { name: 'pidev_read', category: 'bridge', description: 'Pi-dev bridge: read files', mcp: false, sandbox: false, calls: 12 },
    { name: 'pidev_write', category: 'bridge', description: 'Pi-dev bridge: write files', mcp: false, sandbox: false, calls: 10 },
    { name: 'pidev_edit', category: 'bridge', description: 'Pi-dev bridge: edit files', mcp: false, sandbox: false, calls: 8 },
    { name: 'bash_exec', category: 'developer', description: 'Execute shell commands', mcp: true, sandbox: true, calls: 18 },
    { name: 'http_request', category: 'network', description: 'Make HTTP requests', mcp: true, sandbox: false, calls: 22 }
  ];

  const categories = [...new Set(tools.map((t) => t.category))];
  let selectedCategory = 'all';

  $: filteredTools =
    selectedCategory === 'all' ? tools : tools.filter((t) => t.category === selectedCategory);
</script>

<svelte:head>
  <title>Tools | Agent Tooling</title>
</svelte:head>

<div class="space-y-6 animate-in">
  <div class="flex flex-wrap items-baseline justify-between gap-3">
    <div>
      <h1 class="text-base font-medium text-on_background">Tool registry</h1>
      <p class="mt-1 text-sm text-on_surface">{filteredTools.length} of {tools.length} tools</p>
    </div>
    <button class="btn btn-primary">Register tool</button>
  </div>

  <div class="flex flex-wrap items-center gap-4">
    <button
      on:click={() => (selectedCategory = 'all')}
      class="filter {selectedCategory === 'all' ? 'filter-active' : ''}"
      aria-pressed={selectedCategory === 'all'}
    >
      all ({tools.length})
    </button>
    {#each categories as category}
      <button
        on:click={() => (selectedCategory = category)}
        class="filter {selectedCategory === category ? 'filter-active' : ''}"
        aria-pressed={selectedCategory === category}
      >
        {category} ({tools.filter((t) => t.category === category).length})
      </button>
    {/each}
  </div>

  <div class="panel overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-on_surface_alt border-b border-line">
            <th class="px-5 py-2 font-normal">Tool</th>
            <th class="px-5 py-2 font-normal">Category</th>
            <th class="px-5 py-2 font-normal">Description</th>
            <th class="px-5 py-2 font-normal text-right">Calls</th>
            <th class="px-5 py-2 font-normal text-right">State</th>
            <th class="px-5 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {#each filteredTools as tool}
            <tr class="border-b border-line last:border-b-0 hover:bg-surface_alt">
              <td class="px-5 py-3 font-mono text-xs text-on_background">{tool.name}</td>
              <td class="px-5 py-3 text-xs text-on_surface_alt">{tool.category}</td>
              <td class="px-5 py-3 text-sm text-on_surface">{tool.description}</td>
              <td class="px-5 py-3 text-right font-mono text-xs tabular text-on_surface">{tool.calls}</td>
              <td class="px-5 py-3 text-right">
                <span class={tool.sandbox ? 'state-warn' : 'state-up'}>
                  {tool.sandbox ? 'sandbox' : tool.mcp ? 'mcp' : 'local'}
                </span>
              </td>
              <td class="px-5 py-3 text-right">
                <button class="btn btn-ghost text-xs">Schema</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>

  <div class="panel">
    <div class="panel-header">
      <h2 class="panel-title">Register a tool</h2>
      <p class="font-mono text-xs text-on_surface_alt">seed data</p>
    </div>
    <div class="p-5">
      <div class="code-block text-xs">
        <pre>from agent_tooling import tool

@tool(name="my_tool", category="custom", mcp_enabled=True)
def my_tool(param: str) -> str:
    """One sentence on what the tool does."""
    return f"Result: {param}"</pre>
      </div>
    </div>
  </div>
</div>
