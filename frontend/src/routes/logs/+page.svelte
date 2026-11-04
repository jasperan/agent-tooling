<script lang="ts">
  // Seed data. In production this comes from the agent-tooling API.
  const logs = [
    { time: '03:45:22', level: 'ok', message: 'Tool execution completed: calculate', source: 'executor' },
    { time: '03:45:18', level: 'info', message: 'Invoking tool: calculate with params {"expression": "2+2"}', source: 'registry' },
    { time: '03:40:15', level: 'info', message: 'Connected to Ollama at localhost:11434', source: 'provider' },
    { time: '03:38:42', level: 'ok', message: 'Docker workspace initialized: python:3.12-slim', source: 'workspace' },
    { time: '03:35:10', level: 'info', message: 'Pi-dev bridge tools imported: 5 tools', source: 'bridge' },
    { time: '03:30:05', level: 'warn', message: 'Rate limit warning: OpenAI API (retry in 30s)', source: 'provider' },
    { time: '03:25:33', level: 'fail', message: 'Tool execution failed: run_code - sandbox timeout', source: 'executor' },
    { time: '03:20:18', level: 'info', message: 'MCP server started on stdio', source: 'mcp' },
    { time: '03:15:00', level: 'ok', message: 'Agent session initialized with model: ollama/qwen3-coder', source: 'agent' }
  ];

  const levels = ['all', 'ok', 'warn', 'fail'];
  let filterLevel = 'all';

  $: filteredLogs = filterLevel === 'all' ? logs : logs.filter((l) => l.level === filterLevel);
  $: counts = levels
    .filter((l) => l !== 'all')
    .map((level) => ({ level, count: logs.filter((l) => l.level === level).length }));

  // Only the level cell carries colour; the rest of the row stays neutral.
  const levelColor: Record<string, string> = {
    ok: 'text-success',
    warn: 'text-warning',
    fail: 'text-danger',
    info: 'text-on_surface_alt'
  };
</script>

<svelte:head>
  <title>Logs | Agent Tooling</title>
</svelte:head>

<div class="space-y-6 animate-in">
  <div class="flex flex-wrap items-baseline justify-between gap-3">
    <div>
      <h1 class="text-base font-medium text-on_background">Execution logs</h1>
      <p class="mt-1 text-sm text-on_surface">{filteredLogs.length} of {logs.length} entries</p>
    </div>
    <div class="flex items-center gap-4">
      {#each levels as level}
        <button
          on:click={() => (filterLevel = level)}
          class="filter {filterLevel === level ? 'filter-active' : ''}"
          aria-pressed={filterLevel === level}
        >
          {level}
        </button>
      {/each}
    </div>
  </div>

  <div class="panel overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-on_surface_alt border-b border-line">
            <th class="px-5 py-2 font-normal">Time</th>
            <th class="px-5 py-2 font-normal">Level</th>
            <th class="px-5 py-2 font-normal">Source</th>
            <th class="px-5 py-2 font-normal">Message</th>
          </tr>
        </thead>
        <tbody class="font-mono text-xs">
          {#each filteredLogs as log}
            <tr class="border-b border-line last:border-b-0 hover:bg-surface_alt">
              <td class="px-5 py-3 tabular text-on_surface_alt">{log.time}</td>
              <td class="px-5 py-3 {levelColor[log.level]}">{log.level}</td>
              <td class="px-5 py-3 text-on_surface_alt">{log.source}</td>
              <td class="px-5 py-3 text-on_background">{log.message}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>

  <div class="flex flex-wrap gap-8 font-mono text-xs text-on_surface_alt">
    {#each counts as entry}
      <span>{entry.level} <span class="tabular text-on_background">{entry.count}</span></span>
    {/each}
    <span class="ml-auto">seed data</span>
  </div>
</div>
