<script>
  export let id;
  export let label;
  export let value = '';
  export let placeholder = '';
  export let maxlength = undefined;
  export let rows = 8;
</script>

<div class="textarea-field">
  <label class="textarea-field__label" for={id}>{label}</label>
  <textarea
    {id}
    class="textarea-field__input"
    {rows}
    {placeholder}
    {maxlength}
    bind:value
  ></textarea>
</div>

<style>
  .textarea-field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    width: 100%;
  }

  .textarea-field__label {
    font-size: var(--text-sm);
    font-weight: 500;
    color: var(--text-secondary);
    letter-spacing: 0.01em;
  }

  .textarea-field__input {
    width: 100%;
    resize: vertical;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    background: var(--bg-input);
    color: var(--text-primary);
    padding: var(--space-5);
    font-size: var(--text-base);
    line-height: 1.7;
    transition: border-color var(--transition-fast),
      box-shadow var(--transition-fast), background var(--transition-fast);
    outline: none;
    min-height: 180px;
  }

  .textarea-field__input::placeholder {
    color: var(--text-muted);
  }

  .textarea-field__input:hover {
    border-color: var(--border-strong);
  }

  .textarea-field__input:focus {
    border-color: var(--border-focus);
    box-shadow: 0 0 0 4px rgba(167, 139, 250, 0.18);
  }
</style>
