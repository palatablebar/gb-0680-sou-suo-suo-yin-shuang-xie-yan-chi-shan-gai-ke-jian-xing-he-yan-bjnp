from app.modules.m3_versions.rules import evaluate
def event(id,ver,op="upsert",document=None,side="index"):
    return {"event_id":str(id),"doc_id":"01","side":side,"version":str(ver),"op":op,
            "document":document if document is not None else (None if op=="delete" else {"a":1}),"_sources":[id]}
def test_tombstone_carries_last_visible_body():
    r=evaluate([event(1,4),event(2,5,"delete")],{})["rows"][0]
    assert r["tombstone"] is True and r["prior_document"]=={"a":1} and r["prior_version"]=="4" and r["prior_sources"]==[1]
def test_tombstone_without_upsert_has_no_reconstructable_body():
    r=evaluate([event(1,5,"delete")],{})["rows"][0]
    assert r["tombstone"] is True and r["prior_document"] is None and r["prior_sources"]==[]
def test_prior_body_uses_highest_version_below_tombstone():
    r=evaluate([event(1,3,document={"a":1}),event(2,4,document={"a":2}),event(3,5,"delete")],{})["rows"][0]
    assert r["prior_version"]=="4" and r["prior_document"]=={"a":2}
