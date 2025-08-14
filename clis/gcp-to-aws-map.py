#!/usr/bin/env python3
import sys, json, yaml, logging
from tools.llm_client import LLMClient
from tools.util import load_yaml, write_json

logging.basicConfig(level=logging.INFO)
cfg = load_yaml("config/config.yaml")
llm = LLMClient(cfg)

inv_path = sys.argv[1]
out_path = sys.argv[2]

inventory = json.load(open(inv_path))

system = "You are a cloud-migration expert. Map GCP services to AWS equivalents and estimate complexity (Low/Med/High). Output JSON with fields: gcp_service, gcp_resource_name, suggested_aws_service, aws_resource_type, complexity, notes."

user = f"Inventory (JSON):\n```json\n{json.dumps(inventory)[:15000]}\n```\n\nRules: Use known AWS equivalents; if no direct mapping, put suggested alternative or 'no-direct-equivalent'. Provide concise notes and required actions."

resp = llm.chat(system, user)
# attempt to parse JSON from LLM; fallback to saving plain text mapping.
try:
    mapped = json.loads(resp)
    write_json(out_path, mapped)
    print("[✓] mapping written to", out_path)
except Exception as e:
    # try to extract a JSON code block
    import re
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", resp)
    if m:
        mapped = json.loads(m.group(1))
        write_json(out_path, mapped)
        print("[✓] mapping written (from code fence) to", out_path)
    else:
        open(out_path, "w").write(resp)
        print("[!] mapping saved as text to", out_path)
