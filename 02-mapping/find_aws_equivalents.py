import os
import sys
import json
import requests
import csv

# This script takes a JSON list of GCP resources and uses the Gemini API
# to find the equivalent AWS services and details.

# --- Configuration ---
# Set your Gemini API key and endpoint as environment variables
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_API_ENDPOINT = "https://your-gemini-api-endpoint/v1/models/gemini-pro:generateContent?key="

def call_gemini(prompt):
    """
    Calls the Gemini API with a given prompt and returns the response.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    headers = {"Content-Type": "application/json"}
    url = f"{GEMINI_API_ENDPOINT}{GEMINI_API_KEY}"
    
    # A generic request body for Gemini API. Adjust as per your provider's spec.
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
        
        # Adjust based on the actual API response structure
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}", file=sys.stderr)
        return None

def main(gcp_resource_list_file, output_csv_file):
    """
    Main function to orchestrate the mapping process.
    """
    if not os.path.exists(gcp_resource_list_file):
        print(f"Input file not found: {gcp_resource_list_file}", file=sys.stderr)
        sys.exit(1)
    
    print(f"[*] Reading GCP resources from: {gcp_resource_list_file}")
    with open(gcp_resource_list_file, 'r') as f:
        gcp_resources = json.load(f)

    if not gcp_resources:
        print("[!] No resources found. Exiting.", file=sys.stderr)
        sys.exit(0)

    print("[*] Generating prompt for Gemini API...")
    prompt = (
        "You are an expert cloud architect. I have a list of GCP resources. "
        "Your task is to identify the most suitable equivalent AWS service for each. "
        "Respond only with a CSV string. The columns should be: "
        "'GCP_Resource', 'AWS_Equivalent_Service', 'Details'. "
        "The 'Details' column should be a short, concise description of the mapping and any considerations. "
        "Here is the list of GCP resources:\n"
        f"{', '.join(gcp_resources)}"
    )

    print("[*] Calling Gemini API to get AWS equivalents...")
    gemini_response = call_gemini(prompt)

    if not gemini_response:
        print("[!] Failed to get a response from Gemini.", file=sys.stderr)
        sys.exit(1)
    
    print("[*] Writing mapping to CSV file.")
    with open(output_csv_file, 'w', newline='') as csvfile:
        csvfile.write(gemini_response)

    print(f"[✓] AWS mapping saved to: {output_csv_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 find_aws_equivalents.py <GCP_RESOURCE_LIST_JSON> <OUTPUT_CSV_FILE>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    main(input_file, output_file)
