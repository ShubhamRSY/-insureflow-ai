import sys, os, json
from pathlib import Path
R=Path("/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team")
sys.path[:0]=[str(R/"underwriting_pipeline/ai"),str(R/"underwriting_pipeline/models"),str(R/"underwriting_pipeline/app")]
import llm_extract, prepare
T=Path(sys.argv[1]); calls=[]
def blocked(*a,**k):
    calls.append(1); raise RuntimeError("BLOCKED: live call needed")
llm_extract._post=blocked
# SUB-184/179 replies are on the old prompt (b025802c0dfa): re-key a copy inside the temp cache only
_ck=llm_extract.cache_key
def _rekey(docs, model):
    k=_ck(docs, model); new=llm_extract.CACHE/"extractions"/f"{k}.json"
    if not new.exists():
        cur=llm_extract.PROMPT_VERSION; llm_extract.PROMPT_VERSION="b025802c0dfa"
        try: old=llm_extract.CACHE/"extractions"/f"{_ck(docs, model)}.json"
        finally: llm_extract.PROMPT_VERSION=cur
        if old.exists(): new.write_bytes(old.read_bytes()); print("re-keyed old-prompt reply ->", k[:12])
    return k
llm_extract.cache_key=_rekey
assert llm_extract.CACHE==T/"cache", llm_extract.CACHE
reps=prepare.write_drafts(T/"inbox", T/"out"/"pending", T/"out"/"conflicts")
for r in reps: print(r["folder"], r.get("status"), (r.get("error") or "")[:60])
print("blocked live-call attempts:", len(calls))
