System: Map GCP resources to AWS.

User: Provided an inventory JSON. For each resource, return a JSON array item:
{
  "gcp_type": "...",
  "gcp_name": "...",
  "aws_suggested_service": "...",
  "aws_resource_type": "...",
  "complexity": "Low|Medium|High",
  "notes": "..."
}
