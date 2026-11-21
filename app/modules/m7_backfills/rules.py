import hashlib,json
from decimal import Decimal
from app.errors import DomainError
from app.reasons import sources
from app import takedown
def evaluate(rows,context):
    stages=[v for v in context.values() if isinstance(v,dict) and "metrics" in v]
    balances=[s["metrics"]["balanced"] for s in stages if "balanced" in s["metrics"]]
    if balances and not all(balances): raise DomainError("UNBALANCED","来源行未对平，不能归档")
    ids=[str(r.get("doc_id",r.get("_line",""))) for r in rows]
    if len(ids)!=len(set(ids)): raise DomainError("ARCHIVE_DUPLICATE","归档业务键重复")
    # 每篇撤下文档只能有一个结论号；结论号重复即结论被复用，拒绝归档
    td=[r["takedown_id"] for r in rows if r.get("takedown_id")]
    if len(td)!=len(set(td)): raise DomainError("TAKEDOWN_DUPLICATE","撤下结论号不唯一")
    encoded=json.dumps(rows,ensure_ascii=False,sort_keys=True,default=str).encode()
    return {"rows":rows,"quarantine":[],"metrics":{"records":len(rows),"source_lines":len(set(x for row in rows for x in sources(row))),"sha256":hashlib.sha256(encoded).hexdigest(),"ready":True,"differences":sum(r.get("status")=="差异" for r in rows),"takedown_total":sum(r.get("takedown_state") in takedown.TAKEDOWN_STATES for r in rows),"takedown_proven":sum(r.get("takedown_state")==takedown.PROVEN for r in rows),"takedown_blocked":sum(r.get("takedown_state") in (takedown.UNPROVEN,takedown.BODY_MISMATCH) for r in rows)}}
