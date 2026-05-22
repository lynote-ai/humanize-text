# n8n Workflow Guide

## What is n8n?

[n8n](https://n8n.io) is an open-source workflow automation tool. The included workflow lets you run the Standard humanization pipeline without writing code.

## Setup

### 1. Import the Workflow

1. Open your n8n instance
2. Go to **Workflows** → **Import from File**
3. Select `n8n/humanize_standard.json`

### 2. Configure API Keys

After importing, you need to set API keys in two places:

**DeepSeek (Steps 1-2):**
- Click on "Step 1: Chinese Rewrite (DeepSeek)" node
- Go to **Authentication** → **Header Auth**
- Set header name: `Authorization`
- Set header value: `Bearer YOUR_DEEPSEEK_KEY`
- Repeat for "Step 2: Japanese Rewrite (DeepSeek)"

**Niutrans (Steps 4-5):**
- Click on "Step 4: German → Spanish (Niutrans)" node
- In the body parameters, replace `YOUR_NIUTRANS_KEY` with your actual key
- Repeat for "Step 5: Spanish → English (Niutrans)"

### 3. Run

1. Click **Execute Workflow**
2. Input your text in the "Input Text" node
3. The humanized result appears in the "Output" node

## Workflow Nodes

```
Start → Input Text → Step 1 (DeepSeek: → Chinese)
  → Step 2 (DeepSeek: → Japanese)
  → Step 3 (Google: → German)
  → Step 4 (Niutrans: → Spanish)
  → Step 5 (Niutrans: → English)
  → Output
```

## Customization

### Change Target Language

In "Step 5", change the `to` parameter from `en` to your target language code (e.g., `fr` for French).

### Batch Processing

Replace the "Start" trigger with a spreadsheet or database trigger to process multiple texts automatically.
