#!/bin/bash
set -e

# =========================
# Usage check
# =========================
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <GCP_PROJECT_ID> <TFSTATE_FILE1> [TFSTATE_FILE2 ...]"
    exit 1
fi

PROJECT_ID="$1"
shift
TFSTATE_FILES=("$@")

# =========================
# Variables
# =========================
OUTPUT_DIR="output"
ASSET_FILE="${OUTPUT_DIR}/gcp_assets.json"
TF_RESOURCES_FILE="${OUTPUT_DIR}/tf_resources.json"
COMBINED_OUTPUT="${OUTPUT_DIR}/combined_inventory.json"

mkdir -p "$OUTPUT_DIR"

# =========================
# Extract resource details from multiple Terraform state files
# =========================
echo "[INFO] Extracting Terraform resources from state files..."
> "$TF_RESOURCES_FILE"

for STATE_FILE in "${TFSTATE_FILES[@]}"; do
    if [[ "$STATE_FILE" == gs://* ]]; then
        # Download from GCS if path starts with gs://
        TMP_FILE="$(mktemp)"
        echo "[INFO] Downloading $STATE_FILE ..."
        gsutil cp "$STATE_FILE" "$TMP_FILE"
        STATE_FILE="$TMP_FILE"
    fi

    if [ ! -f "$STATE_FILE" ]; then
        echo "[WARNING] State file $STATE_FILE not found, skipping."
        continue
    fi

    jq -r '.resources[] | 
           {type: .type, name: .name, attributes: (.instances[].attributes // null)}' \
       "$STATE_FILE" >> "$TF_RESOURCES_FILE"
done

# Remove duplicates in TF resources based on resource id
TF_RESOURCES_FILE_SORTED="${OUTPUT_DIR}/tf_resources_dedup.json"
jq -s 'unique_by(.attributes.id)' "$TF_RESOURCES_FILE" > "$TF_RESOURCES_FILE_SORTED"
mv "$TF_RESOURCES_FILE_SORTED" "$TF_RESOURCES_FILE"

# =========================
# Fetch GCP assets using Asset Inventory API
# =========================
echo "[INFO] Fetching GCP assets..."
gcloud asset search-all-resources --project="$PROJECT_ID" --format=json > "$ASSET_FILE"

# Remove duplicates in GCP assets based on name
ASSET_FILE_SORTED="${OUTPUT_DIR}/gcp_assets_dedup.json"
jq 'unique_by(.name)' "$ASSET_FILE" > "$ASSET_FILE_SORTED"
mv "$ASSET_FILE_SORTED" "$ASSET_FILE"

# =========================
# Identify unique resources
# =========================
echo "[INFO] Identifying unique resources..."

TF_IDS=$(jq -r '.attributes.id' "$TF_RESOURCES_FILE" | sort -u)
GCP_IDS=$(jq -r '.name' "$ASSET_FILE" | sort -u)

GCP_ONLY=$(comm -23 <(echo "$GCP_IDS") <(echo "$TF_IDS"))
TF_ONLY=$(comm -13 <(echo "$GCP_IDS") <(echo "$TF_IDS"))

# =========================
# Get full details for unique resources
# =========================
echo "[INFO] Fetching full attributes for unique resources..."

GCP_ONLY_DETAILS=$(jq -c --argjson ids "$(echo "$GCP_ONLY" | jq -Rsc 'split("\n") | map(select(. != ""))')" '
    . as $all
    | $ids
    | map($id | $all[] | select(.name == $id))
' "$ASSET_FILE")

TF_ONLY_DETAILS=$(jq -c --argjson ids "$(echo "$TF_ONLY" | jq -Rsc 'split("\n") | map(select(. != ""))')" '
    . as $all
    | $ids
    | map($id | $all | select(.attributes.id == $id))
' "$TF_RESOURCES_FILE")

# =========================
# Create combined inventory file
# =========================
echo "[INFO] Creating combined unique inventory file..."
jq -n \
  --argjson unique_gcp "$GCP_ONLY_DETAILS" \
  --argjson unique_tf "$TF_ONLY_DETAILS" \
  '{ 
     unique_gcp: $unique_gcp,
     unique_tf: $unique_tf,
     combined_unique: ($unique_gcp + $unique_tf)
   }' > "$COMBINED_OUTPUT"

echo "[SUCCESS] Attribute-rich combined inventory saved to $COMBINED_OUTPUT"
