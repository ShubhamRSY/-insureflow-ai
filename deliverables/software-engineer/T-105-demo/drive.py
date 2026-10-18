import sys, os, json
from pathlib import Path
R=Path("/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team")
sys.path[:0]=[str(R/"underwriting_pipeline/ai"),str(R/"underwriting_pipeline/models"),str(R/"underwriting_pipeline/app")]
import llm_extract, prepare
T=Path(sys.argv[1]); calls=[]
def blocked(*a,**k):
    calls.append(1); raise RuntimeError("BLOCKED: live call needed")
llm_extract._post=blocked
assert llm_extract.CACHE==T/"cache", llm_extract.CACHE
reps=prepare.write_drafts(T/"inbox", T/"out"/"pending", T/"out"/"conflicts")
for r in reps: print(r["folder"], r.get("status"), (r.get("error") or "")[:60])
print("blocked live-call attempts:", len(calls))
