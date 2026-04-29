# Prompt Schema v1

## Structure

```json
{
  "name": "string - prompt identifier",
  "version": "v1 etc",
  "model": "gpt-4 etc",
  "temperature": 0.2,
  "system_prompt": "full system prompt text",
  "user_prompt_template": "template with {placeholders}",
  "expected_output_schema": {"field": "type", ...},
  "created_at": "YYYY-MM-DD"
}
```

## Usage

1. Version prompts so re-runs are reproducible
2. Record `prompt_version` in parser output
3. Version bump = re-parse (manual for now)

## existing prompts

- `prompts/preflop_analysis_v1.json` - current preflop analysis prompt