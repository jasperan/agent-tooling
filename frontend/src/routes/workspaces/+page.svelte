<script lang="ts">
  // Seed data. In production this comes from the agent-tooling API.
  const workspaces = [
    {
      name: 'LocalWorkspace',
      type: 'local',
      status: 'up',
      description: 'In-process execution for trusted tools',
      isolation: 'none',
      image: '',
      containers: 0
    },
    {
      name: 'DockerWorkspace',
      type: 'docker',
      status: 'up',
      description: 'Container isolation for untrusted code',
      isolation: 'full',
      image: 'python:3.12-slim',
      containers: 3
    },
    {
      name: 'RemoteWorkspace',
      type: 'remote',
      status: 'down',
      description: 'Network-isolated execution over HTTP',
      isolation: 'network',
      image: '',
      containers: 0,
      server: 'http://agent-server:3000'
    }
  ];
</script>

<svelte:head>
  <title>Workspaces | Agent Tooling</title>
</svelte:head>

<div class="space-y-6 animate-in">
  <div class="flex flex-wrap items-baseline justify-between gap-2">
    <div>
      <h1 class="text-base font-medium text-on_background">Workspaces</h1>
      <p class="mt-1 text-sm text-on_surface">{workspaces.length} execution environments</p>
    </div>
    <p class="font-mono text-xs text-on_surface_alt">seed data</p>
  </div>

  <div class="panel">
    {#each workspaces as ws}
      <div class="flex flex-wrap items-center gap-4 px-5 py-4 border-t border-line first:border-t-0">
        <div class="w-40">
          <p class="text-sm text-on_background">{ws.name}</p>
          <p class={ws.status === 'up' ? 'state-up' : 'state-down'}>{ws.status}</p>
        </div>

        <div class="flex-1 min-w-[220px]">
          <p class="text-sm text-on_surface">{ws.description}</p>
          {#if ws.image}
            <p class="mt-1 font-mono text-xs text-on_surface_alt">{ws.image}</p>
          {/if}
          {#if ws.server}
            <p class="mt-1 font-mono text-xs text-on_surface_alt">{ws.server}</p>
          {/if}
        </div>

        <div class="w-28 font-mono text-xs text-on_surface_alt">
          <p>{ws.type}</p>
          <p>isolation {ws.isolation}</p>
        </div>

        <div class="flex items-center gap-2">
          <span class="font-mono text-xs tabular text-on_surface_alt w-16 text-right">
            {ws.containers} box{ws.containers === 1 ? '' : 'es'}
          </span>
          <button class="btn btn-secondary text-xs">Configure</button>
        </div>
      </div>
    {/each}
  </div>

  <div class="panel">
    <div class="panel-header">
      <h2 class="panel-title">Configure a workspace</h2>
    </div>
    <div class="p-5">
      <div class="code-block text-xs">
        <pre>from agent_tooling.workspace.local import LocalWorkspace
from agent_tooling.workspace.docker import DockerWorkspace
from agent_tooling.workspace.remote import RemoteWorkspace

# in-process
ws = LocalWorkspace()

# container per execution
ws = DockerWorkspace(image="python:3.12-slim")

# remote server
ws = RemoteWorkspace(server_url="http://agent-server:3000")</pre>
      </div>
    </div>
  </div>
</div>
