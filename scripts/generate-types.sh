#!/usr/bin/env bash
# generate-types.sh — Export Pydantic JSON Schemas and convert to TypeScript.
#
# Usage:
#   ./scripts/generate-types.sh
#
# Prerequisites:
#   npm i -g json-schema-to-typescript   (or use npx)
#   uv (for running the backend Python)
#
# Output:
#   frontend/src/lib/generated-types.ts
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
SCHEMA_DIR="$PROJECT_ROOT/.tmp-schemas"
OUTPUT_FILE="$FRONTEND_DIR/src/lib/generated-types.ts"

# Clean up temp dir on exit
trap 'rm -rf "$SCHEMA_DIR"' EXIT
mkdir -p "$SCHEMA_DIR"

echo "▸ Exporting Pydantic schemas to JSON Schema..."
cd "$BACKEND_DIR"
uv run python -c "
import json, pathlib, sys
from app.schemas.file_schemas import FileUploadResponse, FileInfo
from app.schemas.item_schemas import BoQItemSchema, StatusUpdate, CellUpdate
from app.schemas.match_schemas import (
    MatchRequest, MatchResult, MatchGroup, MatchResponse,
    PriceHistoryRequest, PriceHistoryInstance, PriceHistoryResponse,
)
from app.schemas.chat_schemas import ChatRequest, ChatMessageSchema

out = pathlib.Path(sys.argv[1])
models = [
    FileUploadResponse, FileInfo,
    BoQItemSchema, StatusUpdate, CellUpdate,
    MatchRequest, MatchResult, MatchGroup, MatchResponse,
    PriceHistoryRequest, PriceHistoryInstance, PriceHistoryResponse,
    ChatRequest, ChatMessageSchema,
]
for m in models:
    schema = m.model_json_schema()
    (out / f'{m.__name__}.json').write_text(json.dumps(schema, indent=2))
    print(f'  ✓ {m.__name__}')
" "$SCHEMA_DIR"

echo "▸ Converting JSON Schema → TypeScript..."
{
  echo "/* Auto-generated from backend Pydantic schemas — do not edit manually. */"
  echo "/* Run: ./scripts/generate-types.sh */"
  echo ""
} > "$OUTPUT_FILE"

for schema_file in "$SCHEMA_DIR"/*.json; do
  name="$(basename "$schema_file" .json)"
  npx --yes json-schema-to-typescript "$schema_file" --bannerComment "" >> "$OUTPUT_FILE" 2>/dev/null
  echo "  ✓ $name"
done

echo ""
echo "✓ Generated $(wc -l < "$OUTPUT_FILE") lines → $OUTPUT_FILE"
