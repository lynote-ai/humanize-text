<header class="header">
  <div class="header__inner">
    <a href="/" class="header__brand" aria-label="Humanize Text home">
      <span class="header__logo" aria-hidden="true">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="url(#logo-gradient)" />
          <path d="M2 17L12 22L22 17" stroke="url(#logo-gradient-stroke)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M2 12L12 17L22 12" stroke="url(#logo-gradient-stroke-2)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          <defs>
            <linearGradient id="logo-gradient" x1="2" y1="2" x2="22" y2="12" gradientUnits="userSpaceOnUse">
              <stop stop-color="#7c3aed" />
              <stop offset="1" stop-color="#5785fa" />
            </linearGradient>
            <linearGradient id="logo-gradient-stroke" x1="2" y1="17" x2="22" y2="17" gradientUnits="userSpaceOnUse">
              <stop stop-color="#7c3aed" />
              <stop offset="1" stop-color="#5785fa" />
            </linearGradient>
            <linearGradient id="logo-gradient-stroke-2" x1="2" y1="12" x2="22" y2="12" gradientUnits="userSpaceOnUse">
              <stop stop-color="#a78bfa" />
              <stop offset="1" stop-color="#3d96ff" />
            </linearGradient>
          </defs>
        </svg>
      </span>
      <span class="header__name">Humanize Text</span>
    </a>
    <a class="header__link" href="https://github.com/lynote-ai/humanize-text" target="_blank" rel="noopener noreferrer">
      GitHub
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
        <polyline points="15 3 21 3 21 9" />
        <line x1="10" y1="14" x2="21" y2="3" />
      </svg>
    </a>
  </div>
</header>

<style>
  .header {
    position: sticky;
    top: 0;
    z-index: 50;
    width: 100%;
    background: rgba(248, 250, 255, 0.75);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid transparent;
  }

  @media (prefers-color-scheme: dark) {
    .header {
      background: rgba(10, 14, 23, 0.75);
    }
  }

  .header__inner {
    max-width: 1200px;
    margin: 0 auto;
    padding: var(--space-4) var(--space-6);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .header__brand {
    display: inline-flex;
    align-items: center;
    gap: var(--space-3);
    color: var(--text-primary);
    font-weight: 700;
    font-size: var(--text-lg);
    text-decoration: none;
  }

  .header__brand:hover {
    text-decoration: none;
  }

  .header__logo {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .header__name {
    letter-spacing: -0.02em;
  }

  .header__link {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    color: var(--text-secondary);
    font-size: var(--text-sm);
    font-weight: 500;
    text-decoration: none;
  }

  .header__link:hover {
    color: var(--text-primary);
  }

  @media (max-width: 480px) {
    .header__inner {
      padding: var(--space-3) var(--space-4);
    }

    .header__name {
      font-size: var(--text-base);
    }
  }
</style>
