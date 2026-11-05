"""P-083 (D-164) condition (e): every case where v7 fires and v8 does not must name exactly one highway premises, written one way, and no other address."""
import sys, importlib.util, random
sys.path.insert(0, sys.argv[1]); import scope as v8
spec = importlib.util.spec_from_file_location("v7", sys.argv[2]); v7 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v7)
pre = ["", "Mailing address: ", "Mailing address:\n", "Home address:\n", "Agent: ", "Carrier A: ", "Producer: Jane Roe, ", "ABC Insurance Agency\n",
       "Carrier A Loss Run Attached\n", "Our agent said ", "Prior address (3 yrs): ", "Owner's home: ", "Mailing address\t", "Landlord: Oak Holdings, ",
       "Billing: ", "Note to agent: ", "MAILING ADDRESS: ", "Agent address:\n", "Former premises: ", "Insured\t", "We also keep stock at ", "Warehouse: "]
hwy = ["4400 FM 1960 Rd, Houston", "800 I-35 Frontage Rd, Waco", "12 State Highway 6, Bryan", "77 County Road 12, Hearne", "100 Spur 5 Rd, Kerrville",
       "1906 Hwy 290 W, Brenham", "100 Spur 191, Kerrville", "100 US-59, Houston", "4400 FM 1960 Road, Houston", "4401 FM 1960 Rd, Houston", "4400 FM 1961 Rd",
       # code review 2026-11-04 (P-083) shapes
       "4400 FM 1960 Rd W, Houston", "4400 FM 1960 Rd E, Humble", "77 County Road 12, Waco", "800 I-35 Service Rd, Temple", "100 US 59 Rd", "100 US 59 Business, Victoria",
       "4400 RM 620 Rd, Austin", "4400 RM 2222, Austin", "4400 FM 1960 Rd, Humble"]
other = ["2215 Leonard Rd, Bryan", "9 Oak Ave, Waco", "55 N. Elm Street Ste 2, Austin", "PO Box 9, Waco TX", "12 main st, Waco", "300 Bell St",
         "Post Office Box 9, Waco TX", "Box 9, Waco TX 76701", "RR 3 Box 12, Waco", "12A Main St, Waco", "One Main Street, Waco", "9 Oak, Waco"]
addr = hwy + other
mid = ["", ". ", " and ", ", ", "\n", "\t", ". Carrier A loss run attached. ", "\nWe also keep stock at ", " & "]
random.seed(7)
cases = [p1 + a1 + m + p2 + a2 for p1 in pre for a1 in addr for m in mid for p2 in pre for a2 in addr]
sample = random.sample(cases, 100000) + [p + a for p in pre for a in addr]
loose, bad, n = [], [], 0
for t in sample:
    for docs in ([{"name": "e.md", "text": t}], [{"name": "a.md", "text": "Premises address: " + t.split("\n")[0]}, {"name": "e.md", "text": t}]):
        n += 1
        if v7._place_words(docs) and not v8._place_words(docs):
            loose.append(docs)
            text = "\n".join(d["text"] for d in docs)
            present = [a for a in addr if a in text]
            mains = {a for a in present if not any(a != o and a in o for o in present)}  # an address inside a longer listed one is that one
            if len(mains) != 1 or not mains <= set(hwy):
                bad.append(docs)
print(n, "cases; v7 fires, v8 not:", len(loose), "; of those NOT exactly one highway premises:", len(bad))
for d in bad[:20]: print("BAD", repr([x["text"] for x in d]))
for d in loose[:10]: print("ok ", repr([x["text"] for x in d]))
