<script lang="ts">
  import '../app.css';
  import { page } from '$app/stores';

  let sidebarOpen = false;

  const navItems = [
    { href: '/', label: 'Dashboard', icon: 'dashboard' },
    { href: '/providers', label: 'Providers', icon: 'providers' },
    { href: '/tools', label: 'Tools', icon: 'tools' },
    { href: '/workspaces', label: 'Workspaces', icon: 'workspaces' },
    { href: '/chat', label: 'Chat', icon: 'chat' },
    { href: '/logs', label: 'Logs', icon: 'logs' }
  ];

  $: currentPath = $page.url.pathname;
  $: currentLabel = navItems.find((item) => item.href === currentPath)?.label ?? 'Agent Tooling';
  $: if (currentPath) sidebarOpen = false;

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape' && sidebarOpen) {
      sidebarOpen = false;
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<a
  href="#main-content"
  class="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:bg-primary focus:text-on_primary focus:px-4 focus:py-2 focus:rounded-lg"
>
  Skip to main content
</a>

<div class="flex h-screen bg-background text-on_background overflow-hidden">
  {#if sidebarOpen}
    <div
      class="fixed inset-0 bg-black/60 z-30 lg:hidden"
      on:click={() => (sidebarOpen = false)}
      role="presentation"
      aria-hidden="true"
    ></div>
  {/if}

  <aside
    class="w-60 flex flex-col border-r border-line bg-surface fixed inset-y-0 left-0 z-40 transform transition-transform duration-200 ease-out lg:relative lg:translate-x-0 {sidebarOpen
      ? 'translate-x-0'
      : '-translate-x-full'}"
  >
    <div class="h-14 flex items-center justify-between px-4 border-b border-line">
      <div>
        <h1 class="text-sm font-medium text-on_background">agent tooling</h1>
        <p class="font-mono text-xs text-on_surface_alt">multi-provider</p>
      </div>

      <button
        class="lg:hidden btn-icon"
        on:click={() => (sidebarOpen = false)}
        aria-label="Close sidebar"
      >
        <svg class="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M6 18L18 6M6 6l12 12"
          ></path>
        </svg>
      </button>
    </div>

    <nav class="flex-1 p-2 overflow-y-auto" role="navigation" aria-label="Main navigation">
      {#each navItems as item}
        <a
          href={item.href}
          class="{currentPath === item.href ? 'sidebar-link-active' : 'sidebar-link'}"
          aria-current={currentPath === item.href ? 'page' : undefined}
        >
          <svg
            class="w-[18px] h-[18px] flex-shrink-0 text-on_surface_alt"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            {#if item.icon === 'dashboard'}
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="1.5"
                d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
              ></path>
            {:else if item.icon === 'providers'}
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="1.5"
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              ></path>
            {:else if item.icon === 'tools'}
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="1.5"
                d="M11.42 15.17L7.4 19.2a2.12 2.12 0 01-3-3l4.03-4.03M14.5 6.5l3 3m-9.5 1.5l6-6 4 4-6 6-4-4z"
              ></path>
            {:else if item.icon === 'workspaces'}
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="1.5"
                d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
              ></path>
            {:else if item.icon === 'chat'}
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="1.5"
                d="M8 10h8M8 14h5M21 12c0 4.418-4.03 8-9 8a9.86 9.86 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              ></path>
            {:else if item.icon === 'logs'}
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="1.5"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              ></path>
            {/if}
          </svg>
          <span>{item.label}</span>
        </a>
      {/each}
    </nav>

    <div class="px-4 py-3 border-t border-line">
      <p class="font-mono text-xs text-on_surface_alt">local</p>
    </div>
  </aside>

  <div class="flex-1 flex flex-col overflow-hidden">
    <header class="h-14 flex items-center px-4 border-b border-line bg-surface lg:px-6">
      <button
        class="lg:hidden btn-icon mr-2"
        on:click={() => (sidebarOpen = true)}
        aria-label="Open sidebar"
      >
        <svg class="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M4 6h16M4 12h16M4 18h16"
          ></path>
        </svg>
      </button>

      <h2 class="flex-1 text-sm font-medium text-on_background">{currentLabel}</h2>

      <button class="btn-icon" aria-label="Settings">
        <svg class="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M12 15a3 3 0 100-6 3 3 0 000 6z"
          ></path>
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09A1.65 1.65 0 008.5 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09A1.65 1.65 0 004.6 8.5a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z"
          ></path>
        </svg>
      </button>
    </header>

    <main id="main-content" class="flex-1 overflow-y-auto p-6" role="main">
      <slot />
    </main>
  </div>
</div>

<style>
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
  }

  .focus\:not-sr-only:focus {
    position: fixed;
    width: auto;
    height: auto;
    padding: 0.5rem 1rem;
    margin: 0;
    overflow: visible;
    clip: auto;
    white-space: normal;
  }
</style>
