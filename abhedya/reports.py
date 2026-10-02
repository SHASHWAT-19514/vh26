from __future__ import annotations
from html import escape
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from .config import DATA_DIR

def render(content, kind='case-diary'):
    title='POLICE CASE DIARY' if kind=='case-diary' else 'BANK FREEZE REQUISITION'
    tx=list(content.get('transactions',{}).values()); accounts=list(content.get('accounts',{}).values())
    rows=''.join(f"<tr><td>{escape(str(e.get('ts','')))}</td><td>{escape(str(e.get('txn_id','')))}</td><td>{escape(str(e.get('from','')))}</td><td>{escape(str(e.get('to','')))}</td><td>{escape(str(e.get('amount','')))}</td></tr>" for e in tx)
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>body{{font-family:Arial;color:#14231f;margin:42px}}h1{{font-size:22px;border-bottom:2px solid #14231f;padding-bottom:12px}}.note{{background:#eef5e7;padding:12px}}table{{border-collapse:collapse;width:100%;font-size:10px}}td,th{{border:1px solid #ccd8d0;padding:6px;text-align:left}}</style></head><body><h1>{title}</h1><p><b>Investigation:</b> {escape(content['meta']['investigation_id'])}</p><p><b>Victim account:</b> {escape(str(content.get('victim')))}</p><p><b>Total traced amount (paise):</b> {escape(str(content.get('totals',{}).get('total_siphoned','0')))}</p><div class="note">System-generated analytical findings; not a legal conclusion. Statutory provisions and placeholders are to be confirmed by the Investigating Officer.</div><h2>Chronological money trail</h2><table><tr><th>Timestamp</th><th>Transaction</th><th>From</th><th>To</th><th>Amount (paise)</th></tr>{rows}</table><h2>Accounts in trace</h2><p>{len(accounts)} accounts identified across positional layers. No balance data is available; any residual is an estimate.</p><footer>Evidence SHA-256: {content['seal']['content_sha256']}</footer></body></html>'''

def save(content, kind='case-diary'):
    out = DATA_DIR / 'reports'
    out.mkdir(parents=True, exist_ok=True)
    eid = content['meta']['investigation_id']

    # Generate HTML
    html = render(content, kind)
    hp = out / f'{eid}-{kind}.html'
    hp.write_text(html, encoding='utf-8')

    # Generate proper PDF using reportlab
    pp = out / f'{eid}-{kind}.pdf'
    doc = SimpleDocTemplate(str(pp), pagesize=A4, topMargin=0.75*inch, bottomMargin=0.75*inch, leftMargin=0.75*inch, rightMargin=0.75*inch)

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#14231f'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#14231f'),
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        textColor=colors.HexColor('#14231f'),
        spaceAfter=6
    )
    note_style = ParagraphStyle(
        'CustomNote',
        parent=styles['BodyText'],
        fontSize=9,
        textColor=colors.HexColor('#14231f'),
        backColor=colors.HexColor('#eef5e7'),
        borderPadding=12,
        spaceAfter=12
    )

    # Build document
    story = []

    # Title
    title = 'POLICE CASE DIARY' if kind == 'case-diary' else 'BANK FREEZE REQUISITION'
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 0.2*inch))

    # Investigation details
    story.append(Paragraph(f"<b>Investigation ID:</b> {content['meta']['investigation_id']}", body_style))
    story.append(Paragraph(f"<b>Victim Account:</b> {content.get('victim', 'N/A')}", body_style))
    total_siphoned = content.get('totals', {}).get('total_siphoned', '0')
    story.append(Paragraph(f"<b>Total Traced Amount (paise):</b> {total_siphoned}", body_style))
    story.append(Spacer(1, 0.15*inch))

    # Disclaimer
    disclaimer = "System-generated analytical findings; not a legal conclusion. Statutory provisions and placeholders are to be confirmed by the Investigating Officer."
    story.append(Paragraph(disclaimer, note_style))
    story.append(Spacer(1, 0.2*inch))

    # Transaction table
    story.append(Paragraph("Chronological Money Trail", heading_style))

    tx = list(content.get('transactions', {}).values())
    if tx:
        # Prepare table data
        table_data = [['Timestamp', 'Transaction ID', 'From', 'To', 'Amount (₹)']]
        for e in tx[:100]:  # Limit to first 100 transactions to avoid huge PDFs
            table_data.append([
                str(e.get('ts', ''))[:19],  # Truncate timestamp
                str(e.get('txn_id', ''))[:20],  # Truncate long IDs
                str(e.get('from', ''))[:12],
                str(e.get('to', ''))[:12],
                f"₹{int(e.get('amount', 0)) / 100:.2f}"
            ])

        # Create table
        t = Table(table_data, colWidths=[1.2*inch, 1.5*inch, 1.0*inch, 1.0*inch, 0.9*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#14231f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ccd8d0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8faf9')])
        ]))
        story.append(t)

        if len(tx) > 100:
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph(f"<i>Note: Showing first 100 of {len(tx)} transactions. Full data available in evidence record.</i>", body_style))
    else:
        story.append(Paragraph("No transactions in trace.", body_style))

    story.append(Spacer(1, 0.2*inch))

    # Account summary
    story.append(Paragraph("Accounts in Trace", heading_style))
    accounts = list(content.get('accounts', {}).values())
    story.append(Paragraph(f"{len(accounts)} accounts identified across positional layers. No balance data is available; any residual is an estimate.", body_style))

    story.append(Spacer(1, 0.3*inch))

    # Footer
    footer_text = f"<b>Evidence Seal (SHA-256):</b> {content['seal']['content_sha256']}"
    story.append(Paragraph(footer_text, body_style))

    # Build PDF
    doc.build(story)

    return {'html': str(hp), 'pdf': str(pp), 'evidence_id': eid}
