import csv,io,json
def build_archive(run):
    stream=io.StringIO(newline="");writer=csv.writer(stream)
    writer.writerow(["run_id","input_sha256","rule_version","kind","source_lines","reason","takedown_id","takedown_state","evidence"])
    meta=run["manifest"]
    def line(kind,row,reason):
        writer.writerow([run["run_id"],meta["input_sha256"],meta["rule_version"],kind,json.dumps(row.get("_sources",[])),reason,row.get("takedown_id") or "",row.get("takedown_state") or "",json.dumps(row,ensure_ascii=False)])
    for row in run["stages"][-1]["rows"]:
        line("accepted",row,row.get("status",""))
    for row in run["stages"][-1].get("cumulative_quarantine",[]):
        line("quarantine",row,row.get("reason",""))
    return "﻿"+stream.getvalue()
