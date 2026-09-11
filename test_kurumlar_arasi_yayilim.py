import os, sys, json, tempfile, shutil
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0, r"C:\Users\gokay\Desktop\aSc\ChenKi_v2")
import version_store as VS
SAND=os.path.join(tempfile.gettempdir(),"prop2"); shutil.rmtree(SAND,ignore_errors=True); os.makedirs(SAND)
VS._base_dir=lambda: SAND; VS._ensure_base=lambda: SAND
DAYS=["Pzt","Sal","Car","Per","Cum"]; P=8
def toff(kapali=()): return [[0 if d in kapali else 2 for _ in range(P)] for d in range(5)]
def kur(slug,primary,data):
    d=os.path.join(SAND,slug,"versions"); os.makedirs(d,exist_ok=True)
    json.dump({"name":slug,"is_primary":primary,"active_version":"v1.roz"},open(os.path.join(SAND,slug,"meta.json"),"w",encoding="utf-8"))
    json.dump(data,open(os.path.join(d,"v1.roz"),"w",encoding="utf-8"),ensure_ascii=False)
ana={"settings":{"periods":P,"days":DAYS},"ogretmenler":[{"ad":"Ahmet","timeoff":toff()}],
     "grid_placements":[{"teacher_name":"Ahmet","day":0,"period":0,"duration":2}],"atamalar":[]}
onceki=toff(kapali=(2,))
ik={"settings":{"periods":P,"days":DAYS},"ogretmenler":[{"ad":"Ahmet","timeoff":[list(r) for r in onceki]}],
    "atamalar":[{"teacher":"Ahmet","duration":30}],"grid_placements":[]}
kur("bogazici_egitim_kurumlari",True,ana); kur("birey_egitim_kurumlari",False,ik)
VS.propagate_primary_timeoff_to_secondary("bogazici_egitim_kurumlari",ana)
son=json.load(open(os.path.join(SAND,"birey_egitim_kurumlari","versions","v1.roz"),encoding="utf-8"))
m=son["ogretmenler"][0]["timeoff"]
print("IKINCIL KURUM - yayilimdan sonra:")
for d,g in enumerate(DAYS): print("   %-5s %s"%(g,"".join("K" if v==0 else "A" for v in m[d])))
print()
print(">>> HIC DEGISMEDI MI:", "EVET" if m==onceki else "HAYIR  <-- HATA")
assert m==onceki, "yayilim hala tabloyu degistiriyor"
print(">>> Carsamba kapali:", all(v==0 for v in m[2]))
print(">>> Pazartesi dokunulmadi (ana kurumda derste olsa bile):", m[0][0]==2)
print()
print("TEST GECTI - kurumlar tamamen bagimsiz")
