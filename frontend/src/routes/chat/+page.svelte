<script lang="ts">
  type Entry = { role: 'user' | 'system'; content: string; time: string };

  let messages: Entry[] = [];
  let input = '';
  let selectedProvider = 'ollama';
  let selectedModel = 'qwen3-coder';

  const providers = [
    { id: 'ollama', name: 'Ollama', models: ['qwen3-coder', 'mistral-small3.2', 'llama3.2'] },
    { id: 'anthropic', name: 'Anthropic', models: ['claude-sonnet-4', 'claude-opus-4'] },
    { id: 'openai', name: 'OpenAI', models: ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'] }
  ];

  $: currentProvider = providers.find((p) => p.id === selectedProvider);

  function handleSubmit() {
    if (!input.trim()) return;

    const text = input.trim();
    messages = [
      ...messages,
      { role: 'user', content: text, time: new Date().toLocaleTimeString() },
      {
        role: 'system',
        content: 'not sent · the dashboard has no API client yet',
        time: new Date().toLocaleTimeString()
      }
    ];
    input = '';
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }
</script>

<svelte:head>
  <title>Chat | Agent Tooling</title>
</svelte:head>

<div class="flex flex-col h-[calc(100vh-8rem)] animate-in">
  <div class="flex flex-wrap items-start justify-between gap-3 mb-4">
    <div>
      <h1 class="text-base font-medium text-on_background">Chat</h1>
      <p class="mt-1 text-sm text-on_surface">Messages queue locally. No API client is wired yet.</p>
    </div>

    <div class="flex items-center gap-2">
      <select bind:value={selectedProvider} class="input w-auto text-xs" aria-label="Provider">
        {#each providers as provider}
          <option value={provider.id}>{provider.name}</option>
        {/each}
      </select>

      <select bind:value={selectedModel} class="input w-auto text-xs" aria-label="Model">
        {#if currentProvider}
          {#each currentProvider.models as model}
            <option value={model}>{model}</option>
          {/each}
        {/if}
      </select>
    </div>
  </div>

  <div class="flex-1 overflow-y-auto panel mb-4" role="log" aria-live="polite">
    {#if messages.length === 0}
      <p class="px-5 py-6 text-sm text-on_surface_alt">No messages yet.</p>
    {:else}
      {#each messages as message}
        <div class="px-5 py-4 border-b border-line last:border-b-0">
          <div class="flex items-baseline gap-3">
            <span class="font-mono text-xs w-16 text-on_surface_alt">
              {message.role === 'user' ? 'you' : 'system'}
            </span>
            <p
              class="flex-1 text-sm whitespace-pre-wrap {message.role === 'user'
                ? 'text-on_background'
                : 'font-mono text-xs text-on_surface_alt'}"
            >
              {message.content}
            </p>
            <span class="font-mono text-xs tabular text-on_surface_alt">{message.time}</span>
          </div>
        </div>
      {/each}
    {/if}
  </div>

  <form on:submit|preventDefault={handleSubmit} class="flex gap-2 items-end">
    <textarea
      bind:value={input}
      on:keydown={handleKeydown}
      class="input flex-1 resize-none py-2"
      placeholder="Write a message"
      rows="2"
      aria-label="Chat input"
    ></textarea>
    <button type="submit" class="btn btn-primary" disabled={!input.trim()}>Queue</button>
  </form>
</div>
