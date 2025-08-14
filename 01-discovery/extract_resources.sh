#!/usr/bin/env bash

# This script performs a comprehensive discovery of a GCP project,
# including all resources, IAM policies, various service configurations,
# and detailed GKE cluster/workload information for a robust migration plan.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration and Dependency Check ---
GCP_PROJECT_ID="$1"
TERRAFORM_STATE_FILE="$2"
OUTPUT_DIR="01-discovery/outputs/${GCP_PROJECT_ID}"

command -v gcloud >/dev/null 2>&1 || { echo >&2 "gcloud is not installed. Aborting."; exit 1; }
command -v jq >/dev/null 2>&1 || { echo >&2 "jq is not installed. Aborting."; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo >&2 "kubectl is not installed. GKE workload discovery will be skipped."; }

if [[ -z "$GCP_PROJECT_ID" ]]; then
    echo "Usage: $0 <GCP_PROJECT_ID> [TERRAFORM_STATE_FILE]"
    exit 1
fi

echo "[*] Ensuring output directory exists: ${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

# --- 1. Project-Level Information ---
echo "[*] Capturing project metadata..."
gcloud projects describe "${GCP_PROJECT_ID}" --format=json > "${OUTPUT_DIR}/project_metadata.json"

echo "[*] Listing all enabled services/APIs..."
gcloud services list --enabled --project="${GCP_PROJECT_ID}" --format=json > "${OUTPUT_DIR}/enabled_services.json"

# --- 2. Resource Discovery (Combined) ---
echo "[*] Discovering resources using gcloud asset inventory..."
gcloud asset search-all-resources --scope=projects/"${GCP_PROJECT_ID}" --format="json" > "${OUTPUT_DIR}/gcloud_resources.json"

TEMP_TF_RESOURCES_FILE="${OUTPUT_DIR}/terraform_resources_temp.json"
if [[ -n "$TERRAFORM_STATE_FILE" ]]; then
    if [[ ! -f "$TERRAFORM_STATE_FILE" ]]; then
        echo "[!] Terraform state file not found at: ${TERRAFORM_STATE_FILE}. Skipping."
    else
        echo "[*] Extracting resources from Terraform state file: ${TERRAFORM_STATE_FILE}"
        jq -r '[.resources[].instances[].attributes.id]' "${TERRAFORM_STATE_FILE}" > "${TEMP_TF_RESOURCES_FILE}"
    fi
fi

if [[ -f "${TEMP_TF_RESOURCES_FILE}" ]]; then
    jq -s '.[0] + .[1] | unique' "${OUTPUT_DIR}/gcloud_resources.json" "${TEMP_TF_RESOURCES_FILE}" > "${OUTPUT_DIR}/all_resources_combined.json"
    rm "${TEMP_TF_RESOURCES_FILE}"
else
    cp "${OUTPUT_DIR}/gcloud_resources.json" "${OUTPUT_DIR}/all_resources_combined.json"
fi

echo "[✓] Combined resource list saved to: ${OUTPUT_DIR}/all_resources_combined.json"

# --- 3. Security and IAM Configuration ---
echo "[*] Capturing all IAM policies..."
gcloud asset search-all-iam-policies --scope=projects/"${GCP_PROJECT_ID}" --format=json > "${OUTPUT_DIR}/iam_policies.json"

echo "[*] Listing all firewall rules..."
gcloud compute firewall-rules list --project="${GCP_PROJECT_ID}" --format=json > "${OUTPUT_DIR}/firewall_rules.json"

# --- 4. Networking ---
echo "[*] Listing all VPC subnets..."
gcloud compute networks subnets list --project="${GCP_PROJECT_ID}" --format=json > "${OUTPUT_DIR}/subnets.json"

# --- 5. Application and Data Services ---
echo "[*] Listing Pub/Sub topics and subscriptions..."
gcloud pubsub topics list --project="${GCP_PROJECT_ID}" --format=json > "${OUTPUT_DIR}/pubsub_topics.json"
gcloud pubsub subscriptions list --project="${GCP_PROJECT_ID}" --format=json > "${OUTPUT_DIR}/pubsub_subscriptions.json"

echo "[*] Listing Secret Manager secrets..."
gcloud secrets list --project="${GCP_PROJECT_ID}" --format=json > "${OUTPUT_DIR}/secrets.json"

echo "[*] Listing BigQuery datasets..."
gcloud alpha bq datasets list --project="${GCP_PROJECT_ID}" --format=json > "${OUTPUT_DIR}/bq_datasets.json"

# --- 6. GKE and Kubernetes Configuration ---
echo ""
echo "--- GKE and Kubernetes Discovery ---"
if ! command -v kubectl >/dev/null 2>&1; then
  echo "[!] kubectl not found. GKE workload discovery will be skipped."
else
  # Get list of GKE clusters
  GKE_CLUSTERS=$(gcloud container clusters list --project="${GCP_PROJECT_ID}" --format="json" || echo "[]")

  if [[ $(echo "$GKE_CLUSTERS" | jq 'length') -eq 0 ]]; then
      echo "[*] No GKE clusters found in project: ${GCP_PROJECT_ID}"
  else
      echo "$GKE_CLUSTERS" > "${OUTPUT_DIR}/gke_clusters.json"
      echo "[*] Found GKE clusters. Exporting cluster configs and workloads..."

      # Loop through each cluster and export its details and workloads
      echo "$GKE_CLUSTERS" | jq -c '.[]' | while read -r CLUSTER_JSON; do
          CLUSTER_NAME=$(echo "$CLUSTER_JSON" | jq -r '.name')
          CLUSTER_LOCATION=$(echo "$CLUSTER_JSON" | jq -r '.location')
          
          echo "  > Processing cluster: ${CLUSTER_NAME} in ${CLUSTER_LOCATION}"

          # Export node pool list
          gcloud container node-pools list --project="${GCP_PROJECT_ID}" --cluster="${CLUSTER_NAME}" --format=json > "${OUTPUT_DIR}/gke_node_pools_${CLUSTER_NAME}.json"

          # Get credentials for kubectl
          gcloud container clusters get-credentials "${CLUSTER_NAME}" --region="${CLUSTER_LOCATION}" --project="${GCP_PROJECT_ID}"

          # Export all Kubernetes workloads and resources
          kubectl get all --all-namespaces -o yaml > "${OUTPUT_DIR}/k8s_workloads_${CLUSTER_NAME}.yaml"
          kubectl get deployments,services,ingresses,configmaps,secrets,persistentvolumeclaims,storageclass --all-namespaces -o yaml > "${OUTPUT_DIR}/k8s_workloads_${CLUSTER_NAME}_detailed.yaml"

      done
      echo "[✓] GKE cluster and workload discovery complete."
  fi
fi

# --- 7. Final Summary ---
echo ""
echo "--- Discovery Complete ---"
echo "All inventory files have been saved to the directory:"
echo "${OUTPUT_DIR}"
