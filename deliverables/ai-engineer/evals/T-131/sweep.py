import sys, importlib.util, json
from pathlib import Path
root = Path(sys.argv[1]); sys.path.insert(0, str(root / "underwriting_pipeline/ai"))
import sources, scope as new
spec = importlib.util.spec_from_file_location("scope_v7", sys.argv[2]); old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
folders = [p for d in ("simulation/inbox", "simulation/inbox-dev", "deliverables/ai-engineer/evals/T-129/devcheck-inbox") for p in sorted((root / d).iterdir()) if p.is_dir() and not p.name.startswith((".", "__"))]
loosened, stricter, same = [], [], 0
for f in folders:
    docs = sources.read_folder(f)
    a, b = old.detect(docs), new.detect(docs)
    if a["in_scope"] == b["in_scope"]:
        same += 1
    elif b["in_scope"]:
        loosened.append(f.name)
    else:
        stricter.append((f.name, [r["text"] for r in b["reasons"]]))
dev = [(f.name, new.detect(sources.read_folder(f))["in_scope"]) for f in folders if f.parent.name == "devcheck-inbox"]
print(json.dumps({"folders": len(folders), "same": same, "newly_in_scope": loosened, "newly_manual_intake": stricter, "dev12_new_in_scope": dev}, indent=1))
