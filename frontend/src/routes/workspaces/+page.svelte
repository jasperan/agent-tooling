<script lang="ts">
  const workspaces = [
    { 
      name: 'LocalWorkspace', 
      type: 'local',
      status: 'active',
      description: 'In-process execution - development and trusted tools',
      isolation: 'None',
      image: '-',
      containers: 0
    },
    { 
      name: 'DockerWorkspace', 
      type: 'docker',
      status: 'active',
      description: 'Full container isolation - untrusted code and production',
      isolation: 'Full',
      image: 'python:3.12-slim',
      containers: 3
    },
    { 
      name: 'RemoteWorkspace', 
      type: 'remote',
      status: 'disconnected',
      description: 'Network-isolated execution via HTTP',
      isolation: 'Network',
      image: '-',
      containers: 0,
      server: 'http://agent-server:3000'
    }
  ];
  
  function getTypeColor(type: string) {
    const colors: Record<string, string> = {
      local: 'success',
      docker: 'warning',
      remote: 'info'
    };
    return colors[type] || 'info';
  }
</script>

<svelte:head>
  <title>Workspaces | Agent Tooling</title>
</svelte:head>

<div class="space-y-6">
  <div>
    <h1 class="text-xl font-semibold text-on_background">Workspaces</h1>
    <p class="text-sm text-on_surface_alt">Execution environments for tool isolation</p>
  </div>

  <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
    {#each workspaces as ws}
      <div class="card-hover">
        <div class="flex items-start justify-between mb-3">
          <div>
            <h3 class="font-semibold text-on_background">{ws.name}</h3>
            <span class="badge badge-{getTypeColor(ws.type)}">{ws.type}</span>
          </div>
          <span class="badge badge-{ws.status === 'active' ? 'success' : 'danger'}">{ws.status}</span>
        </div>
        
        <p class="text-sm text-on_surface_alt mb-4">{ws.description}</p>
        
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-on_surface_alt">Isolation:</span>
            <span class="text-on_background">{ws.isolation}</span>
          </div>
          {#if ws.image !== '-'}
            <div class="flex justify-between">
              <span class="text-on_surface_alt">Image:</span>
              <code class="text-xs bg-background px-2 py-0.5 rounded">{ws.image}</code>
            </div>
          {/if}
          {#if ws.containers > 0}
            <div class="flex justify-between">
              <span class="text-on_surface_alt">Containers:</span>
              <span class="text-on_background">{ws.containers}</span>
            </div>
          {/if}
          {#if ws.server}
            <div class="flex justify-between">
              <span class="text-on_surface_alt">Server:</span>
              <code class="text-xs bg-background px-2 py-0.5 rounded">{ws.server}</code>
            </div>
          {/if}
        </div>
        
        <div class="divider"></div>
        
        <div class="flex gap-2">
          <button class="btn-secondary flex-1 text-sm">Configure</button>
          {#if ws.type === 'docker'}
            <button class="btn-ghost text-sm">Prune</button>
          {/if}
        </div>
      </div>
    {/each}
  </div>

  <!-- Code Examples -->
  <div class="card">
    <h3 class="text-lg font-semibold text-on_background mb-4">Workspace Configuration</h3>
    <div class="code-block text-sm">
      <pre class="text-on_surface"><span class="text-warning">from</span> agent_tooling.workspace.local <span class="text-warning">import</span> LocalWorkspace
<span class="text-warning">from</span> agent_tooling.workspace.docker <span class="text-warning">import</span> DockerWorkspace
<span class="text-warning">from</span> agent_tooling.workspace.remote <span class="text-warning">import</span> RemoteWorkspace

<span class="text-on_surface_alt"># Local: tools run in-process</span>
ws = LocalWorkspace()

<span class="text-on_surface_alt"># Docker: tools run in containers</span>
ws = DockerWorkspace(image=<span class="text-success">"python:3.12-slim"</span>)

<span class="text-on_surface_alt"># Remote: tools run on remote server</span>
ws = RemoteWorkspace(server_url=<span class="text-success">"http://agent-server:3000"</span>)</pre>
    </div>
  </div>
</div>
