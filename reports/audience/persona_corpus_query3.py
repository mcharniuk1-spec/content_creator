import sqlite3, json, glob, re, os, collections, statistics as st
R="/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar"
con=sqlite3.connect(os.path.join(R,"data/radar.db")); con.row_factory=sqlite3.Row
T={}
for f in sorted(glob.glob(os.path.join(R,"data/analysis/transcripts/*.json"))):
    d=json.load(open(f)); T[d["code"]]=d
VF={r["code"]:dict(r) for r in con.execute("select * from video_features")}
CAP={r["code"]:dict(r) for r in con.execute("select code,cap,play,resh,save from reels group by code")}
def w15(s):
    s=re.sub(r"\s+"," ",s).strip(); ws=s.split()
    return " ".join(ws[:15])+("…" if len(ws)>15 else "")

# --- direct 2nd-person audience address sentences ---
ADDR=re.compile(r"\b(if you(?:'re| are| run| own| have| do| want| work|r)\b[^.!?]{0,110}|for (?:anyone|anybody|everyone|those|people|business owners|founders|agencies|beginners)[^.!?]{0,90}|you'?re a [^.!?]{0,70})", re.I)
hits=collections.Counter(); ex=collections.defaultdict(list)
n_reels_with=0
for c,d in T.items():
    txt=" ".join([b.get("text","") for b in d.get("beats",[])])
    found=ADDR.findall(txt)
    if found: n_reels_with+=1
    for f in found:
        ex["all"].append((c,w15(f)))
print("=== Q1b DIRECT ADDRESS ('if you…', 'for anyone…', \"you're a…\") ===")
print("reels containing at least one direct-address phrase:", n_reels_with, "of", len(T))
print("total phrases:", len(ex["all"]))
# categorise the address target
CATS=[("founder/owner/business", r"business|founder|company|agency|clients?|startup|store|brand|team"),
      ("beginner/non-technical", r"beginner|new to|non-?tech|can'?t code|don'?t know how|never"),
      ("developer/builder", r"developer|coding|code|engineer|build(ing)? (an? )?(app|agent|saas)"),
      ("creator/marketer", r"creator|content|post(ing)?|marketer|marketing|audience|reels?|video")]
cc=collections.Counter()
for c,q in ex["all"]:
    m=[n for n,rx in CATS if re.search(rx,q,re.I)]
    cc[m[0] if m else "other/unlabelled"]+=1
for k,v in cc.most_common(): print(f"  {k:26s} {v}")
print("\nsample verbatim (code | phrase):")
seen=set()
for c,q in ex["all"]:
    key=q.lower()[:40]
    if key in seen: continue
    seen.add(key)
    if len(q.split())>=5: print("  ",c,"|",q)
    if len(seen)>45: break

# --- I-27 replication: non-technical / no-code audience mentions ---
print("\n=== Q5 CONTRADICTION CHECKS ===")
aud={c:(T[c].get("semantics",{}).get("audience","") or "").lower() for c in T}
nt=[c for c in T if re.search(r"non-?technical|no-?code|not technical|without cod|can'?t code|nontechnical", aud[c]+" "+(T[c].get("semantics",{}).get("audience_stage","") or "").lower())]
print("reels naming a NON-TECHNICAL / no-code audience:", len(nt), nt)
dev=[c for c in T if re.search(r"develop|engineer|coder|programmer|vibe coder|\bdevs?\b", aud[c])]
print("reels naming a DEVELOPER/coder audience:", len(dev))
own=[c for c in T if re.search(r"business owner|small business|\bsmb\b|local business|store owner|restaurant", aud[c])]
print("reels naming SMALL-BUSINESS OWNER audience:", len(own))

def med(codes, field):
    v=[VF[c][field] for c in codes if c in VF and VF[c].get(field) is not None and (VF[c]['play'] or 0)>=100]
    return round(st.median(v),5) if v else None
def blob(c):
    d=T[c]; s=d.get("semantics",{})
    return " ".join(x for x in [s.get("subtopic",""),s.get("subject",""),s.get("thesis",""),s.get("problem",""),s.get("solution",""),s.get("hook_text","")]+[b.get("text","") for b in d.get("beats",[])]+[CAP.get(c,{}).get("cap") or ""] if x).lower()
B={c:blob(c) for c in T}

# strict "what is AI / explainer" set: solution_type == framework_mental_model
fm=[c for c in T if T[c].get("semantics",{}).get("solution_type")=="framework_mental_model"]
rh=[c for c in T if T[c].get("semantics",{}).get("solution_type")=="resource_handoff"]
cmp_=[c for c in T if T[c].get("semantics",{}).get("solution_type")=="comparison"]
allc=list(T)
print(f"\nframework_mental_model ('here is how to think about it'): n={len(fm)} share={med(fm,'share_rate')} save={med(fm,'save_rate')} lift={med(fm,'view_lift')}")
print(f"resource_handoff  ('take this thing'):                     n={len(rh)} share={med(rh,'share_rate')} save={med(rh,'save_rate')} lift={med(rh,'view_lift')}")
print(f"comparison (tool A vs tool B):                             n={len(cmp_)} share={med(cmp_,'share_rate')} save={med(cmp_,'save_rate')} lift={med(cmp_,'view_lift')}")
print(f"ALL 274 baseline:                                          n={len(allc)} share={med(allc,'share_rate')} save={med(allc,'save_rate')} lift={med(allc,'view_lift')}")

# funnel_role / positioning
print("\nfunnel_role:")
for r in con.execute("select funnel_role,count(*) n from video_features where funnel_role is not null group by 1 order by n desc"):
    codes=[x[0] for x in con.execute("select code from video_features where funnel_role=?", (r[0],))]
    print(f"  {r[0]:16s} {r[1]:3d} share={med(codes,'share_rate')} save={med(codes,'save_rate')}")
print("\naudience_stage buckets:")
sb=collections.Counter()
for c in T:
    s=(T[c].get("semantics",{}).get("audience_stage","") or "").lower()
    if re.search(r"beginner|new|never|curious|unaware|has not|hasn't|no experience",s): sb["beginner/unaware"]+=1
    elif re.search(r"already (using|running|paying|build)|power user|advanced|experienced|daily",s): sb["already using AI"]+=1
    elif re.search(r"tried|experiment|dabbl|aware but|knows about|intermediate|some",s): sb["tried it, not systematic"]+=1
    else: sb["unclassified"]+=1
for k,v in sb.most_common(): print(f"  {k:26s} {v}")

# quotes for cost cluster
print("\n=== Q4 sample verbatim money lines ===")
mrx=re.compile(r"[^.!?]{0,80}(\$\s?\d[\d,\.]*|\d+ dollars|per month|a month|subscription|for free|100% free)[^.!?]{0,60}", re.I)
out=[];seen=set()
for c in T:
    for b in T[c].get("beats",[]):
        m=mrx.search(b.get("text",""))
        if m:
            q=w15(m.group(0))
            if q.lower()[:35] in seen: continue
            seen.add(q.lower()[:35]); out.append((c,q)); break
for c,q in out[:28]: print("  ",c,"|",q)

# --- topics table across full 3211 ---
print("\n=== full-corpus topic tags (topics table, all reels) ===")
for r in con.execute("select topic,count(distinct code) n from topics group by 1 order by n desc limit 25"): print(f"  {r[0]:44s} {r[1]}")
