import os, re, json, requests, logging
from tools.util import retry, load_yaml

log = logging.getLogger("gwm.llm")
FENCE_RE = re.compile(r"```(?:hcl|terraform|json|tf|yaml|yml)?\s*([\s\S]*?)```", re.IGNORECASE)

class LLMClient:
    def __init__(self, cfg):
        self.cfg = cfg
        self.api_key = os.environ.get(cfg["llm"]["api_key_env"])
        if not self.api_key:
            raise RuntimeError("LLM API key not set in env")
        self.endpoint = cfg["llm"].get("endpoint")
        self.model = cfg["llm"].get("model")
        self.timeout = cfg["llm"].get("timeout_sec", 60)

    @retry(tries=3, delay=2)
    def chat(self, system, user, temperature=0):
        payload = {
            "model": self.model,
            "messages":[
                {"role":"system","content":system},
                {"role":"user","content":user}
            ],
            "temperature": temperature
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type":"application/json"}
        r = requests.post(self.endpoint, json=payload, headers=headers, timeout=self.timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"LLM error {r.status_code}: {r.text[:2000]}")
        js = r.json()
        text = js["choices"][0]["message"]["content"]
        return text

    def extract_code_blocks(self, text):
        return FENCE_RE.findall(text)
