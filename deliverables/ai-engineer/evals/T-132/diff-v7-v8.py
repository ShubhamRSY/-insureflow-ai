"""P-084 (D-165): stricter only. Over generated cases, v7 fires and v8 does not must be 0; also counts where v8 adds a hit."""
import sys, importlib.util, random
sys.path.insert(0, sys.argv[1]); import scope as v8
spec = importlib.util.spec_from_file_location("v7", sys.argv[2]); v7 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v7)
pre = ["", "Mailing address: ", "Mailing address:\n", "Home address:\n", "Agent: ", "Carrier A: ", "Producer: Jane Roe, ", "ABC Insurance Agency\n",
       "Carrier A Loss Run Attached\n", "Our agent said ", "Prior address (3 yrs): ", "Owner's home: ", "Mailing address\t", "Landlord: Oak Holdings, ",
       "Billing: PO Box 9, ", "Note to agent: ", "MAILING ADDRESS: ", "Agent address:\n", "Former premises: ", "Insured\t", "We also keep stock at "]
addr = ["2215 Leonard Rd, Bryan", "1906 Hwy 290 W, Brenham", "100 Spur 191, Kerrville", "100 US-59, Houston", "4400 FM 1960 Rd, Houston",
        "9 Oak Ave, Waco", "800 I-35 Frontage Rd, Waco", "12 State Highway 6, Bryan", "55 N. Elm Street Ste 2, Austin", "77 County Road 12, Hearne",
        "1200 ELM DR, WACO", "9 oak way, Waco", "12 IH 35, Waco", "4400 LOOP 1604 FRONTAGE RD, San Antonio", "Calle 5 de Mayo 120, Laredo", "1604 SL 1604, San Antonio", "12 TX-71, Bastrop", "PMB 123, Waco", "General Delivery, Waco",
        "Calle Roble 12, Laredo", "Av. Juarez 120, Laredo", "PO Box 9, Waco"]
mid = ["", ". ", " and ", ", ", "\n", "\t", ". Carrier A loss run attached. ", "\nWe also keep stock at ", " & "]
random.seed(11)
cases = [p1 + a1 + m + p2 + a2 for p1 in pre for a1 in addr for m in mid for p2 in pre for a2 in addr]
sample = random.sample(cases, 100000) + [p + a for p in pre for a in addr]
loose, added, n = [], 0, 0
for t in sample:
    for docs in ([{"name": "e.md", "text": t}], [{"name": "a.md", "text": "Premises address: " + t.split("\n")[0]}, {"name": "e.md", "text": t}]):
        n += 1
        a, b = v7._place_words(docs), v8._place_words(docs)
        if a and not b: loose.append(docs)
        if b and not a: added += 1
        if v7.detect(docs)["in_scope"] is False and v8.detect(docs)["in_scope"]: loose.append(docs)
print(n, "cases; v7 fires and v8 not (place words or detect):", len(loose), "; v8 adds a hit:", added)
for d in loose[:10]: print("LOOSE", repr([x["text"] for x in d]))
