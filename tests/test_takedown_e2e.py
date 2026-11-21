import csv,io
from app.pipeline import calculate,execute
from app import store
from app.archive import build_archive
HEADER=["event_id","doc_id","version","op","source_time","visible_time","side","payload","reported","note"]
def ev(event,doc,ver,op,side,payload,visible="-"):
    return [event,doc,str(ver),op,"2026-11-16T10:00:00Z",visible,side,payload,"1","x"]
def make(events):
    buf=io.StringIO();w=csv.writer(buf);w.writerow(HEADER)
    for e in events:w.writerow(e)
    return buf.getvalue().encode()
def mismatch_csv():
    # 两端各有 v3 upsert 且正文不同，再各自 v5 撤下：墓碑同版本，但撤下前正文不一致
    return make([ev("1","0001",3,"upsert","source",'{"v":"源正文A"}'),
        ev("2","0001",3,"upsert","index",'{"v":"索引正文B"}',"2026-11-16T10:00:10Z"),
        ev("3","0001",5,"delete","source","{}"),
        ev("4","0001",5,"delete","index","{}","2026-11-16T10:00:20Z")])
def proven_csv():
    return make([ev("1","0001",3,"upsert","source",'{"v":"同一份正文"}'),
        ev("2","0001",3,"upsert","index",'{"v":"同一份正文"}',"2026-11-16T10:00:10Z"),
        ev("3","0001",5,"delete","source","{}"),
        ev("4","0001",5,"delete","index","{}","2026-11-16T10:00:20Z")])
def no_prior_csv():
    return make([ev("1","0002",5,"delete","source","{}"),
        ev("2","0002",5,"delete","index","{}","2026-11-16T10:00:20Z")])
def find(rows,doc):return next(r for r in rows if r["doc_id"]==doc)
def test_body_mismatch_takedown_not_signed_off():
    r=calculate(mismatch_csv());m4=find(r["stages"][3]["rows"],"0001");m5=find(r["stages"][4]["rows"],"0001")
    assert m4["takedown_state"]=="撤下正文不一致" and m4["takedown_id"]
    assert m5["gate"]=="撤下正文不一致" and m5["reported"]=="0"
    assert r["stages"][3]["metrics"]["takedown_body_mismatch"]==1
    assert r["stages"][6]["metrics"]["takedown_blocked"]==1
def test_matching_prior_body_signed_off():
    r=calculate(proven_csv());m4=find(r["stages"][3]["rows"],"0001");m5=find(r["stages"][4]["rows"],"0001")
    assert m4["takedown_state"]=="撤下完成" and m5["gate"]=="通过" and m5["reported"]=="1"
def test_unreconstructable_body_cannot_claim_complete():
    r=calculate(no_prior_csv());m4=find(r["stages"][3]["rows"],"0002");m5=find(r["stages"][4]["rows"],"0002")
    assert m4["takedown_state"]=="撤下待证" and m4["proof"] is None
    assert m5["gate"]=="撤下待证" and m5["reported"]=="0"
def test_rerun_keeps_conclusion_and_adds_no_record():
    raw=mismatch_csv()
    first=execute(raw);second=execute(raw)
    assert first["run_id"]==second["run_id"] and len(store.history())==1
    a=find(first["stages"][3]["rows"],"0001");b=find(second["stages"][3]["rows"],"0001")
    assert a["takedown_id"]==b["takedown_id"] and a["takedown_state"]==b["takedown_state"]
def test_archive_shares_page_conclusion_id():
    r=execute(mismatch_csv())
    page_id=find(r["stages"][3]["rows"],"0001")["takedown_id"]
    exported=list(csv.reader(io.StringIO(build_archive(r).encode().decode("utf-8-sig"))))
    assert exported[0][6]=="takedown_id" and exported[0][7]=="takedown_state"
    hit=[x for x in exported[1:] if x[6]==page_id]
    assert len(hit)==1 and hit[0][7]=="撤下正文不一致"
def test_each_doc_has_one_conclusion_id():
    r=execute(mismatch_csv())
    ids=[x["takedown_id"] for x in r["stages"][3]["rows"] if x["takedown_id"]]
    assert len(ids)==len(set(ids))==1
def test_http_archive_and_visibility_page_share_conclusion(client):
    p=client.post("/api/runs",json={"csv":mismatch_csv().decode()}).get_json()
    rid=p["run_id"]
    page=client.get("/visibility")
    assert page.status_code==200 and "撤下结论".encode() in page.data
    export=list(csv.reader(io.StringIO(client.get(f"/api/runs/{rid}/archive").data.decode("utf-8-sig"))))
    page_id=next(x["takedown_id"] for x in p["stages"][3]["rows"] if x["takedown_id"])
    assert any(x[6]==page_id and x[7]=="撤下正文不一致" for x in export[1:])
    # 重跑同输入不新增批次
    client.post("/api/runs",json={"csv":mismatch_csv().decode()})
    assert len(client.get("/api/runs").get_json()["runs"])==1
