<footer class="footer">
  <div class="footer__inner">
    <p class="footer__tagline">
      Open-source AI text humanizer - powered by the Humanize-Text project.
    </p>
    <div class="footer__links">
      <a href="https://github.com/lynote-ai/humanize-text" target="_blank" rel="noopener noreferrer">
        GitHub Repository
      </a>
      <span class="footer__divider" aria-hidden="true">•</span>
      <a href="https://lynote.ai" target="_blank" rel="noopener noreferrer">
        Lynote.ai
      </a>
      <span class="footer__divider" aria-hidden="true">•</span>
      <a href="/docs" rel="noopener noreferrer">
        API
      </a>
    </div>
    <p class="footer__copy">Designed to match the Lynote.ai visual language.</p>
  </div>
</footer>

<style>
  .footer {
    margin-top: auto;
    padding: var(--space-12) var(--space-6) var(--space-8);
    text-align: center;
  }

  .footer__inner {
    max-width: 720px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-3);
  }

  .footer__tagline {
    color: var(--text-secondary);
    font-size: var(--text-sm);
    font-weight: 500;
  }

  .footer__links {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    color: var(--text-muted);
    font-size: var(--text-sm);
  }

  .footer__links a {
    color: var(--text-secondary);
    font-weight: 500;
  }

  .footer__links a:hover {
    color: var(--color-primary-600);
  }

  .footer__divider {
    color: var(--border-color);
  }

  .footer__copy {
    color: var(--text-muted);
    font-size: var(--text-xs);
  }
</style>
