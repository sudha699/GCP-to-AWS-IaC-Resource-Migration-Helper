import os
import sys
import csv
import requests
import json


# This script takes the AWS service mapping CSV and uses the Gemini API
# to generate the Terraform HCL for the AWS resources.

# --- Configuration ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key="

def call_gemini(prompt):
    """
    Calls the Gemini API with a given prompt and returns the response.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    headers = {"Content-Type": "application/json"}
    url = f"{GEMINI_API_ENDPOINT}{GEMINI_API_KEY}"
    
    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}", file=sys.stderr)
        return None

def main(mapping_csv_file, output_tf_file):
    """
    Main function to orchestrate the Terraform generation.
    """
    if not os.path.exists(mapping_csv_file):
        print(f"Input mapping file not found: {mapping_csv_file}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Reading AWS mapping from: {mapping_csv_file}")
    aws_services = []
    with open(mapping_csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            aws_services.append(row['AWS_Equivalent_Service'])
    
    if not aws_services:
        print("[!] No AWS services found in mapping file. Exiting.", file=sys.stderr)
        sys.exit(0)

    print("[*] Generating prompt for Gemini API to create Terraform HCL...")
    prompt = (
        "You are an expert in Terraform. I need you to generate a valid Terraform configuration "
        "for the following list of AWS services. "
        "The HCL should be modular and follow best practices, including using variables for sensitive or dynamic values "
        "(e.g., vpc_id, instance_type, region). "
        "Please include a `terraform` block with required providers and a `provider` block. "
        "Add a `tags = { 'migrated-from' = 'gcp' }` on every resource where applicable. "
        "Provide only the raw HCL code, no markdown or extra text. "
        "Here is the list of AWS services:\n"
        f"{', '.join(aws_services)}"
    )

    print("[*] Calling Gemini API to generate Terraform code...")
    terraform_code = call_gemini(prompt)

    if not terraform_code:
        print("[!] Failed to get a response from Gemini.", file=sys.stderr)
        sys.exit(1)
    
    print("[*] Writing generated Terraform code to file.")
    with open(output_tf_file, 'w') as f:
        f.write(terraform_code)

    print(f"[✓] AWS Terraform configuration saved to: {output_tf_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 generate_aws_tf.py <AWS_MAPPING_CSV> <OUTPUT_TF_FILE>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    main(input_file, output_file)

