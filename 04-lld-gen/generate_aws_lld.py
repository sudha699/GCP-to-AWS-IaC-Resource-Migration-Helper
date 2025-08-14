import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in environment variables.", file=sys.stderr)
    sys.exit(1)

GEMINI_MODEL = "gemini-1.5-pro"  # Using a more capable model for document generation

def call_gemini(prompt):
    """
    Calls the Gemini API to generate content.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.9,
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
        response_json = response.json()
        
        # Extract the text from the response
        candidates = response_json.get("candidates")
        if candidates and len(candidates) > 0:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts and len(parts) > 0:
                return parts[0].get("text", "")
    except requests.exceptions.RequestException as e:
        print(f"API call failed: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"JSON decoding failed: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return None
        
    return None

def main(input_tf_file, output_lld_file):
    """
    Reads the Terraform code and generates an LLD document.
    """
    if not os.path.exists(input_tf_file):
        print(f"Input Terraform file not found: {input_tf_file}", file=sys.stderr)
        sys.exit(1)
    
    print(f"[*] Reading Terraform code from: {input_tf_file}")
    with open(input_tf_file, 'r') as f:
        terraform_code = f.read()

    if not terraform_code:
        print("[!] No Terraform code found. Exiting.", file=sys.stderr)
        sys.exit(0)

    print("[*] Generating LLD prompt for Gemini API...")
    prompt = (
        "You are an expert cloud architect and technical writer. "
        "Based on the following AWS Terraform HCL code, "
        "write a detailed Low-Level Design (LLD) document in Markdown format. "
        "The LLD should describe the architecture, networking, security considerations, and the purpose of each resource. "
        "Ensure the document is well-structured with clear headings and a professional tone.\n"
        f"AWS Terraform HCL Code:\n\n{terraform_code}"
    )

    print("[*] Calling Gemini API to generate LLD...")
    gemini_response = call_gemini(prompt)

    if not gemini_response:
        print("[!] Failed to get a response from Gemini. Exiting.", file=sys.stderr)
        sys.exit(1)

    print("[*] Writing LLD to Markdown file.")
    
    # --- FIX FOR DIRECTORY NOT FOUND ERROR ---
    output_dir = os.path.dirname(output_lld_file)
    if output_dir and not os.path.exists(output_dir):
        print(f"Creating output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
    # -----------------------------------------
    
    with open(output_lld_file, 'w') as f:
        f.write(gemini_response)

    print(f"[✓] LLD document generated and saved to: {output_lld_file}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 generate_aws_lld.py <AWS_TF_FILE> <OUTPUT_LLD_FILE>", file=sys.stderr)
        sys.exit(1)

    input_tf_file = sys.argv[1]
    output_lld_file = sys.argv[2]
    main(input_tf_file, output_lld_file)
