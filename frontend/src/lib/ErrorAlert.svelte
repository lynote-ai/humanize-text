<script>
  import { slide } from 'svelte/transition';

  export let message = '';
</script>

{#if message}
  <div class="error-alert" role="alert" transition:slide={{ duration: 250 }}>
    <span class="error-alert__icon" aria-hidden="true">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
    </span>
    <p class="error-alert__message">{message}</p>
  </div>
{/if}

<style>
  .error-alert {
    display: flex;
    align-items: flex-start;
    gap: var(--space-3);
    width: 100%;
    padding: var(--space-4) var(--space-5);
    border-radius: var(--radius-lg);
    background: var(--bg-error);
    border: 1px solid rgba(220, 38, 38, 0.15);
    color: var(--text-error);
    box-shadow: var(--shadow-sm);
  }

  .error-alert__icon {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .error-alert__message {
    margin: 0;
    font-size: var(--text-sm);
    font-weight: 500;
    line-height: 1.6;
  }
</style>
