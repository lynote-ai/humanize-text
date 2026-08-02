<script>
  export let type = 'primary';
  export let disabled = false;
  export let fullWidth = false;
  export let size = 'lg';

  $: classes = [
    'button',
    `button--${type}`,
    `button--${size}`,
    fullWidth && 'button--full-width',
  ]
    .filter(Boolean)
    .join(' ');
</script>

<button class={classes} {disabled} on:click>
  <slot />
</button>

<style>
  .button {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    border: none;
    border-radius: var(--radius-full);
    font-weight: 600;
    cursor: pointer;
    transition: transform var(--transition-base),
      box-shadow var(--transition-base), background var(--transition-fast);
    outline: none;
    overflow: hidden;
  }

  .button::after {
    content: '';
    position: absolute;
    inset: 0;
    background: var(--gradient-card-shine);
    opacity: 0;
    transition: opacity var(--transition-base);
  }

  .button:hover::after {
    opacity: 1;
  }

  .button:active:not(:disabled) {
    transform: translateY(1px) scale(0.99);
  }

  .button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
    transform: none !important;
  }

  /* Sizes */
  .button--lg {
    padding: var(--space-4) var(--space-8);
    font-size: var(--text-lg);
    min-height: 3.25rem;
  }

  .button--md {
    padding: var(--space-3) var(--space-5);
    font-size: var(--text-base);
    min-height: 2.75rem;
  }

  .button--full-width {
    width: 100%;
  }

  /* Primary */
  .button--primary {
    background: var(--gradient-primary);
    color: var(--text-inverse);
    box-shadow: 0 8px 24px rgba(124, 58, 237, 0.25),
      inset 0 1px 0 rgba(255, 255, 255, 0.2);
  }

  .button--primary:hover:not(:disabled) {
    background: var(--gradient-primary-hover);
    box-shadow: 0 12px 32px rgba(124, 58, 237, 0.35),
      inset 0 1px 0 rgba(255, 255, 255, 0.2);
    transform: translateY(-2px);
  }

  /* Secondary */
  .button--secondary {
    background: var(--bg-surface);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-sm);
  }

  .button--secondary:hover:not(:disabled) {
    background: var(--bg-hover);
    border-color: var(--border-strong);
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
  }

  /* Ghost */
  .button--ghost {
    background: transparent;
    color: var(--text-secondary);
  }

  .button--ghost:hover:not(:disabled) {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
</style>
