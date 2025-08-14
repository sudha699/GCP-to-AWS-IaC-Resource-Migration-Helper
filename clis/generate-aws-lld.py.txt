#!/usr/bin/env python3
import sys, json, os, logging
from tools.docx_lld import fill_lld_template
from tools.llm_client import LLMClient
from tools.util import load_yaml

logging.basicConfig(level=logging.INFO)
cfg = load_yaml("config/config.yaml")
llm = LLMClient(cfg)

mapping_json = sys.argv[1]
tf_dir = sys.argv[2]
template = sys.argv[3]
out_docx = sys.argv[4]

mapping = json.load(open(mapping_json))
# create a context for LLD doc: populate top-level known fields
context = {
    "PROJECT_NAME": mapping.get("project_name","<project>"),
    "VPC_TOPOLOGY": mapping.get("vpc","see attached"),
    "ESTIMATED_COST": mapping.get("estimated_cost","TBD"),
    "SECURITY_CONTROLS": mapping.get("security","TBD"),
}
# ask LLM to generate descriptive sections for LLD
system = "You are a cloud solutions architect. Produce concise LLD text for the following mapping and terraform code overview."
user = f"Mapping summary:\n```json\n{json.dumps(mapping)[:20000]}\n```\n\nTerraform files are in {tf_dir} (assume standard AWS resources created). Provide: executive summary, network topology text, IAM design, storage & data migration notes, cutover approach and rollback steps (concise)."

lld_text = llm.chat(system, user)
# inject into docx template placeholders using simple keys
context["EXEC_SUMMARY"] = lld_text[:10000]
fill_lld_template(template, out_docx, context)
print("[✓] LLD document generated:", out_docx)
