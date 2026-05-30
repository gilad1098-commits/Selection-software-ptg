"""Inline HTML templates for the PTG procurement pilot."""

from datetime import datetime, date


def _nav() -> str:
    return """
    <nav>
        <a href="/">Dashboard</a>
        <a href="/new">New RFQ</a>
        <a href="/analyze">Analyze Email</a>
    </nav>
"""


def _base(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — PTG Procurement</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f5f6fa; color: #222; min-height: 100vh; }}
  nav {{ background: #1a2e4a; padding: 14px 32px; display: flex; gap: 24px; align-items: center; }}
  nav a {{ color: #cde; text-decoration: none; font-size: 15px; font-weight: 500; }}
  nav a:hover {{ color: #fff; }}
  nav::before {{ content: "PTG Procurement"; color: #fff; font-weight: 700;
                 font-size: 17px; margin-right: auto; }}
  .container {{ max-width: 1100px; margin: 32px auto; padding: 0 20px; }}
  h1 {{ font-size: 22px; margin-bottom: 20px; color: #1a2e4a; }}
  h2 {{ font-size: 18px; margin-bottom: 14px; color: #1a2e4a; }}
  .card {{ background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,.1);
           padding: 24px; margin-bottom: 20px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; padding: 10px 12px; font-size: 13px; color: #555;
        border-bottom: 2px solid #e8e8e8; white-space: nowrap; }}
  td {{ padding: 10px 12px; font-size: 14px; border-bottom: 1px solid #f0f0f0;
        vertical-align: middle; }}
  tr:hover td {{ background: #fafbff; }}
  .badge {{ display: inline-block; padding: 3px 9px; border-radius: 12px;
            font-size: 12px; font-weight: 600; white-space: nowrap; }}
  .badge-yellow {{ background: #fff3cd; color: #856404; }}
  .badge-blue {{ background: #cfe2ff; color: #084298; }}
  .badge-orange {{ background: #ffe5d0; color: #8b3a00; }}
  .badge-green {{ background: #d1e7dd; color: #0a3622; }}
  .badge-gray {{ background: #e2e3e5; color: #41464b; }}
  .badge-purple {{ background: #e0d4f7; color: #4a1f8c; }}
  .badge-teal {{ background: #d0f0ec; color: #0a4a42; }}
  .days-red {{ color: #c0392b; font-weight: 700; }}
  label {{ display: block; font-size: 13px; font-weight: 600; margin-bottom: 5px;
           color: #444; }}
  input[type=text], input[type=email], input[type=date], select, textarea {{
    width: 100%; padding: 9px 12px; border: 1px solid #d0d0d0; border-radius: 5px;
    font-size: 14px; background: #fff; }}
  input:focus, select:focus, textarea:focus {{ outline: none;
    border-color: #1a2e4a; box-shadow: 0 0 0 3px rgba(26,46,74,.1); }}
  .form-group {{ margin-bottom: 16px; }}
  .btn {{ display: inline-block; padding: 9px 20px; border: none; border-radius: 5px;
          font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; }}
  .btn-primary {{ background: #1a2e4a; color: #fff; }}
  .btn-primary:hover {{ background: #253f67; }}
  .btn-sm {{ padding: 5px 12px; font-size: 12px; }}
  .btn-outline {{ background: #fff; border: 1px solid #ccc; color: #333; }}
  .btn-outline:hover {{ background: #f0f0f0; }}
  .alert {{ padding: 12px 16px; border-radius: 6px; margin-bottom: 16px; font-size: 14px; }}
  .alert-success {{ background: #d1e7dd; color: #0a3622; }}
  .alert-info {{ background: #cfe2ff; color: #084298; }}
  .result-card {{ background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px;
                  padding: 20px; margin-top: 16px; }}
  .draft-box {{ background: #fff; border: 1px solid #c8d4e0; border-radius: 6px;
                padding: 16px; font-size: 14px; line-height: 1.7; white-space: pre-wrap;
                font-family: Georgia, serif; }}
  .copy-btn {{ margin-top: 10px; }}
  .tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px;
          background: #e8eaf0; color: #333; margin-right: 4px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  @media(max-width:700px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
  .empty-state {{ text-align: center; padding: 48px; color: #888; }}
  .notes-text {{ font-size: 12px; color: #666; max-width: 200px; white-space: pre-line; }}
  .modal-overlay {{ display:none; position:fixed; top:0; left:0; width:100%; height:100%;
                    background:rgba(0,0,0,.4); z-index:1000; align-items:center;
                    justify-content:center; }}
  .modal-overlay.open {{ display:flex; }}
  .modal {{ background:#fff; border-radius:8px; padding:24px; width:400px;
             max-width:90vw; box-shadow:0 8px 32px rgba(0,0,0,.2); }}
  .modal h3 {{ margin-bottom:14px; font-size:16px; color:#1a2e4a; }}
  .modal-close {{ float:right; cursor:pointer; font-size:20px; color:#888;
                  line-height:1; margin-top:-4px; }}
</style>
</head>
<body>
{_nav()}
<div class="container">
{body}
</div>
<script>
function openModal(id) {{
  document.getElementById(id).classList.add('open');
}}
function closeModal(id) {{
  document.getElementById(id).classList.remove('open');
}}
function copyDraft() {{
  const text = document.getElementById('draft-content').innerText;
  navigator.clipboard.writeText(text).then(() => {{
    const btn = document.getElementById('copy-btn');
    btn.textContent = 'Copied!';
    setTimeout(() => {{ btn.textContent = 'Copy to Clipboard'; }}, 2000);
  }});
}}
</script>
</body>
</html>"""


def _status_badge(status: str) -> str:
    badges = {
        "awaiting_reply": ("badge-yellow", "Awaiting Reply"),
        "supplier_replied": ("badge-blue", "Supplier Replied"),
        "engineer_review": ("badge-orange", "Engineer Review"),
        "approved": ("badge-green", "Approved"),
        "po_issued": ("badge-teal", "PO Issued"),
        "delivery_confirmed": ("badge-purple", "Delivery Confirmed"),
        "closed": ("badge-gray", "Closed"),
    }
    cls, label = badges.get(status, ("badge-gray", status))
    return f'<span class="badge {cls}">{label}</span>'


def _days_open(sent_at: str, status: str) -> str:
    try:
        sent = datetime.fromisoformat(sent_at).date()
        delta = (date.today() - sent).days
        if delta > 3 and status == "awaiting_reply":
            return f'<span class="days-red">{delta}d</span>'
        return f"{delta}d"
    except Exception:
        return "—"


STATUS_CHOICES = [
    "awaiting_reply",
    "supplier_replied",
    "engineer_review",
    "approved",
    "po_issued",
    "delivery_confirmed",
    "closed",
]


def dashboard_page(rfqs: list) -> str:
    if not rfqs:
        rows = '<tr><td colspan="8"><div class="empty-state">No open RFQs. <a href="/new">Create one</a> or <a href="/analyze">analyze an email</a>.</div></td></tr>'
    else:
        rows = ""
        for r in rfqs:
            rfq_id = r["rfq_id"]
            rid = r["id"]
            rows += f"""<tr>
  <td><strong>{rfq_id}</strong></td>
  <td>{r['supplier_name']}<br><small style="color:#888">{r['supplier_email']}</small></td>
  <td style="max-width:220px">{r['subject']}</td>
  <td>{_status_badge(r['status'])}</td>
  <td style="white-space:nowrap">{r['sent_at'][:10]}</td>
  <td style="white-space:nowrap">{_days_open(r['sent_at'], r['status'])}</td>
  <td style="text-align:center">{r['followup_count']}</td>
  <td style="white-space:nowrap">
    <button class="btn btn-sm btn-outline" onclick="openModal('note-modal-{rid}')">Note</button>
    <button class="btn btn-sm btn-outline" onclick="openModal('status-modal-{rid}')">Status</button>
  </td>
</tr>"""
            # Note modal
            rows += f"""
<div class="modal-overlay" id="note-modal-{rid}">
  <div class="modal">
    <span class="modal-close" onclick="closeModal('note-modal-{rid}')">&times;</span>
    <h3>Add Note — {rfq_id}</h3>
    <form method="post" action="/rfq/{rid}/note">
      <div class="form-group">
        <label>Note</label>
        <textarea name="note" rows="4" placeholder="Enter your note..."></textarea>
      </div>
      <button type="submit" class="btn btn-primary">Save Note</button>
    </form>
  </div>
</div>"""
            # Status modal
            options = "".join(
                f'<option value="{s}" {"selected" if s == r["status"] else ""}>{s.replace("_"," ").title()}</option>'
                for s in STATUS_CHOICES
            )
            rows += f"""
<div class="modal-overlay" id="status-modal-{rid}">
  <div class="modal">
    <span class="modal-close" onclick="closeModal('status-modal-{rid}')">&times;</span>
    <h3>Update Status — {rfq_id}</h3>
    <form method="post" action="/rfq/{rid}/update-status">
      <div class="form-group">
        <label>Status</label>
        <select name="status">{options}</select>
      </div>
      <button type="submit" class="btn btn-primary">Update</button>
    </form>
  </div>
</div>"""

    body = f"""
<h1>Open RFQs</h1>
<div class="card" style="padding:0; overflow:hidden;">
  <table>
    <thead>
      <tr>
        <th>RFQ ID</th><th>Supplier</th><th>Subject</th><th>Status</th>
        <th>Sent</th><th>Days Open</th><th>Follow-ups</th><th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</div>"""
    return _base("Dashboard", body)


def new_rfq_page(suggested_id: str = "", error: str = "") -> str:
    today = date.today().isoformat()
    error_html = f'<div class="alert alert-info">{error}</div>' if error else ""
    body = f"""
<h1>New RFQ</h1>
{error_html}
<div class="card">
  <form method="post" action="/new">
    <div class="grid-2">
      <div class="form-group">
        <label>RFQ ID</label>
        <input type="text" name="rfq_id" value="{suggested_id}" placeholder="RFQ-2026-001" required>
      </div>
      <div class="form-group">
        <label>Date Sent</label>
        <input type="date" name="sent_at" value="{today}" required>
      </div>
    </div>
    <div class="grid-2">
      <div class="form-group">
        <label>Supplier Name</label>
        <input type="text" name="supplier_name" placeholder="Acme Corp" required>
      </div>
      <div class="form-group">
        <label>Supplier Email</label>
        <input type="email" name="supplier_email" placeholder="contact@supplier.com" required>
      </div>
    </div>
    <div class="form-group">
      <label>Subject</label>
      <input type="text" name="subject" placeholder="RFQ for Widget Part #1234" required>
    </div>
    <button type="submit" class="btn btn-primary">Create RFQ</button>
  </form>
</div>"""
    return _base("New RFQ", body)


def analyze_page(
    rfqs: list,
    result: dict = None,
    draft: str = "",
    form_values: dict = None,
    error: str = "",
) -> str:
    fv = form_values or {}
    error_html = f'<div class="alert alert-info">{error}</div>' if error else ""

    rfq_options = '<option value="">— None / not linked —</option>' + "".join(
        f'<option value="{r["rfq_id"]}" {"selected" if fv.get("rfq_id") == r["rfq_id"] else ""}>'
        f'{r["rfq_id"]} — {r["supplier_name"]}</option>'
        for r in rfqs
    )

    result_html = ""
    if result:
        cls = result.get("classification", "")
        summary = result.get("summary", "")
        supplier = result.get("supplier_name") or "—"
        delivery = result.get("delivery_date") or "—"
        eng = "Yes" if result.get("requires_engineer") else "No"
        badge_map = {
            "supplier_quote_received": "badge-green",
            "supplier_question": "badge-orange",
            "supplier_delivery_confirmed": "badge-teal",
            "supplier_acknowledgment": "badge-blue",
            "other": "badge-gray",
        }
        badge_cls = badge_map.get(cls, "badge-gray")
        cls_label = cls.replace("_", " ").title()

        draft_html = ""
        if draft:
            escaped_draft = draft.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            draft_html = f"""
<h2 style="margin-top:20px">Draft Reply</h2>
<div class="draft-box" id="draft-content">{escaped_draft}</div>
<button class="btn btn-outline copy-btn" id="copy-btn" onclick="copyDraft()">Copy to Clipboard</button>
"""

        result_html = f"""
<div class="result-card">
  <h2>Classification Result</h2>
  <table style="width:auto">
    <tr><th style="padding:6px 16px 6px 0">Classification</th>
        <td><span class="badge {badge_cls}">{cls_label}</span></td></tr>
    <tr><th style="padding:6px 16px 6px 0">Supplier</th><td>{supplier}</td></tr>
    <tr><th style="padding:6px 16px 6px 0">Delivery Date</th><td>{delivery}</td></tr>
    <tr><th style="padding:6px 16px 6px 0">Needs Engineer</th><td>{eng}</td></tr>
    <tr><th style="padding:6px 16px 6px 0">Summary</th><td>{summary}</td></tr>
  </table>
  {draft_html}
</div>"""

    body = f"""
<h1>Analyze Email</h1>
{error_html}
<div class="card">
  <form method="post" action="/analyze">
    <div class="grid-2">
      <div class="form-group">
        <label>Supplier Name</label>
        <input type="text" name="supplier_name" value="{fv.get('supplier_name','')}" placeholder="Acme Corp">
      </div>
      <div class="form-group">
        <label>Supplier Email (sender)</label>
        <input type="email" name="supplier_email" value="{fv.get('supplier_email','')}" placeholder="contact@supplier.com">
      </div>
    </div>
    <div class="grid-2">
      <div class="form-group">
        <label>Subject</label>
        <input type="text" name="subject" value="{fv.get('subject','')}" placeholder="Re: RFQ-2026-001" required>
      </div>
      <div class="form-group">
        <label>Link to existing RFQ (optional)</label>
        <select name="rfq_id">{rfq_options}</select>
      </div>
    </div>
    <div class="form-group">
      <label>Email Body</label>
      <textarea name="body" rows="10" placeholder="Paste the full email body here..." required>{fv.get('body','')}</textarea>
    </div>
    <button type="submit" class="btn btn-primary">Analyze &amp; Draft Reply</button>
  </form>
</div>
{result_html}"""
    return _base("Analyze Email", body)
