import sys
exec(open(sys.argv[1]+"/flow_head.py").read())
S=T/"shots"; S.mkdir(exist_ok=True); LOGS=[]
SUBS=["SUB-127","SUB-129","SUB-133"]
def shot(sub, n, step, msg=None, queue=None, pre="T-105"):
    q = queue or w.load_queue(sub)
    page = w.render(q, w.correction_counts(w.LOG), {sub:msg} if msg else {})
    name=f"{pre}-{sub}-{n:02d}-{step}"
    (S/f"{name}.html").write_text(page); LOGS.append(name)
def act(sub,path,payload):
    p=dict(payload); p["submission"]=sub
    if p.pop("_hash",False): p["run_hash"]=hash_(sub)
    if p.pop("_acks",False): p["ack"]=acks(sub)
    r=w.act(path,p); print(sub,path,r[1],r[2]); return (r[1],r[2])
def am(sub):
    # the account-manager send IS the send (D-017); no typed override needed now (T-107e)
    try: package.send_to_carrier(sub,"account-manager",w.TO_CARRIER,reason="file complete, in appetite")
    except ValueError as e: print(sub,"AM refused:",e); return (False,"Account-manager check refused: "+str(e))
    print(sub,"AM sent"); return (True,f"Account-manager check passed, sent: package {sub}.md written to to-carrier. Not bound.")
def quote(sub,c,prem,ded,terms):
    (T/"box"/"from-carrier"/f"{sub}-carrier-{c.lower()}.md").write_text(f"QUOTE\nCarrier: {c}\nSubmission: {sub}\nFICTIONAL planning figures. Not a bind.\n\nPremium: {prem}\nDeductible: {ded}\nTerms: {terms}\nSubjectivities: none beyond the file as sent.\n")
    print(sub,[ (r["carrier"],r["status"],r["premium"],r["deductible"],r["bound"]) for r in quotes.track() if r["submission"]==sub])
APPR=lambda uw:{"underwriter_id":uw,"action":"approve","reason":"demo review of the file","_hash":True,"_acks":True}
# T-107e best case: SUB-184, inbox -> complete -> Carrier A -> account-manager check -> send
sub="SUB-184"; P="T-107e"
shot(sub,0,"queue",queue=w.load_queue(sub),pre=P)
shot(sub,1,"card-carrier-a",pre=P)
shot(sub,2,"approve",act(sub,"/decision",APPR("UW-002")),pre=P)
shot(sub,3,"account-manager-send",am(sub),pre=P)
quote(sub,"A",3900,1000,"office, TIV 260000, per file."); shot(sub,4,"quote",pre=P)
shot("SUB-127",0,"queue-all-three",queue=[x for s in SUBS for x in w.load_queue(s)])
# SUB-127 senior referral
sub="SUB-127"
shot(sub,1,"card")
shot(sub,2,"send-refused-before-approve",act(sub,"/send",{"user_line":"send to carrier SUB-127"}))
shot(sub,3,"nonsenior-confirm-refused",act(sub,"/confirm-market",{"underwriter_id":"UW-002","carrier":"carrier_a","reason":"non-senior try","_hash":True}))
shot(sub,4,"senior-confirm",act(sub,"/confirm-market",{"underwriter_id":"UW-001","carrier":"carrier_a","reason":"financial advisory is an office occupancy; Carrier A office appetite","_hash":True}))
shot(sub,5,"approve",act(sub,"/decision",APPR("UW-002")))
shot(sub,6,"send-sent",am(sub))
quote(sub,"A",5100,1000,"office, masonry non-combustible, TIV 1150000, valued loss runs through 2026-09-30.")
shot(sub,7,"quote")
# SUB-129 manual intake
sub="SUB-129"
shot(sub,1,"card")
shot(sub,2,"approve-refused",act(sub,"/decision",{"underwriter_id":"UW-002","action":"approve","reason":"x","_hash":True}))
shot(sub,3,"send-refused",act(sub,"/send",{"user_line":"send to carrier SUB-129"}))
shot(sub,4,"draft-approve-refused",act(sub,"/approve-draft",{"reason":"x"}))
# SUB-133 messy
sub="SUB-133"
shot(sub,1,"card")
shot(sub,2,"send-refused-before-approve",act(sub,"/send",{"user_line":"send to carrier SUB-133"}))
shot(sub,3,"senior-confirm",act(sub,"/confirm-market",{"underwriter_id":"UW-001","carrier":"carrier_c","reason":"habitational, 12 units; Carrier C habitational appetite","_hash":True}))
shot(sub,4,"send-refused-not-approved",act(sub,"/send",{"user_line":"send to carrier SUB-133"}))
shot(sub,5,"approve-scan-value-ticked",act(sub,"/decision",APPR("UW-002")))
shot(sub,6,"send-sent",am(sub))
quote(sub,"C",11800,2500,"habitational 12 units, per file.")
shot(sub,7,"quote")
print("PAGE_EXISTS_IN_BOX", w.PAGE.exists(), str(w.PAGE))
