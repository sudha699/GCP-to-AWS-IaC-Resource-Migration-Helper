#!/usr/bin/env bash

# This script orchestrates the entire GCP-to-AWS migration process,
# executing discovery, mapping, IaC generation, and LLD creation.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
GCP_PROJECT_ID="$1"
TF_STATE_FILE="$2"
AWS_ACCOUNT_ID="$3"
AWS_REGION="$4"

if [[ -z "$GCP_PROJECT_ID" || -z "$TF_STATE_FILE" || -z "$AWS_ACCOUNT_ID" || -z "$AWS_REGION" ]]; then
    echo "Usage: $0 <GCP_PROJECT_ID> <TF_STATE_FILE> <AWS_ACCOUNT_ID> <AWS_REGION>"
    exit 1
fi

# --- Set up environment variables for Python scripts ---
export GCP_PROJECT_ID
export AWS_ACCOUNT_ID
export AWS_REGION

# --- You must set your Gemini API Key before running ---
# export GEMINI_API_KEY="your-api-key-here"

# --- Define input and output files based on the project ID ---
DISCOVERY_OUT_DIR="01-discovery/outputs/${GCP_PROJECT_ID}"
DISCOVERY_OUT_FILE="${DISCOVERY_OUT_DIR}/gcp_resources.json"

MAPPING_OUT_DIR="02-mapping/outputs/${GCP_PROJECT_ID}"
MAPPING_OUT_FILE="${MAPPING_OUT_DIR}/service_mapping.csv"

IAC_OUT_DIR="03-iac-gen/outputs/${GCP_PROJECT_ID}"
IAC_OUT_FILE="${IAC_OUT_DIR}/aws_iac.tf"

LLD_OUT_DIR="04-lld-gen/outputs/${GCP_PROJECT_ID}"
LLD_OUT_FILE="${LLD_OUT_DIR}/lld_document.docx"


echo "--- Starting GCP to AWS Migration Tool ---"
echo "Project: ${GCP_PROJECT_ID}"

# --- Step 1: Discover GCP Resources ---
echo ""
echo "[*] STEP 1: Discovering and combining GCP resources..."
mkdir -p "${DISCOVERY_OUT_DIR}"
bash 01-discovery/extract_resources.sh "${GCP_PROJECT_ID}" "${TF_STATE_FILE}"
echo "[✓] Step 1 Complete."

# --- Step 2: Find AWS Equivalents ---
echo ""
echo "[*] STEP 2: Finding equivalent AWS services using Gemini..."
mkdir -p "${MAPPING_OUT_DIR}"
python3 02-mapping/find_aws_equivalents.py "${DISCOVERY_OUT_FILE}" "${MAPPING_OUT_FILE}"
echo "[✓] Step 2 Complete."

# --- Step 3: Generate AWS Terraform HCL ---
echo ""
echo "[*] STEP 3: Generating AWS Terraform configuration using Gemini..."
mkdir -p "${IAC_OUT_DIR}"
python3 03-iac-gen/generate_aws_tf.py "${MAPPING_OUT_FILE}" "${IAC_OUT_FILE}"
echo "[✓] Step 3 Complete."

# --- Step 4: Generate LLD Document ---
echo ""
echo "[*] STEP 4: Generating LLD document..."
mkdir -p "${LLD_OUT_DIR}"
python3 04-lld-gen/generate_aws_lld.py "${DISCOVERY_OUT_FILE}" "${MAPPING_OUT_FILE}" "${IAC_OUT_FILE}" "${LLD_OUT_FILE}"
echo "[✓] Step 4 Complete."

echo ""
echo "--- Migration Tool Execution Finished ---"
echo "Outputs are available in the respective 'outputs' directories."
