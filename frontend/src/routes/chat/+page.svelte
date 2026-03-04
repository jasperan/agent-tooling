<script lang="ts">
  let messages: { role: 'user' | 'assistant'; content: string; time: string }[] = [
    { role: 'assistant', content: 'Hello! I\'m your agent-tooling assistant. I can help you with tool execution, provider configuration, and workspace management. What would you like to do?', time: 'Now' }
  ];
  
  let input = '';
  let isLoading = false;
  let selectedProvider = 'ollama';
  let selectedModel = 'qwen3-coder';
  
  const providers = [
    { id: 'ollama', name: 'Ollama', models: ['qwen3-coder', 'mistral-small3.2', 'llama3.2'] },
    { id: 'anthropic', name: 'Anthropic', models: ['claude-sonnet-4', 'claude-opus-4'] },
    { id: 'openai', name: 'OpenAI', models: ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'] }
  ];
  
  $: currentProvider = providers.find(p => p.id === selectedProvider);
  
  async function handleSubmit() {
    if (!input.trim() || isLoading) return;
    
    const userMessage = { role: 'user' as const, content: input, time: new Date().toLocaleTimeString() };
    messages = [...messages, userMessage];
    input = '';
    isLoading = true;
    
    // Simulate response (in production, this would call the backend)
    await new Promise(r => setTimeout(r, 1500));
    
    messages = [...messages, {
      role: 'assistant',
      content: `I received your message: "${userMessage.content}"\n\nThis is a demo. In production, this would connect to the agent-tooling backend and execute tools based on your request.`,
      time: new Date().toLocaleTimeString()
    }];
    
    isLoading = false;
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

<div class="flex flex-col h-[calc(100vh-8rem)]">
  <!-- Header -->
  <div class="flex items-center justify-between mb-4">
    <div>
      <h1 class="text-xl font-semibold text-on_background">Chat</h1>
      <p class="text-sm text-on_surface_alt">Interactive agent session</p>
    </div>
    
    <div class="flex items-center gap-3">
      <select 
        bind:value={selectedProvider}
        class="input w-auto"
        aria-label="Select provider"
      >
        {#each providers as provider}
          <option value={provider.id}>{provider.name}</option>
        {/each}
      </select>
      
      <select 
        bind:value={selectedModel}
        class="input w-auto"
        aria-label="Select model"
      >
        {#if currentProvider}
          {#each currentProvider.models as model}
            <option value={model}>{model}</option>
          {/each}
        {/if}
      </select>
    </div>
  </div>

  <!-- Messages -->
  <div class="flex-1 overflow-y-auto card mb-4 p-4 space-y-4" role="log" aria-live="polite">
    {#each messages as message}
      <div class="flex gap-3 {message.role === 'user' ? 'flex-row-reverse' : ''}">
        <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 {message.role === 'user' ? 'bg-primary' : 'bg-surface_alt'}">
          {#if message.role === 'user'}
            <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
            </svg>
          {:else}
            <svg class="w-4 h-4 text-on_background" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
            </svg>
          {/if}
        </div>
        
        <div class="flex-1 max-w-[80%] {message.role === 'user' ? 'text-right' : ''}">
          <div class="inline-block px-4 py-3 rounded-xl {message.role === 'user' ? 'bg-primary text-white' : 'bg-surface_alt text-on_background'}">
            <p class="text-sm whitespace-pre-wrap">{message.content}</p>
          </div>
          <p class="text-xs text-on_surface_alt mt-1">{message.time}</p>
        </div>
      </div>
    {/each}
    
    {#if isLoading}
      <div class="flex gap-3">
        <div class="w-8 h-8 rounded-full bg-surface_alt flex items-center justify-center">
          <div class="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
        </div>
        <div class="bg-surface_alt rounded-xl px-4 py-3">
          <p class="text-sm text-on_surface">Thinking...</p>
        </div>
      </div>
    {/if}
  </div>

  <!-- Input -->
  <form on:submit|preventDefault={handleSubmit} class="flex gap-3">
    <textarea
      bind:value={input}
      on:keydown={handleKeydown}
      class="input flex-1 resize-none"
      placeholder="Ask anything... (Shift+Enter for new line)"
      rows="2"
      disabled={isLoading}
      aria-label="Chat input"
    ></textarea>
    <button 
      type="submit" 
      class="btn-primary self-end"
      disabled={!input.trim() || isLoading}
      aria-label="Send message"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path>
      </svg>
      Send
    </button>
  </form>
</div>
