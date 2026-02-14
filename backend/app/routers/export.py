from __future__ import annotations

import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.boq import BoQFile, BoQItem

router = APIRouter()


def _get_file_with_items(
    file_id: str, db: Session
) -> tuple[BoQFile, list[BoQItem]]:
    boq_file = db.query(BoQFile).filter(BoQFile.id == file_id).first()
    if not boq_file:
        raise HTTPException(status_code=404, detail="File not found")
    items = (
        db.query(BoQItem)
        .filter(BoQItem.file_id == file_id)
        .order_by(BoQItem.row)
        .all()
    )
    return boq_file, items


# ── XLSX Export ──────────────────────────────────────────────────────


@router.get("/export/{file_id}/xlsx")
async def export_xlsx(file_id: str, db: Session = Depends(get_db)):
    """Export a BOQ file as XLSX."""
    boq_file, items = _get_file_with_items(file_id, db)

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

    wb = Workbook()
    ws = wb.active
    ws.title = "BOQ Export"

    # Styles
    header_font = Font(name="Arial", bold=True, size=10, color="FFFFFF")
    header_fill = PatternFill(start_color="1a1a2e", end_color="1a1a2e", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin", color="2a2a40"),
        right=Side(style="thin", color="2a2a40"),
        top=Side(style="thin", color="2a2a40"),
        bottom=Side(style="thin", color="2a2a40"),
    )
    num_align = Alignment(horizontal="right", vertical="center")
    text_align = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # Title row
    ws.merge_cells("A1:F1")
    title_cell = ws["A1"]
    title_cell.value = f"BOQ Export - {boq_file.file_name}"
    title_cell.font = Font(name="Arial", bold=True, size=14)
    ws.merge_cells("A2:F2")
    ws["A2"].value = f"Project: {boq_file.project_name or 'N/A'} | Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ws["A2"].font = Font(name="Arial", size=9, italic=True, color="6b7280")

    # Header row
    headers = ["#", "Description", "Unit", "Qty", "Unit Price", "Total"]
    col_widths = [10, 50, 8, 12, 14, 14]
    for col_idx, (header, width) in enumerate(zip(headers, col_widths), start=1):
        cell = ws.cell(row=4, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws.column_dimensions[cell.column_letter].width = width

    # Data rows
    for row_idx, item in enumerate(items, start=5):
        row_data = [
            item.item_number or "",
            item.description or "",
            item.unit or "",
            item.quantity or 0,
            item.unit_price or 0,
            item.total or 0,
        ]
        for col_idx, value in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            if col_idx in (4, 5, 6):
                cell.alignment = num_align
                cell.number_format = "#,##0.00"
            else:
                cell.alignment = text_align

    # Summary row
    if items:
        summary_row = 5 + len(items) + 1
        ws.cell(row=summary_row, column=5, value="TOTAL:").font = Font(bold=True)
        total_cell = ws.cell(
            row=summary_row,
            column=6,
            value=sum(i.total or 0 for i in items),
        )
        total_cell.font = Font(bold=True)
        total_cell.number_format = "#,##0.00"
        total_cell.alignment = num_align

    # Write to buffer
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = boq_file.file_name.rsplit(".", 1)[0] + "_export.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── PDF Export ───────────────────────────────────────────────────────


@router.get("/export/{file_id}/pdf")
async def export_pdf(file_id: str, db: Session = Depends(get_db)):
    """Export a BOQ file as PDF."""
    boq_file, items = _get_file_with_items(file_id, db)

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(f"BOQ Export - {boq_file.file_name}", styles["Title"]))
    elements.append(
        Paragraph(
            f"Project: {boq_file.project_name or 'N/A'} | "
            f"Items: {len(items)} | "
            f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 10 * mm))

    # Table
    header = ["#", "Description", "Unit", "Qty", "Unit Price", "Total"]
    data = [header]
    for item in items:
        desc = (item.description or "")[:80]  # truncate for PDF
        data.append([
            item.item_number or "",
            desc,
            item.unit or "",
            f"{item.quantity:.2f}" if item.quantity else "",
            f"{item.unit_price:.2f}" if item.unit_price else "",
            f"{item.total:.2f}" if item.total else "",
        ])

    # Summary
    grand_total = sum(i.total or 0 for i in items)
    data.append(["", "", "", "", "TOTAL:", f"{grand_total:.2f}"])

    col_widths = [25 * mm, 70 * mm, 15 * mm, 20 * mm, 25 * mm, 25 * mm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle([
            # Header
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            # Body
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("ALIGN", (3, 1), (5, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            # Grid
            ("GRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#2a2a40")),
            # Alternating rows
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8f8fc")]),
            # Summary row
            ("FONTNAME", (4, -1), (5, -1), "Helvetica-Bold"),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#1a1a2e")),
            # Padding
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    elements.append(table)

    doc.build(elements)
    buf.seek(0)

    filename = boq_file.file_name.rsplit(".", 1)[0] + "_export.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
