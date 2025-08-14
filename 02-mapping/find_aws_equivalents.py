#!/usr/bin/env python3
import os
import requests
import json
import csv
import sys
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

# --- Configuration ---
# Your Gemini API key, retrieved from environment variables for security.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# The correct base endpoint for the Gemini API.
# Note: This should NOT include 'https://' or any path.
GEMINI_API_ENDPOINT = "generativelanguage.googleapis.com"
GEMINI_MODEL = "gemini-1.0-pro"
OUTPUT_HEADERS = ['GCP_Resource', 'AWS_Equivalent_Service', 'Details']

def call_gemini(prompt):
    """
    Calls the Gemini API with a given prompt and returns the response.
    """
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY environment variable not set. Please set it before running the script.", file=sys.stderr)
        return None

    try:
        # Corrected URL construction:
        # 1. Adds the 'https://' scheme.
        # 2. Includes the full API path.
        # 3. Appends the API key as a query parameter.
        url = f"https://{GEMINI_API_ENDPOINT}/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        # Use requests.post for a POST request.
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
        
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
        gcp_resources_data = json.load(f)

    if not gcp_resources_data:
        print("[!] No resources found. Exiting.", file=sys.stderr)
        sys.exit(0)

    # The 'gcloud asset search-all-resources' command outputs a list of dictionaries.
    # This list comprehension extracts just the string 'name' from each dictionary.
    try:
        gcp_resource_names = [res['name'] for res in gcp_resources_data]
    except (TypeError, KeyError) as e:
        print(f"[!] Error parsing input JSON. Ensure it's a list of objects with a 'name' key. Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    print("[*] Generating prompt for Gemini API...")
    prompt = (
        "You are an expert cloud architect. I have a list of GCP resources. "
        "Your task is to identify the most suitable equivalent AWS service for each. "
        "Respond only with a CSV string. The columns should be: "
        "'GCP_Resource', 'AWS_Equivalent_Service', 'Details'. "
        "The 'Details' column should be a short, concise description of the mapping and any considerations. "
        "Here is the list of GCP resources:\n"
        f"{', '.join(gcp_resource_names)}"
    )

    print("[*] Calling Gemini API to get AWS equivalents...")
    gemini_response = call_gemini(prompt)

    if not gemini_response:
        print("[!] Failed to get a response from Gemini. Exiting.", file=sys.stderr)
        sys.exit(1)
    
    print("[*] Writing mapping to CSV file.")
    # The response might contain extra whitespace or markdown ticks.
    cleaned_response = gemini_response.strip('` \n').replace('`csv', '')
    
    with open(output_csv_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Check if Gemini included headers in the response. If not, add them.
        csv_lines = cleaned_response.split('\n')
        if not csv_lines[0].lower().startswith(OUTPUT_HEADERS[0].lower()):
            writer.writerow(OUTPUT_HEADERS)

        for line in csv_lines:
            writer.writerow(line.split(','))

    print(f"[✓] AWS mapping saved to: {output_csv_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 find_aws_equivalents.py <GCP_RESOURCE_LIST_JSON> <OUTPUT_CSV_FILE>", file=sys.stderr)
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    main(input_file, output_file)


