<script>
  export let size = 'md';
</script>

<div class="spinner spinner--{size}" aria-label="Loading">
  <div class="spinner__ring"></div>
</div>

<style>
  .spinner {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .spinner--sm {
    width: 20px;
    height: 20px;
  }

  .spinner--md {
    width: 32px;
    height: 32px;
  }

  .spinner--lg {
    width: 48px;
    height: 48px;
  }

  .spinner__ring {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    background: conic-gradient(
      from 0deg,
      transparent 0%,
      var(--color-primary-500) 60%,
      var(--color-accent-500) 100%
    );
    mask: radial-gradient(circle, transparent 60%, black 61%);
    -webkit-mask: radial-gradient(circle, transparent 60%, black 61%);
    animation: spin 1s linear infinite;
  }
</style>
