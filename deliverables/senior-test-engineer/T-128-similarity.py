"""T-128 similarity gate (T-128 build check H2): every hold-out email body vs every earlier email body in simulation/inbox and
simulation/inbox-dev (difflib ratio, digits masked); gate < 0.80. Also: no sentence of a hold-out email appears in the scope.py or
prepare.py source (self-checks) or in any inbox-dev file. Read-only. Run: python T-128-similarity.py 550 581"""
import difflib, re, sys
from pathlib import Path
lo, hi = int(sys.argv[1]), int(sys.argv[2])
ids = {f"SUB-{n}" for n in range(lo, hi + 1)}
def body(p):
    t = p.read_text(errors="ignore")
    t = t.split("\n", 3)[-1] if t.startswith("**FICTIONAL") else t
    return re.sub(r"\d", "0", re.sub(r"^Subject:.*$", "", t, flags=re.M)).strip().lower()
mine = {p.parent.name: body(p) for p in Path("simulation/inbox").glob("SUB-*/email.md") if p.parent.name in ids}
older = {str(p): body(p) for d in ("simulation/inbox", "simulation/inbox-dev") for p in Path(d).rglob("email*.md") if p.parent.name not in ids}
src = (Path("underwriting_pipeline/ai/scope.py").read_text() + Path("underwriting_pipeline/ai/prepare.py").read_text()).lower()
dev = " ".join(p.read_text(errors="ignore").lower() for p in Path("simulation/inbox-dev").rglob("*.md"))
worst, over, reused = [], 0, []
for k, b in sorted(mine.items()):
    sm = difflib.SequenceMatcher(None, b, autojunk=False)
    best = (0.0, "")
    for path, o in older.items():
        sm.set_seq2(o)
        if sm.real_quick_ratio() > best[0] and sm.quick_ratio() > best[0]:
            r = sm.ratio()
            if r > best[0]: best = (r, path)
    over += best[0] >= 0.80
    worst.append((round(best[0], 3), k, best[1]))
    orig = Path(f"simulation/inbox/{k}/email.md").read_text().lower()
    for s in re.split(r"(?<=[.!?])\s+|\n", orig):
        s = s.strip()
        if len(s) >= 20 and not s.startswith("**fictional") and s != "mailing address: same as premises" and (s in src or s in dev):  # banner; 573 shape label (plan)
            reused.append((k, s))
worst.sort(reverse=True)
print(f"emails >= 0.80: {over} of {len(mine)}; mean best match {sum(w[0] for w in worst) / len(worst):.3f}")
for w in worst[:6]: print("  ", w)
print("sentences found in scope.py/prepare.py/inbox-dev:", reused or "none")
sys.exit(1 if over or reused else 0)
