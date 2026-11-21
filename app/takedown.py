import hashlib
import json

# 撤下结论：墓碑只证明存在删除事件，不能证明两端撤下的是同一份正文。
# 仅当两端撤下前最后一份可见正文都能还原且内容一致时，才允许签收为撤下完成。
PROVEN = "撤下完成"
BODY_MISMATCH = "撤下正文不一致"
UNPROVEN = "撤下待证"
NOT_A_TAKEDOWN = "非撤下"

TAKEDOWN_STATES = {PROVEN, BODY_MISMATCH, UNPROVEN}


def body_key(document):
    return json.dumps(document, sort_keys=True, ensure_ascii=False)


def conclusion_id(doc_id, source, index):
    """每篇文档唯一的撤下结论号，随输入确定性派生；重跑不新增、不变更。"""
    version = max(
        [str(side["version"]) for side in (source, index) if side is not None],
        key=lambda text: int(text) if text.isdigit() else text,
    )
    basis = json.dumps([doc_id, version, "takedown"], ensure_ascii=False)
    return "TD-" + hashlib.sha256(basis.encode()).hexdigest()[:16]


def adjudicate(doc_id, source, index):
    """按撤下前可见正文裁决单篇文档，返回结论号、结论与证据，不冒充完成。"""
    deleted_source = source is not None and source.get("tombstone") is True
    deleted_index = index is not None and index.get("tombstone") is True
    if not (deleted_source or deleted_index):
        return {"takedown_id": None, "takedown_state": NOT_A_TAKEDOWN, "takedown_reason": "", "proof": None}
    td_id = conclusion_id(doc_id, source, index)
    if not (deleted_source and deleted_index):
        return {"takedown_id": td_id, "takedown_state": UNPROVEN,
                "takedown_reason": "缺少一端墓碑，撤下未双端确认", "proof": None}
    prior_source = source.get("prior_document")
    prior_index = index.get("prior_document")
    if prior_source is None or prior_index is None:
        return {"takedown_id": td_id, "takedown_state": UNPROVEN,
                "takedown_reason": "撤下前正文无法还原，不能按墓碑冒充完成", "proof": None}
    if body_key(prior_source) != body_key(prior_index):
        return {"takedown_id": td_id, "takedown_state": BODY_MISMATCH,
                "takedown_reason": "两端撤下前可见正文不一致",
                "proof": {"source_prior_version": source.get("prior_version"),
                          "index_prior_version": index.get("prior_version"),
                          "source_lines": source.get("prior_sources", []),
                          "index_lines": index.get("prior_sources", [])}}
    return {"takedown_id": td_id, "takedown_state": PROVEN,
            "takedown_reason": "两端撤下前正文一致，撤下可签收",
            "proof": {"source_prior_version": source.get("prior_version"),
                      "index_prior_version": index.get("prior_version"),
                      "source_lines": source.get("prior_sources", []),
                      "index_lines": index.get("prior_sources", [])}}
