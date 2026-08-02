<script>
  export let id;
  export let label;
  export let value;
  export let options = [];
  export let helper = '';

  $: selectedLabel = options.find((o) => o.value === value)?.label ?? value;
</script>

<div class="select-field">
  <label class="select-field__label" for={id}>{label}</label>
  <div class="select-field__wrapper">
    <select {id} bind:value on:change class="select-field__select">
      {#each options as option}
        <option value={option.value}>{option.label}</option>
      {/each}
    </select>
    <span class="select-field__chevron" aria-hidden="true">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </span>
  </div>
  {#if helper}
    <span class="select-field__helper">{helper}</span>
  {/if}
</div>

<style>
  .select-field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    width: 100%;
  }

  .select-field__label {
    font-size: var(--text-sm);
    font-weight: 500;
    color: var(--text-secondary);
    letter-spacing: 0.01em;
  }

  .select-field__wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .select-field__select {
    width: 100%;
    appearance: none;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    background: var(--bg-input);
    color: var(--text-primary);
    padding: var(--space-3) var(--space-10) var(--space-3) var(--space-4);
    font-size: var(--text-base);
    font-weight: 500;
    cursor: pointer;
    transition: border-color var(--transition-fast),
      box-shadow var(--transition-fast), background var(--transition-fast);
    outline: none;
  }

  .select-field__select:hover {
    border-color: var(--border-strong);
  }

  .select-field__select:focus {
    border-color: var(--border-focus);
    box-shadow: 0 0 0 4px rgba(167, 139, 250, 0.2);
  }

  .select-field__chevron {
    position: absolute;
    right: var(--space-4);
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-muted);
    pointer-events: none;
  }

  .select-field__helper {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }
</style>
