#!/usr/bin/env python3
import sys, os, json, logging, pathlib
from tools.llm_client import LLMClient
from tools.tf_helpers import split_markdown_to_tf, terraform_validate
from tools.util import load_yaml

logging.basicConfig(level=logging.INFO)
cfg = load_yaml("config/config.yaml")
llm = LLMClient(cfg)

src_inventory_dir = sys.argv[1]        # e.g., ./output/projectA
mapping_json = sys.argv[2]            # e.g., ./output/projectA/mapping.json
out_tf_dir = sys.argv[3]              # destination for AWS tf

# collect tf snippets from terraformer output
tf_files=[]
for p in pathlib.Path(src_inventory_dir).rglob("*.tf"):
    tf_files.append(str(p))
# build prompt with limited token chunking
chunks=[]
for f in tf_files:
    txt = open(f).read()
    chunks.append({"path":f, "content": txt[:12000]})
prompt_parts = []
for c in chunks[:20]:
    prompt_parts.append(f"### FILE: {c['path']}\n```hcl\n{c['content']}\n```")

system = "You are a deterministic Terraform translator. Convert Google provider blocks to AWS provider equivalents. Use modules when helpful. Do not invent values. Add TODO comments for any manual decisions."

user = f"Mapping JSON:\n```json\n{open(mapping_json).read()}\n```\n\nHCL snippets:\n" + "\n\n".join(prompt_parts)

resp = llm.chat(system, user)
# save response and split into .tf files
os.makedirs(out_tf_dir, exist_ok=True)
md_path = os.path.join(out_tf_dir, "aws_iac_generated.md")
open(md_path,"w").write(resp)
print("WROTE", md_path)
# split code fences into TF files
split_markdown_to_tf(md_path, out_tf_dir)
try:
    terraform_validate(out_tf_dir)
    print("[✓] terraform validate success")
except Exception as e:
    print("[!] terraform validate FAILED; inspect", out_tf_dir)
