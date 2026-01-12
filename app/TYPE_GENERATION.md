# TypeScript Type Generation from FastAPI

This project automatically generates TypeScript types from the FastAPI backend, ensuring type safety across the full stack.

## Setup Complete ✓

The following tools have been installed and configured:

- **openapi-typescript**: Generates TypeScript types from OpenAPI schemas
- **openapi-fetch**: Type-safe fetch client with full autocomplete support

## How It Works

1. **FastAPI generates OpenAPI schema** - Your Pydantic models automatically generate an OpenAPI specification
2. **Python script extracts schema** - `api/generate_openapi.py` exports the schema to JSON
3. **openapi-typescript converts to TS** - Types are generated in `app/src/types/api.ts`
4. **Type-safe client** - `app/src/lib/api.ts` provides fully typed API calls

## Generating Types

### Option 1: Using npm (from app directory)
```bash
npm run generate:types
```

### Option 2: Using make (from project root)
```bash
make types
```

### Option 3: Watch mode (requires API server running)
```bash
npm run generate:types:watch
```

## Usage Example

```typescript
import { generateMidi } from "./lib/api";

// Full type safety with autocomplete!
const result = await generateMidi({
  user_id: "uuid-here",
  thread_id: "uuid-here",
  prompt: "A happy melody in C major",
  key: "C",        // ✓ Autocomplete for valid keys
  bpm: 120,        // ✓ Enforces 30-360 range
  time_signature: "4/4",  // ✓ Autocomplete for valid signatures
  measures: 4,     // ✓ Enforces 1-32 range
});

if (result.data) {
  // Response is fully typed
  console.log(result.data.plan.key);     // Autocomplete works!
  console.log(result.data.plan.bpm);
  console.log(result.data.midi);         // Array<MidiEvent>
}
```

See `app/src/lib/example.ts` for more examples.

## When to Regenerate Types

Regenerate types whenever you:
- Add or modify Pydantic models in the backend
- Add or modify API endpoints
- Change request/response structures

**Tip**: Run `make types` after pulling backend changes to stay in sync.

## Additional Tooling Recommendations

### 1. **React Query / TanStack Query** (Highly Recommended)
For better data fetching, caching, and state management:

```bash
npm install @tanstack/react-query
```

Example integration:
```typescript
import { useQuery } from "@tanstack/react-query";
import { checkHealth } from "./lib/api";

function HealthStatus() {
  const { data, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: checkHealth,
  });

  if (isLoading) return <div>Loading...</div>;
  return <div>Status: {data?.data?.status}</div>;
}
```

### 2. **Zod** (Already in your dependencies!)
I notice you already have Zod installed. You can use it for runtime validation:

```bash
npm install zod-openapi
```

This allows generating Zod schemas from OpenAPI for runtime validation.

### 3. **openapi-react-query**
Automatically generate React Query hooks from your OpenAPI schema:

```bash
npm install --save-dev @openapi-codegen/cli @openapi-codegen/typescript
```

This would generate hooks like:
```typescript
const { data, isLoading } = useGenerateMidi({
  body: { prompt: "...", ... }
});
```

### 4. **MSW (Mock Service Worker)**
Generate mock API handlers for testing:

```bash
npm install --save-dev msw
```

You can auto-generate MSW handlers from your OpenAPI schema for testing.

## Troubleshooting

### Types are out of sync
```bash
make types
```

### Import errors
Make sure the API server dependencies are installed:
```bash
uv pip install -e .
```

### Python module not found
The project must be installed in editable mode (already done):
```bash
cd /path/to/midi-agent
uv pip install -e .
```

## Project Structure

```
midi-agent/
├── api/
│   ├── main.py                    # FastAPI app
│   ├── midi/
│   │   ├── midi_models.py        # Pydantic models (source of truth)
│   │   └── midi_routes.py        # API endpoints
│   └── generate_openapi.py       # OpenAPI schema generator
└── app/
    ├── src/
    │   ├── types/
    │   │   ├── openapi.json      # Generated OpenAPI schema
    │   │   └── api.ts            # Generated TypeScript types
    │   └── lib/
    │       ├── api.ts            # Type-safe API client
    │       └── example.ts        # Usage examples
    └── package.json              # Type generation scripts
```

## Benefits

✓ **Full type safety** - Catch API mismatches at compile time
✓ **Autocomplete** - IDE suggests valid values for keys, time signatures, etc.
✓ **Single source of truth** - Backend Pydantic models drive app types
✓ **Refactoring safety** - TypeScript errors when backend changes
✓ **Documentation** - Types serve as inline documentation
✓ **Developer experience** - Fast feedback loop with type errors
