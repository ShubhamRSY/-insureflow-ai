import sys, itertools, importlib.util, random
sys.path.insert(0, sys.argv[1]); import scope as v7
spec = importlib.util.spec_from_file_location("v6", sys.argv[2]); v6 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v6)
pre = ["", "Mailing address: ", "Mailing address:\n", "Home address:\n", "Agent: ", "Carrier A: ", "Producer: Jane Roe, ", "ABC Insurance Agency\n",
       "Carrier A Loss Run Attached\n", "Our agent said ", "Prior address (3 yrs): ", "Owner's home: ", "Mailing address\t", "Landlord: Oak Holdings, ",
       "Billing: PO Box 9, ", "Note to agent: ", "MAILING ADDRESS: ", "Agent address:\n", "Former premises: ", "Insured\t"]
addr = ["2215 Leonard Rd, Bryan", "1906 Hwy 290 W, Brenham", "100 Spur 191, Kerrville", "100 US-59, Houston", "4400 FM 1960 Rd, Houston",
        "9 Oak Ave, Waco", "800 I-35 Frontage Rd, Waco", "12 State Highway 6, Bryan", "55 N. Elm Street Ste 2, Austin", "77 County Road 12, Hearne"]
mid = ["", ". ", " and ", ", ", "\n", "\t", ". Carrier A loss run attached. ", "\nWe also keep stock at "]
loose = []; n = 0
random.seed(1)
cases = [p1 + a1 + m + p2 + a2 for p1 in pre for a1 in addr for m in mid for p2 in pre for a2 in addr if a1 != a2]
for t in random.sample(cases, 60000) + [p + a for p in pre for a in addr]:
    d = [{"name": "e.md", "text": t}]
    n += 1
    if v6._place_words(d) and not v7._place_words(d):
        loose.append(t)
print(n, "cases; v6 fires, v7 not:", len(loose))
for t in loose[:15]: print(repr(t))
print("--- singles (v6, v7)")
for a in addr:
    for p in ("", "Insured\t", "We are at "):
        d=[{"name":"e.md","text":p+a}]; print(repr(p+a), v6._place_words(d), v7._place_words(d))
self6 = {a for a in addr if v6._place_words([{"name":"e.md","text":a}])}
rest = [t for t in loose if not any(a in t for a in self6)]
print("loose not explained by v6 self-double-count:", len(rest))
for t in rest[:20]: print(repr(t))
