"""Apresentação do relatório em A4, com fontes incorporadas e quebra de páginas."""

from html import escape
from io import BytesIO
from pathlib import Path

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

INK = colors.HexColor("#23342F")
GREEN = colors.HexColor("#285B49")
MUTED = colors.HexColor("#687873")
LINE = colors.HexColor("#DEE5DF")
PALE = colors.HexColor("#F4F6F2")
RED = colors.HexColor("#A34131")


def fonts():
    folder = Path(reportlab.__file__).parent / "fonts"
    if "Vera" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Vera", str(folder / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("VeraBd", str(folder / "VeraBd.ttf")))
    pdfmetrics.registerFontFamily("Vera", normal="Vera", bold="VeraBd")


def money(cents):
    value = abs(cents)
    number = f"{value // 100:,}".replace(",", ".")
    return f"{'-' if cents < 0 else ''}R$ {number},{value % 100:02d}"


def styled():
    return {
        "title": ParagraphStyle("title", fontName="VeraBd", fontSize=21, leading=26,
                                textColor=INK, spaceAfter=5),
        "subtitle": ParagraphStyle("subtitle", fontName="Vera", fontSize=9, leading=14,
                                   textColor=MUTED),
        "section": ParagraphStyle("section", fontName="VeraBd", fontSize=12, leading=16,
                                  textColor=INK, spaceBefore=12, spaceAfter=6,
                                  keepWithNext=1),
        "body": ParagraphStyle("body", fontName="Vera", fontSize=8.5, leading=13,
                               textColor=INK),
        "small": ParagraphStyle("small", fontName="Vera", fontSize=7.5, leading=11,
                                textColor=MUTED),
        "strong": ParagraphStyle("strong", fontName="VeraBd", fontSize=8.5, leading=13,
                                 textColor=INK),
        "right": ParagraphStyle("right", fontName="VeraBd", fontSize=8.5, leading=13,
                                alignment=TA_RIGHT, textColor=INK),
        "metric": ParagraphStyle("metric", fontName="VeraBd", fontSize=15, leading=20,
                                 textColor=GREEN),
        "metric_red": ParagraphStyle("metric_red", fontName="VeraBd", fontSize=15, leading=20,
                                     textColor=RED),
    }


def paragraph(text, style):
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def date_label(day):
    return day.strftime("%d/%m/%Y")


def rows_table(headers, rows, widths, styles):
    cells = [[paragraph(item, styles["strong"]) for item in headers]]
    cells += [[paragraph(item, styles["right"] if column == len(headers) - 1
                         else styles["body"]) for column, item in enumerate(row)] for row in rows]
    table = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, LINE),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def section(story, label, styles):
    story.append(paragraph(label, styles["section"]))


def empty(story, message, styles):
    story.append(paragraph(message, styles["small"]))


