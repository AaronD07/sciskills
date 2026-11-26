def audit_claims(draft, figures, version):
    return [{"id": claim["id"], "status": "keep", "figure": claim["figure"],
             "percent": claim["percent"], "text": claim["text"]}
            for claim in draft]
