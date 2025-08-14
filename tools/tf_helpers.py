import os, pathlib, logging
from tools.util import sh

log = logging.getLogger("gwm.tf")

def split_markdown_to_tf(md_path, out_dir):
    import re
    FENCE_RE = re.compile(r"```(?:hcl|terraform|tf)?\s*([\s\S]*?)```", re.IGNORECASE)
    text = open(md_path).read()
    blocks = FENCE_RE.findall(text)
    os.makedirs(out_dir, exist_ok=True)
    files=[]
    for i, b in enumerate(blocks, start=1):
        path = os.path.join(out_dir, f"gen_{i:03}.tf")
        open(path,"w").write(b.strip()+"\n")
        files.append(path)
    return files

def terraform_validate(dirpath):
    sh(f"terraform -chdir={dirpath} fmt -recursive")
    sh(f"terraform -chdir={dirpath} init -backend=false")
    sh(f"terraform -chdir={dirpath} validate")
