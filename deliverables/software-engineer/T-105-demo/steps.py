APP=lambda uw,**k:("act","/decision",{"underwriter_id":uw,"action":"approve","reason":"demo review of the file","_hash":True,"_acks":True,**k})
Q=lambda sub,c,prem,ded,terms:("quote",f"QUOTE\nCarrier: {c}\nSubmission: {sub}\nFICTIONAL planning figures. Not a bind.\n\nPremium: {prem}\nDeductible: {ded}\nTerms: {terms}\nSubjectivities: none beyond the file as sent.\n",f"carrier-{c.lower()}")
run("SUB-133",[("route",),("act","/send",{"user_line":"send to carrier SUB-133"}),
 ("act","/confirm-market",{"underwriter_id":"UW-001","carrier":"carrier_c","reason":"habitational, 12 units; Carrier C habitational appetite","_hash":True}),
 ("act","/send",{"user_line":"send to carrier SUB-133"}),
 APP("UW-002"),("am",),("act","/send",{"user_line":"send to carrier SUB-133"}),Q("SUB-133","C",11800,2500,"habitational 12 units, per file.")])
run("SUB-129",[("route",),("act","/decision",{"underwriter_id":"UW-002","action":"approve","reason":"x","_hash":True}),("act","/send",{"user_line":"send to carrier SUB-129"}),("act","/approve-draft",{"reason":"x"})])
run("SUB-127",[("route",),("act","/confirm-market",{"underwriter_id":"UW-002","carrier":"carrier_a","reason":"non-senior try","_hash":True}),
 ("act","/confirm-market",{"underwriter_id":"UW-001","carrier":"carrier_a","reason":"financial advisory is an office occupancy; Carrier A office appetite","_hash":True}),
 ("act","/send",{"user_line":"send to carrier SUB-127"}),APP("UW-002"),("am",),("act","/send",{"user_line":"send to carrier SUB-127"}),Q("SUB-127","A",5100,1000,"office, masonry non-combustible, TIV 1150000, valued loss runs through 2026-09-30.")])
run("SUB-131",[("route",),("act","/decision",{"underwriter_id":"UW-002","action":"resolve","conflict_field":"square_footage","chosen_value":"2100","reason":"signed application says 2,100","_hash":True}),("route",),
 APP("UW-002"),("act","/confirm-market",{"underwriter_id":"UW-001","carrier":"carrier_b","reason":"contractor; Carrier B","_hash":True}),("act","/send",{"user_line":"send to carrier SUB-131"}),Q("SUB-131","B",7300,2500,"plumbing service per file.")])
