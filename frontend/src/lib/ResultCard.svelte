<script>
  import { fly, fade } from 'svelte/transition';

  export let result = '';
  export let original = '';
  export let processingTimeMs = 0;
  export let methodUsed = '';
</script>

<article class="result-card" in:fly={{ y: 20, duration: 500, delay: 100 }} out:fade={{ duration: 150 }}>
  <div class="result-card__header">
    <div class="result-card__icon" aria-hidden="true">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" />
        <path d="m9 12 2 2 4-4" />
      </svg>
    </div>
    <div class="result-card__meta">
      <h2 class="result-card__title">Humanized result</h2>
      {#if processingTimeMs > 0}
        <span class="result-card__badge">{Math.round(processingTimeMs)}ms · {methodUsed}</span>
      {/if}
    </div>
  </div>

  <div class="result-card__body">
    {#if original}
      <div class="result-card__section">
        <h3 class="result-card__section-title">Original</h3>
        <p class="result-card__original">{original}</p>
      </div>
      <div class="result-card__divider" aria-hidden="true"></div>
    {/if}
    <div class="result-card__section">
      {#if original}
        <h3 class="result-card__section-title">Humanized</h3>
      {/if}
      <p class="result-card__result">{result}</p>
    </div>
  </div>

  <div class="result-card__actions">
    <button
      class="result-card__copy"
      on:click={() => navigator.clipboard?.writeText(result)}
      title="Copy to clipboard"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
      </svg>
      Copy
    </button>
  </div>
</article>

<style>
  .result-card {
    width: 100%;
    background: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-lg);
    overflow: hidden;
  }

  .result-card__header {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    padding: var(--space-6);
    border-bottom: 1px solid var(--border-color);
  }

  .result-card__icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border-radius: var(--radius-md);
    background: var(--bg-success);
    color: var(--text-success);
    flex-shrink: 0;
  }

  .result-card__meta {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .result-card__title {
    font-size: var(--text-xl);
    font-weight: 700;
    letter-spacing: -0.02em;
  }

  .result-card__badge {
    display: inline-flex;
    width: fit-content;
    padding: var(--space-1) var(--space-3);
    border-radius: var(--radius-full);
    background: var(--bg-hover);
    color: var(--text-secondary);
    font-size: var(--text-xs);
    font-weight: 500;
  }

  .result-card__body {
    padding: var(--space-6);
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
  }

  .result-card__section {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .result-card__section-title {
    font-size: var(--text-xs);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
  }

  .result-card__original {
    color: var(--text-secondary);
    line-height: 1.7;
  }

  .result-card__result {
    color: var(--text-primary);
    line-height: 1.7;
    font-size: var(--text-lg);
    font-weight: 500;
  }

  .result-card__divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border-color), transparent);
  }

  .result-card__actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--space-3);
    padding: var(--space-4) var(--space-6);
    background: var(--bg-hover);
    border-top: 1px solid var(--border-color);
  }

  .result-card__copy {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
    border-radius: var(--radius-full);
    border: 1px solid var(--border-color);
    background: var(--bg-surface);
    color: var(--text-secondary);
    font-size: var(--text-sm);
    font-weight: 500;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .result-card__copy:hover {
    background: var(--bg-hover-strong);
    color: var(--text-primary);
    border-color: var(--border-strong);
  }
</style>