def footer(canvas, document):
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(LINE)
    canvas.line(42, 39, width - 42, 39)
    canvas.setFont("Vera", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(42, 27, "financeiro.  |  Relatório pessoal")
    canvas.drawRightString(width - 42, 27, f"Página {document.page}")
    canvas.restoreState()


def render_monthly_pdf(data, detail=False):
    fonts()
    styles = styled()
    summary = data["summary"]
    month = summary["month"]
    historical = summary["kind"] == "historical"
    width = A4[0] - 84
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=42, rightMargin=42,
                            topMargin=40, bottomMargin=58,
                            title=f"Relatório financeiro - {month:%m/%Y}",
                            author="Financeiro")
    story = [
        paragraph("financeiro.", styles["title"]),
        paragraph(f"{data['workspace_name']}  |  {month:%m/%Y}  |  Gerado em "
                  f"{date_label(data['generated_at'])}", styles["subtitle"]),
        Spacer(1, 14),
        HRFlowable(width="100%", thickness=1, color=LINE),
    ]

    section(story, "Visão geral", styles)
    metric = [
        [paragraph("Renda considerada", styles["small"]),
         paragraph("Resultado do mês", styles["small"]),
         paragraph("Saldo no fim do mês" if historical else "Saldo final previsto",
                   styles["small"])],
        [paragraph(money(summary["income_cents"]), styles["metric"]),
         paragraph(money(summary["result_cents"]),
                   styles["metric_red"] if summary["result_cents"] < 0 else styles["metric"]),
         paragraph(money(summary["projected_balance_cents"]),
                   styles["metric_red"] if summary["projected_balance_cents"] < 0
                   else styles["metric"])],
    ]
    cards = Table(metric, colWidths=[width / 3] * 3, hAlign="LEFT")
    cards.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 11),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 11),
    ]))
    story.append(cards)
    story.append(Spacer(1, 7))
    story.append(paragraph(
        f"Recebido {money(summary['received_income_cents'])}  |  "
        f"Ainda previsto {money(summary['expected_income_cents'])}  |  "
        f"Compromissos {money(summary['committed_cents'])}", styles["small"]))
    percent = summary.get("commitment_percent")
    story.append(paragraph(
        "Renda comprometida: " + (f"{str(percent).replace('.', ',')}%" if percent is not None
                                 else "não se aplica sem renda"), styles["small"]))
    if historical:
        story.append(paragraph("Mês encerrado: valores realizados e saldo histórico.",
                               styles["small"]))
    else:
        story.append(paragraph(
            f"Saldo atual {money(summary['cash_balance_cents'])} + a receber até o mês "
            f"{money(summary['expected_through_month_cents'])} - fixas pendentes "
            f"{money(summary['fixed_through_month_cents'])} - faturas pendentes "
            f"{money(summary['card_through_month_cents'])} - pendências antigas "
            f"{money(summary['overdue_cents'])}.", styles["small"]))

    section(story, "Gastos por categoria", styles)
    if data["categories"]:
        rows = [(name, money(amount)) for name, amount in data["categories"]]
        story.append(rows_table(["Categoria", "Compras e despesas"], rows,
                                [width * .65, width * .35], styles))
        story.append(Spacer(1, 5))
        story.append(paragraph(
            "Categorias mostram consumo e fixas pendentes. Parcelas de fatura refinanciada "
            "são compromissos, não novas compras.", styles["small"]))
    else:
        empty(story, "Nenhuma compra ou despesa categorizada neste mês.", styles)

    section(story, "Receitas", styles)
    if data["incomes"]:
        rows = [(item["description"], money(item["expected_cents"]),
                 money(item["received_cents"])) for item in data["incomes"]]
        story.append(rows_table(["Previsão", "Previsto", "Recebido"], rows,
                                [width * .50, width * .25, width * .25], styles))
    else:
        empty(story, "Nenhuma renda recorrente cadastrada para este mês.", styles)
    linked = sum(item["received_cents"] for item in data["incomes"])
    extra = summary["received_income_cents"] - linked
    if extra:
        story.append(paragraph(f"Receitas avulsas recebidas: {money(extra)}.", styles["small"]))

    section(story, "Despesas fixas", styles)
    if data["fixed"]:
        rows = [(item["description"], item["status"], money(item["amount_cents"]))
                for item in data["fixed"]]
        story.append(rows_table(["Descrição", "Situação", "Valor"], rows,
                                [width * .55, width * .20, width * .25], styles))
    else:
        empty(story, "Nenhuma despesa fixa neste mês.", styles)

    section(story, "Faturas e financiamento", styles)
    if data["invoices"]:
        rows = [(item["name"], date_label(item["due_on"]),
                 money(item["total_cents"]), money(item["remaining_cents"]))
                for item in data["invoices"]]
        story.append(rows_table(["Cartão", "Vencimento", "Fatura", "Pendente"], rows,
                                [width * .31, width * .22, width * .23, width * .24], styles))
        for item in data["invoices"]:
            if item["advanced_cents"] or item["refinanced_cents"]:
                story.append(paragraph(
                    f"{item['name']}: antecipado {money(item['advanced_cents'])}; "
                    f"principal refinanciado {money(item['refinanced_cents'])}.", styles["small"]))
    elif not summary["card_commitment_cents"]:
        empty(story, "Nenhuma fatura neste mês.", styles)
    if data["financings"]:
        rows = [(f"{item['card_name']} - {item['sequence']}/{item['total_count']}",
                 money(item["principal_cents"]), money(item["fee_cents"]),
                 money(item["amount_cents"])) for item in data["financings"]]
        story.append(Spacer(1, 8))
        story.append(rows_table(["Parcela refinanciada", "Principal", "Encargos", "Total"],
                                rows, [width * .38, width * .21, width * .20, width * .21], styles))
    if summary["card_refinanced_cents"]:
        story.append(paragraph(
            f"Principal transferido deste mês para faturas futuras: "
            f"{money(summary['card_refinanced_cents'])}. As compras originais seguem no "
            "mês da fatura; esse principal não é contado duas vezes no resultado.",
            styles["small"]))
    if summary["card_commitment_cents"] and not data["invoices"]:
        story.append(paragraph(
            f"Assinaturas ainda não lançadas, previstas para a fatura: "
            f"{money(summary['card_commitment_cents'])}.", styles["small"]))

    section(story, "Contas", styles)
    if data["accounts"]:
        rows = [(item["name"], "Dinheiro" if item["kind"] == "cash" else "Banco",
                 money(item["balance_cents"])) for item in data["accounts"]]
        story.append(rows_table(["Conta", "Tipo", "Saldo histórico" if historical
                                 else "Saldo atual"], rows,
                                [width * .50, width * .22, width * .28], styles))
    else:
        empty(story, "Nenhuma conta cadastrada naquele período.", styles)

    if detail:
        section(story, "Lançamentos detalhados", styles)
        if data["details"]:
            rows = [(date_label(item["date"]), item["label"], item["category"],
                     money(item["amount_cents"])) for item in data["details"]]
            story.append(rows_table(["Data", "Descrição", "Categoria", "Valor"], rows,
                                    [width * .16, width * .42, width * .22, width * .20], styles))
        else:
            empty(story, "Nenhum lançamento detalhado neste mês.", styles)
    story.append(Spacer(1, 14))
    story.append(paragraph(
        "Resultado do mês e saldo previsto seguem regras distintas: pagamentos já feitos "
        "estão no saldo das contas e não são descontados novamente. Este relatório reflete "
        "os dados disponíveis no momento da geração.", styles["small"]))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
