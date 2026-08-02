<script>
  import { fly, fade } from 'svelte/transition';

  import Header from './lib/Header.svelte';
  import Footer from './lib/Footer.svelte';
  import TextArea from './lib/TextArea.svelte';
  import Select from './lib/Select.svelte';
  import Button from './lib/Button.svelte';
  import LoadingSpinner from './lib/LoadingSpinner.svelte';
  import ResultCard from './lib/ResultCard.svelte';
  import ErrorAlert from './lib/ErrorAlert.svelte';
  import { humanizeText } from './lib/api.js';

  let text = '';
  let method = 'translation_chain';
  let language = 'en';
  const tier = 'standard';

  let result = '';
  let originalText = '';
  let processingTimeMs = 0;
  let methodUsed = '';
  let loading = false;
  let error = '';
  let validationError = '';

  $: charCount = text.length;
  $: if (text.trim() && validationError) validationError = '';

  const MAX_CHARS = 5000;

  const methods = [
    { value: 'translation_chain', label: 'Translation Chain' },
    { value: 'llm_rewrite', label: 'LLM Rewrite' },
    { value: 'detection_guided', label: 'Detection Guided' },
    { value: 'mixed_engine', label: 'Mixed Engine' },
  ];

  const languages = [
    { value: 'en-US', label: 'English (US)' },
    { value: 'en', label: 'English' },
    { value: 'fr-FR', label: 'French' },
    { value: 'zh-CN', label: 'Chinese (Simplified)' },
    { value: 'ja-JP', label: 'Japanese' },
  ];

  function extractOutput(data) {
    if (typeof data === 'string') return data;
    if (!data || typeof data !== 'object') return '';
    return data.humanized_text ?? data.result ?? data.text ?? '';
  }

  function validateInput() {
    error = '';
    validationError = '';

    const trimmed = text.trim();
    if (!trimmed) {
      validationError = 'Please enter some text to humanize.';
      return false;
    }

    if (trimmed.length > MAX_CHARS) {
      validationError = `Text is over ${MAX_CHARS.toLocaleString()} characters. This may fail for methods with strict length limits.`;
    }

    return true;
  }

  async function humanize() {
    if (loading) return;
    if (!validateInput()) return;

    loading = true;
    error = '';
    result = '';
    originalText = text.trim();

    try {
      // Always send the payload as a plain object; api.js will JSON.stringify it.
      const data = await humanizeText({ text, method, language, tier });
      result = extractOutput(data);
      processingTimeMs = data.processing_time_ms ?? 0;
      methodUsed = data.method ?? method;
    } catch (e) {
      console.error('[App] humanize failed:', e);
      result = '';
      error = e.message || 'An unexpected error occurred.';
    } finally {
      loading = false;
    }
  }

  function handleKeydown(event) {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      humanize();
    }
  }

  const sampleText =
    "The implementation of artificial intelligence in educational settings has fundamentally transformed the landscape of modern pedagogy.";

  function fillSample() {
    text = sampleText;
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="page">
  <!-- <Header /> -->

  <main class="main">
    <section class="hero" in:fly={{ y: -20, duration: 600 }}>
      <span class="hero__eyebrow">AI Text Humanizer</span>
      <h1 class="hero__title">
        Make AI-written text sound
        <span class="hero__highlight">genuinely human</span>
      </h1>
      <p class="hero__subtitle">
        Paste your text, choose a method, and let the pipeline rewrite it with
        natural rhythm, varied vocabulary, and cross-engine translation.
      </p>
    </section>

    <section class="workspace" in:fly={{ y: 20, duration: 600, delay: 150 }}>
      <div class="card input-card">
        <div class="input-card__top">
          <TextArea
            id="source-text"
            label="Source text"
            bind:value={text}
            placeholder="Paste AI-generated text here..."
            rows={8}
          />

          <div class="input-meta">
            <span class="char-counter" class:char-counter--over={charCount > MAX_CHARS}>
              {charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters
            </span>
          </div>

          {#if validationError}
            <p class="validation-message" role="alert">{validationError}</p>
          {/if}

          <div class="input-card__hint">
            <button class="hint-link" on:click={fillSample} type="button">
              Try sample text
            </button>
            <span class="hint-shortcut">Ctrl/⌘ + Enter to run</span>
          </div>
        </div>

        <div class="controls-row">
          <Select
            id="method"
            label="Method"
            bind:value={method}
            options={methods}
          />
          <Select
            id="language"
            label="Language"
            bind:value={language}
            options={languages}
          />
        </div>

        <ErrorAlert message={error} />

        <div class="action-row">
          <Button
            type="primary"
            size="lg"
            fullWidth={true}
            disabled={loading}
            on:click={humanize}
          >
            {#if loading}
              <LoadingSpinner size="sm" />
              Humanizing...
            {:else}
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M12 20h9" />
                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
              </svg>
              Humanize Text
            {/if}
          </Button>
        </div>
      </div>

      {#if result}
        <div class="result-wrapper">
          <ResultCard
            {result}
            original={originalText}
            {processingTimeMs}
            {methodUsed}
          />
        </div>
      {:else if loading}
        <div class="placeholder" in:fade={{ duration: 200 }}>
          <div class="placeholder__shimmer"></div>
          <p class="placeholder__text">Rewriting your text through the humanization pipeline...</p>
        </div>
      {/if}
    </section>
  </main>

  <Footer />
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }

  .main {
    flex: 1;
    width: 100%;
    max-width: 840px;
    margin: 0 auto;
    padding: var(--space-8) var(--space-6) var(--space-12);
    display: flex;
    flex-direction: column;
    gap: var(--space-10);
  }

  /* Hero */
  .hero {
    text-align: center;
    max-width: 680px;
    margin: 0 auto;
  }

  .hero__eyebrow {
    display: inline-flex;
    padding: var(--space-2) var(--space-4);
    border-radius: var(--radius-full);
    background: rgba(124, 58, 237, 0.08);
    color: var(--color-primary-600);
    font-size: var(--text-xs);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: var(--space-5);
  }

  @media (prefers-color-scheme: dark) {
    .hero__eyebrow {
      background: rgba(167, 139, 250, 0.12);
      color: var(--color-primary-400);
    }
  }

  .hero__title {
    font-size: var(--text-3xl);
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.04em;
    margin-bottom: var(--space-5);
    color: var(--text-primary);
  }

  .hero__highlight {
    background: var(--gradient-primary);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    position: relative;
    display: inline;
  }

  .hero__subtitle {
    font-size: var(--text-lg);
    color: var(--text-secondary);
    line-height: 1.7;
    max-width: 560px;
    margin: 0 auto;
  }

  /* Workspace */
  .workspace {
    display: flex;
    flex-direction: column;
    gap: var(--space-8);
    width: 100%;
  }

  .card {
    background: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-lg);
  }

  .input-card {
    padding: var(--space-8);
    display: flex;
    flex-direction: column;
    gap: var(--space-6);
    position: relative;
  }

  .input-card::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: var(--gradient-card-shine);
    opacity: 0.5;
    pointer-events: none;
  }

  .input-card__top {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .input-meta {
    display: flex;
    justify-content: flex-end;
  }

  .char-counter {
    font-size: var(--text-xs);
    font-weight: 500;
    color: var(--text-muted);
    transition: color var(--transition-fast);
  }

  .char-counter--over {
    color: var(--text-error);
    font-weight: 700;
  }

  .validation-message {
    margin: var(--space-1) 0 0;
    padding: var(--space-3) var(--space-4);
    border-radius: var(--radius-md);
    background: var(--bg-error);
    color: var(--text-error);
    font-size: var(--text-sm);
    font-weight: 600;
    line-height: 1.5;
  }

  .input-card__hint {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-4);
    font-size: var(--text-sm);
  }

  .hint-link {
    padding: 0;
    border: none;
    background: transparent;
    color: var(--color-primary-600);
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
  }

  .hint-link:hover {
    text-decoration: underline;
  }

  .hint-shortcut {
    color: var(--text-muted);
    font-size: var(--text-xs);
  }

  .controls-row {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-5);
  }

  .action-row {
    padding-top: var(--space-2);
  }

  .result-wrapper {
    width: 100%;
  }

  /* Loading placeholder */
  .placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-5);
    padding: var(--space-12) var(--space-6);
    text-align: center;
    color: var(--text-secondary);
  }

  .placeholder__shimmer {
    width: 100%;
    max-width: 400px;
    height: 120px;
    border-radius: var(--radius-lg);
    background: linear-gradient(
      90deg,
      var(--bg-hover) 25%,
      var(--bg-hover-strong) 50%,
      var(--bg-hover) 75%
    );
    background-size: 200% 100%;
    animation: shimmer 1.6s infinite linear;
  }

  .placeholder__text {
    font-size: var(--text-sm);
    font-weight: 500;
  }

  /* Responsive */
  @media (max-width: 640px) {
    .main {
      padding: var(--space-6) var(--space-4) var(--space-10);
      gap: var(--space-8);
    }

    .input-card {
      padding: var(--space-5);
      gap: var(--space-5);
    }

    .controls-row {
      grid-template-columns: 1fr;
    }

    .hero__title {
      font-size: var(--text-2xl);
    }

    .hero__subtitle {
      font-size: var(--text-base);
    }

    .input-card__hint {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-2);
    }
  }
</style>
