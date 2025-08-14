import os, subprocess, time, json, logging, yaml
from functools import wraps

log = logging.getLogger("gwm.util")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def sh(cmd, check=True, capture=False, env=None):
    log.info("CMD: %s", cmd)
    res = subprocess.run(cmd, shell=True, check=False, capture_output=capture, env=env, text=True)
    if check and res.returncode!=0:
        log.error("Command failed: %s\nstdout:%s\nstderr:%s", cmd, res.stdout, res.stderr)
        raise RuntimeError(f"Command failed: {cmd}")
    return res

def retry(tries=3, delay=1, backoff=2):
    def deco(f):
        @wraps(f)
        def inner(*a, **kw):
            d = delay
            last = None
            for i in range(tries):
                try:
                    return f(*a, **kw)
                except Exception as e:
                    last = e
                    if i == tries-1:
                        raise
                    time.sleep(d)
                    d *= backoff
            raise last
        return inner
    return deco

def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)

def write_json(path, data):
    with open(path,"w") as f:
        json.dump(data, f, indent=2)
