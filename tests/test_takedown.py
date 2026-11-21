from app import takedown
def side(ver,op,prior=None,prior_ver=None,lines=None):
    row={"version":str(ver),"op":op,"tombstone":op=="delete"}
    if prior is not None:row.update(prior_document=prior,prior_version=str(prior_ver or ver-1),prior_sources=lines or [1])
    else:row.update(prior_document=None,prior_version=None,prior_sources=[])
    return row
def delete(ver=5,prior=None,lines=None):return side(ver,"delete",prior,ver-1,lines)
def upsert(ver=4,doc=None):
    row=side(ver,"upsert");row["document"]=doc or {"a":1};return row
def test_matching_prior_body_is_proven():
    v=takedown.adjudicate("d1",delete(prior={"a":1}),delete(prior={"a":1}))
    assert v["takedown_state"]==takedown.PROVEN and v["takedown_id"].startswith("TD-")
def test_tombstone_without_prior_body_cannot_be_signed_off():
    "无法还原撤下前正文时不能冒充撤下完成"
    v=takedown.adjudicate("d1",delete(),delete())
    assert v["takedown_state"]==takedown.UNPROVEN and v["proof"] is None
def test_different_prior_bodies_are_mismatch_not_proven():
    "两端版本一致也无法证明撤下的是同一份正文"
    v=takedown.adjudicate("d1",delete(prior={"a":1}),delete(prior={"a":2}))
    assert v["takedown_state"]==takedown.BODY_MISMATCH and v["takedown_id"]
def test_one_sided_delete_is_unproven():
    v=takedown.adjudicate("d1",delete(prior={"a":1}),None)
    assert v["takedown_state"]==takedown.UNPROVEN
def test_upsert_only_is_not_a_takedown():
    v=takedown.adjudicate("d1",upsert(),upsert())
    assert v["takedown_state"]==takedown.NOT_A_TAKEDOWN and v["takedown_id"] is None
def test_conclusion_id_is_deterministic_and_unique_per_doc():
    a=takedown.adjudicate("d1",delete(prior={"a":1}),delete(prior={"a":1}))
    b=takedown.adjudicate("d1",delete(prior={"a":1}),delete(prior={"a":1}))
    c=takedown.adjudicate("d2",delete(prior={"a":1}),delete(prior={"a":1}))
    assert a["takedown_id"]==b["takedown_id"] and a["takedown_id"]!=c["takedown_id"]
