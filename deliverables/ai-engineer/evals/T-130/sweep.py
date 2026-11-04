import sys, importlib.util, json
from pathlib import Path
root = Path(sys.argv[1]); sys.path.insert(0, str(root / "underwriting_pipeline/ai"))
import sources, scope as v7
spec = importlib.util.spec_from_file_location("scope_v6", sys.argv[2]); v6 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v6)
folders = [p for d in ("simulation/inbox", "simulation/inbox-dev", "deliverables/ai-engineer/evals/T-129/devcheck-inbox") for p in sorted((root / d).iterdir()) if p.is_dir()]
loosened, stricter, same = [], [], 0
for f in folders:
    docs = sources.read_folder(f)
    a, b = v6.detect(docs), v7.detect(docs)
    if a["in_scope"] == b["in_scope"]:
        same += 1
    elif b["in_scope"]:
        loosened.append(f.name)
    else:
        stricter.append((f.name, [r["text"] for r in b["reasons"]]))
dev = [(f.name, v7.detect(sources.read_folder(f))["in_scope"]) for f in folders if f.parent.name == "devcheck-inbox"]
print(json.dumps({"folders": len(folders), "same": same, "newly_in_scope": loosened, "newly_manual_intake": stricter, "dev12_v7_in_scope": dev}, indent=1))
