import sys, re, json, html
from pathlib import Path
R=Path("/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team")
sys.path[:0]=[str(R/"underwriting_pipeline/ai"),str(R/"underwriting_pipeline/models"),str(R/"underwriting_pipeline/app")]
import llm_extract, prepare, package, quotes, workbench as w
T=Path(sys.argv[1]); BOX=T/"box"; BOX.mkdir(exist_ok=True)
# point every source at the temp copies BEFORE sandbox() copies them (D-069)
for d in ("pend","tp","tc","fc"): (T/d).mkdir(exist_ok=True)
prepare.EXTRACT_DIR=T/"out"/"extractions"; w.INBOX=T/"inbox"; prepare.INBOX_DIR=T/"inbox"; package.INBOX=T/"inbox"
w.PENDING=T/"out"/"pending"; w.TO_PRODUCER=T/"tp"; w.TO_CARRIER=T/"tc"; quotes.FROM_CARRIER=T/"fc"; quotes.TO_CARRIER=T/"tc"
package.DECISIONS_LOG=T/"decisions.jsonl"; package.SENDS_LOG=T/"sends.jsonl"; quotes.CLOSURES=T/"closures.jsonl"
w.LOG=package.DECISIONS_LOG
w.sandbox(BOX)
assert str(w.PAGE).startswith(str(BOX)) and str(w.TO_CARRIER).startswith(str(BOX)) and str(prepare.EXTRACT_DIR).startswith(str(BOX))
def text(sub):
    page=w.render(w.load_queue(sub), w.correction_counts(w.LOG), {})
    page=re.sub(r"<(script|style).*?</\1>","",page,flags=re.S); page=re.sub(r"<[^>]+>","\n",page); page=html.unescape(page)
    return "\n".join(l.strip() for l in page.splitlines() if l.strip())
def show(label,res): print(f"  [{label}] ok={res[1]} :: {res[2]}")
def hash_(sub): return prepare.read_saved_run(sub)["saved_hash"]
def acks(sub): return package.needs_review_ids(w.package.with_resolutions(prepare.read_saved_run(sub), sub))
def run(sub, steps):
    print("=====",sub)
    for s in steps:
        kind=s[0]
        if kind=="route":
            rep,_=w.saved_report(sub); rep=package.with_resolutions(rep,sub); m=w.match(rep); print("  route:",rep["status"],m["route"],m["note"][:140])
        elif kind=="act": 
            path,payload=s[1],dict(s[2]); payload["submission"]=sub
            if payload.pop("_hash",False): payload["run_hash"]=hash_(sub)
            if payload.pop("_acks",False): payload["ack"]=acks(sub)
            show(path,w.act(path,payload))
        elif kind=="quote":
            body=s[1]; (T/"box"/"from-carrier"/f"{sub}-{s[2]}.md").write_text(body)
            print("  quote tracking:", [ (r["carrier"],r["status"],r["premium"],r["deductible"],r["sent_date"],r["bound"]) for r in quotes.track() if r["submission"]==sub])
        elif kind=="am":
            try: package.send_to_carrier(sub,"account-manager",w.TO_CARRIER,reason="file complete, in appetite")
            except ValueError as e: print("  [account-manager send] refused ::",e)
            else: print("  [account-manager send] sent")
        elif kind=="text":
            t=text(sub); i=t.find(sub); print("  --- card text ---"); print(t[i:i+int(s[1])] if i>=0 else t[:int(s[1])])
