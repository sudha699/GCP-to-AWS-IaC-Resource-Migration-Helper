#!/usr/bin/env bash

# This script extracts all resources from a GCP project and a local Terraform state file,
# combines them, and saves the unique list to a JSON file.

# Exit immediately if a command exits with a non-zero status.
set -e

# Configuration
GCP_PROJECT_ID="$1"
TERRAFORM_STATE_FILE="$2"
OUTPUT_DIR="01-discovery/outputs/${GCP_PROJECT_ID}"
OUTPUT_FILE="${OUTPUT_DIR}/gcp_resources.json"

# --- Dependencies Check ---
command -v gcloud >/dev/null 2>&1 || { echo >&2 "gcloud is not installed. Aborting."; exit 1; }
command -v jq >/dev/null 2>&1 || { echo >&2 "jq is not installed. Aborting."; exit 1; }

if [[ -z "$GCP_PROJECT_ID" ]]; then
    echo "Usage: $0 <GCP_PROJECT_ID> [TERRAFORM_STATE_FILE]"
    exit 1
fi

echo "[*] Ensuring output directory exists: ${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

echo "[*] Discovering resources using gcloud asset inventory for project: ${GCP_PROJECT_ID}"
# Use gcloud asset search-all-resources to get all resource names
GCLOUD_RESOURCES=$(gcloud asset search-all-resources --scope=projects/"${GCP_PROJECT_ID}" --format="json" | jq -r '.[].name' | sort -u)

# Initialize a list to hold all unique resources
ALL_RESOURCES_LIST=()

# Read the resources from gcloud output
while IFS= read -r resource; do
    ALL_RESOURCES_LIST+=("$resource")
done <<< "$GCLOUD_RESOURCES"

# --- Process Terraform state file if provided ---
if [[ -n "$TERRAFORM_STATE_FILE" ]]; then
    if [[ ! -f "$TERRAFORM_STATE_FILE" ]]; then
        echo "[!] Terraform state file not found at: ${TERRAFORM_STATE_FILE}. Skipping."
    else
        echo "[*] Extracting resources from Terraform state file: ${TERRAFORM_STATE_FILE}"
        # Use jq to get all resource names from the state file
        TERRAFORM_RESOURCES=$(jq -r '.resources[].instances[].attributes.id' "${TERRAFORM_STATE_FILE}" | sort -u)

        while IFS= read -r resource; do
            # Add to the list only if it's not already present
            if ! [[ " ${ALL_RESOURCES_LIST[@]} " =~ " ${resource} " ]]; then
                ALL_RESOURCES_LIST+=("$resource")
            fi
        done <<< "$TERRAFORM_RESOURCES"
    fi
fi

echo "[*] Combining and deduplicating resource lists."
# Convert the array to a JSON array and save it to the output file
printf '%s\n' "${ALL_RESOURCES_LIST[@]}" | jq -R . | jq -s . > "${OUTPUT_FILE}"

echo "[✓] Combined resource list saved to: ${OUTPUT_FILE}"
