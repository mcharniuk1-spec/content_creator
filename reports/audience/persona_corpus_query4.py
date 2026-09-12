import sqlite3, json, glob, re, os, statistics as st
R="/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar"
con=sqlite3.connect(os.path.join(R,"data/radar.db")); con.row_factory=sqlite3.Row
T={}
for f in sorted(glob.glob(os.path.join(R,"data/analysis/transcripts/*.json"))):
    d=json.load(open(f)); T[d["code"]]=d
VF={r["code"]:dict(r) for r in con.execute("select * from video_features")}
def w15(s):
    s=re.sub(r"\s+"," ",str(s)).strip(); ws=s.split()
    return " ".join(ws[:15])+("…" if len(ws)>15 else "")
def pf(c):
    v=VF.get(c,{}); return f"play={v.get('play')} share={round(v['share_rate'],4) if v.get('share_rate') else None} save={round(v['save_rate'],4) if v.get('save_rate') else None} lift={round(v['view_lift'],2) if v.get('view_lift') else None}"

print("=== pain_raw by pain enum: sample verbatim (top pains) ===")
for pain in ["cost_money","dont_know_where_to_start","manual_repetition","time_waste","scaling_without_hiring","chaos_no_process","fear_of_replacement","tool_overload"]:
    codes=[c for c in T if T[c].get("semantics",{}).get("pain")==pain]
    print(f"\n-- {pain} (n={len(codes)})")
    for c in codes[:5]:
        print("  ",c,"|",w15(T[c]["semantics"].get("pain_raw","")))

print("\n=== audience_tension samples for founder/owner reels ===")
own=[c for c in T if re.search(r"business owner|small business|\bsmb\b|founder|solopreneur|agency owner|local business",(T[c].get("semantics",{}).get("audience","") or ""),re.I)]
print("n =",len(own))
for c in own[:16]:
    print("  ",c,"|",w15(T[c].get("interpretation",{}).get("audience_tension","")))

print("\n=== hook_text: highest save_rate reels in the 274 ===")
rank=sorted([c for c in T if VF.get(c,{}).get('save_rate') is not None and (VF[c]['play'] or 0)>=100], key=lambda c:-VF[c]['save_rate'])[:12]
for c in rank: print("  ",c,"|",w15(T[c].get("semantics",{}).get("hook_text","")),"|",pf(c))
print("\n=== hook_text: highest share_rate reels ===")
rank=sorted([c for c in T if VF.get(c,{}).get('share_rate') is not None and (VF[c]['play'] or 0)>=100], key=lambda c:-VF[c]['share_rate'])[:12]
for c in rank: print("  ",c,"|",w15(T[c].get("semantics",{}).get("hook_text","")),"|",pf(c))

print("\n=== the 10 non-technical-audience reels ===")
for c in ['DV2e_4kCDxR','Dc0vBUOjyoQ','Dc4OPuWRwLQ','DcJuUdBT8Cf','Dc_CSwdDwvN','DcmK70aO5VP','DcoE5ZsK4I7','Dcwk9ebO1qY','DdCgx_ci6zj','DdCvFdHsnj1']:
    s=T[c]["semantics"]; print("  ",c,"|",w15(s.get("audience","")),"|",s.get("pain"),"|",pf(c))
nt=['DV2e_4kCDxR','Dc0vBUOjyoQ','Dc4OPuWRwLQ','DcJuUdBT8Cf','Dc_CSwdDwvN','DcmK70aO5VP','DcoE5ZsK4I7','Dcwk9ebO1qY','DdCgx_ci6zj','DdCvFdHsnj1']
def med(codes,f):
    v=[VF[c][f] for c in codes if VF.get(c,{}).get(f) is not None and (VF[c]['play'] or 0)>=100]
    return round(st.median(v),5) if v else None
print("  non-technical set: share=",med(nt,'share_rate'),"save=",med(nt,'save_rate'),"lift=",med(nt,'view_lift'))
