"""Realistic Croatian construction BoQ mock data for development."""

from .models import (
    BoQItemUI,
    ConfidenceBreakdownUI,
    HistoricMatchLineUI,
    HistoricMatchUI,
    MatchStatus,
    ParsedFileUI,
    PipelineStepStatus,
    PipelineStepUI,
    PriceStatsUI,
    PricedLineUI,
    ReasoningEntryUI,
)


def generate_mock_parsed_file() -> ParsedFileUI:
    return ParsedFileUI(
        filename="Kaufland Osijek (RETFALA).xlsx",
        sheet_name="Troskovnik",
        format_detected="kaufland",
        chapter_title="3. BETONSKI I ARMIRANO-BETONSKI RADOVI",
        total_rows=156,
        metadata={
            "investitor": "Kaufland Hrvatska k.d.",
            "lokacija": "Svilajska ul., 31000 Osijek",
            "datum": "2024-03",
        },
        items=[
            BoQItemUI(
                id="ch-3",
                item_number="3.",
                title="BETONSKI I ARMIRANO-BETONSKI RADOVI",
                level=0,
                match_status=MatchStatus.PENDING,
            ),
            BoQItemUI(
                id="sec-3.1",
                item_number="3.1.",
                title="Betonski radovi",
                level=1,
                parent_chapter="3.",
                match_status=MatchStatus.PENDING,
            ),
            BoQItemUI(
                id="unit-3.1.1",
                item_number="3.1.1.",
                title="Podložni beton",
                description=(
                    "Izrada podložnog betona ispod temeljnih traka i "
                    "temeljnih stopa. Beton klase C12/15, debljine 10 cm. "
                    "U cijenu uključen sav materijal, rad, transport i ugradnja."
                ),
                level=2,
                parent_chapter="3.",
                parent_section="3.1.",
                excel_start_row=45,
                excel_end_row=52,
                match_status=MatchStatus.MATCHED,
                priced_lines=[
                    PricedLineUI(
                        item_number="3.1.1.a.",
                        description="Podložni beton C12/15, d=10 cm",
                        unit="m\u00b3",
                        quantity=12.5,
                        unit_price=None,
                        excel_row=48,
                    ),
                    PricedLineUI(
                        item_number="3.1.1.b.",
                        description="Prijevoz betona do mjesta ugradnje",
                        unit="m\u00b3",
                        quantity=12.5,
                        unit_price=None,
                        excel_row=50,
                    ),
                ],
            ),
            BoQItemUI(
                id="unit-3.1.2",
                item_number="3.1.2.",
                title="Temeljne trake",
                description=(
                    "Betoniranje temeljnih traka betonom C25/30. "
                    "Armatura prema statičkom proračunu i planu armature. "
                    "U cijenu uključen kompletan materijal, montaža oplate, "
                    "demontaža oplate nakon sušenja, čišćenje i odvoz kao i "
                    "potrebno njegovanje betona."
                ),
                level=2,
                parent_chapter="3.",
                parent_section="3.1.",
                excel_start_row=53,
                excel_end_row=65,
                match_status=MatchStatus.PENDING,
                priced_lines=[
                    PricedLineUI(
                        item_number="3.1.2.a.",
                        description="Beton C25/30 za temeljne trake",
                        unit="m\u00b3",
                        quantity=28.0,
                        unit_price=None,
                        excel_row=56,
                    ),
                    PricedLineUI(
                        item_number="3.1.2.b.",
                        description="Armatura B500B, srednja složenost",
                        unit="kg",
                        quantity=2240.0,
                        unit_price=None,
                        excel_row=58,
                    ),
                    PricedLineUI(
                        item_number="3.1.2.c.",
                        description="Oplata temeljnih traka, glatka",
                        unit="m\u00b2",
                        quantity=84.0,
                        unit_price=None,
                        excel_row=60,
                    ),
                ],
            ),
            BoQItemUI(
                id="sec-3.2",
                item_number="3.2.",
                title="Armirano-betonski radovi",
                level=1,
                parent_chapter="3.",
                match_status=MatchStatus.PENDING,
            ),
            BoQItemUI(
                id="unit-3.2.1",
                item_number="3.2.1.",
                title="AB ploča prizemlja",
                description=(
                    "Betoniranje armirano-betonske ploče prizemlja. "
                    "Beton C30/37, debljina ploče 20 cm. "
                    "Armatura prema statičkom proračunu."
                ),
                level=2,
                parent_chapter="3.",
                parent_section="3.2.",
                excel_start_row=70,
                excel_end_row=82,
                match_status=MatchStatus.APPLIED,
                priced_lines=[
                    PricedLineUI(
                        item_number="3.2.1.a.",
                        description="Beton C30/37 za AB ploču",
                        unit="m\u00b3",
                        quantity=45.0,
                        unit_price=135.00,
                        total=6075.00,
                        applied_price=135.00,
                        excel_row=74,
                    ),
                    PricedLineUI(
                        item_number="3.2.1.b.",
                        description="Armatura B500B za ploču",
                        unit="kg",
                        quantity=5400.0,
                        unit_price=1.45,
                        total=7830.00,
                        applied_price=1.45,
                        excel_row=76,
                    ),
                ],
            ),
            BoQItemUI(
                id="unit-3.2.2",
                item_number="3.2.2.",
                title="AB stupovi",
                description=(
                    "Nabava materijala, dovoz, montaža glatke dašćane "
                    "oplate i betoniranje armirano betonskih stupova, "
                    "betonom C25/30. Stupove armirati prema statičkom "
                    "proračunu i planu armature."
                ),
                level=2,
                parent_chapter="3.",
                parent_section="3.2.",
                excel_start_row=83,
                excel_end_row=95,
                match_status=MatchStatus.PENDING,
                priced_lines=[
                    PricedLineUI(
                        item_number="3.2.2.a.",
                        description="Beton C25/30 za stupove",
                        unit="m\u00b3",
                        quantity=8.5,
                        unit_price=None,
                        excel_row=87,
                    ),
                ],
            ),
        ],
    )


def generate_mock_matches() -> list[HistoricMatchUI]:
    return [
        HistoricMatchUI(
            match_id="match-001",
            source_file="troskovnik korigirano 7.4.24.",
            project_name="Kaufland Osijek - korigirano",
            year="2024",
            match_confidence=0.87,
            confidence_breakdown=ConfidenceBreakdownUI(
                text_similarity=0.82,
                unit_match=1.0,
                hierarchy_match=0.78,
                description_overlap=0.88,
            ),
            qty_delta_pct=-25.0,
            matched_lines=[
                HistoricMatchLineUI(
                    item_number="3.1.2.a.",
                    description=(
                        "Nabava materijala, dovoz, montaža glatke dašćane "
                        "oplate i betoniranje vertikalnih serklaža, betonom C25/30"
                    ),
                    unit_of_measure="m\u00b3",
                    quantity=2.9,
                    unit_price=220.00,
                    total=638.00,
                ),
            ],
            avg_unit_price=220.00,
            total=638.00,
        ),
        HistoricMatchUI(
            match_id="match-002",
            source_file="Za kredit grad.obrt troskovnik popravljeno",
            project_name="Kredit grad.obrt - popravljeno",
            year="2024",
            match_confidence=0.74,
            confidence_breakdown=ConfidenceBreakdownUI(
                text_similarity=0.71,
                unit_match=1.0,
                hierarchy_match=0.55,
                description_overlap=0.70,
            ),
            qty_delta_pct=-28.0,
            matched_lines=[
                HistoricMatchLineUI(
                    item_number="10.a.",
                    description=(
                        "Nabava materijala, dovoz, montaža dvostrane glatke "
                        "dašćane oplate i betoniranje horizontalnih serklaža"
                    ),
                    unit_of_measure="m\u00b3",
                    quantity=2.4,
                    unit_price=190.00,
                    total=456.00,
                ),
            ],
            avg_unit_price=190.00,
            total=456.00,
        ),
        HistoricMatchUI(
            match_id="match-003",
            source_file="troskovnik IVICA SRŠEN",
            project_name="Ivica Sršen",
            year="2024",
            match_confidence=0.68,
            confidence_breakdown=ConfidenceBreakdownUI(
                text_similarity=0.65,
                unit_match=1.0,
                hierarchy_match=0.45,
                description_overlap=0.62,
            ),
            qty_delta_pct=8.0,
            matched_lines=[
                HistoricMatchLineUI(
                    item_number="9.a.",
                    description=(
                        "Nabava materijala, dovoz, montaža glatke dašćane "
                        "oplate i betoniranje armirano betonskih stupova"
                    ),
                    unit_of_measure="m\u00b3",
                    quantity=0.3,
                    unit_price=220.00,
                    total=66.00,
                ),
            ],
            avg_unit_price=220.00,
            total=66.00,
        ),
        HistoricMatchUI(
            match_id="match-004",
            source_file="Pehar Jelavić troskovnik",
            project_name="Pehar Jelavić",
            year="2023",
            match_confidence=0.62,
            confidence_breakdown=ConfidenceBreakdownUI(
                text_similarity=0.58,
                unit_match=1.0,
                hierarchy_match=0.42,
                description_overlap=0.48,
            ),
            qty_delta_pct=-13.0,
            matched_lines=[
                HistoricMatchLineUI(
                    item_number="5.a.",
                    description=(
                        "Nabava materijala, dovoz, montaža glatke dašćane "
                        "oplate i betoniranje armirano betonskih nadtemeljnih zidova"
                    ),
                    unit_of_measure="m\u00b3",
                    quantity=3.5,
                    unit_price=190.00,
                    total=665.00,
                ),
            ],
            avg_unit_price=190.00,
            total=665.00,
        ),
        HistoricMatchUI(
            match_id="match-005",
            source_file="Eurospin Savska Opatovina",
            project_name="Eurospin - Savska Opatovina",
            year="2024",
            match_confidence=0.55,
            confidence_breakdown=ConfidenceBreakdownUI(
                text_similarity=0.50,
                unit_match=1.0,
                hierarchy_match=0.38,
                description_overlap=0.32,
            ),
            qty_delta_pct=-40.0,
            matched_lines=[
                HistoricMatchLineUI(
                    item_number="3.2.1.a.",
                    description="Beton C25/30 za temelje",
                    unit_of_measure="m\u00b3",
                    quantity=18.0,
                    unit_price=180.00,
                    total=3240.00,
                ),
            ],
            avg_unit_price=180.00,
            total=3240.00,
        ),
    ]


def generate_mock_price_stats() -> PriceStatsUI:
    return PriceStatsUI(
        avg_price=201.61,
        min_price=165.00,
        max_price=240.00,
        num_matches=5,
        currency="EUR",
    )


def generate_mock_reasoning_log() -> list[ReasoningEntryUI]:
    return [
        ReasoningEntryUI(
            timestamp="17:32:01",
            agent_name="system",
            message="Pipeline started for unit 3.1.2. Temeljne trake",
            entry_type="info",
        ),
        ReasoningEntryUI(
            timestamp="17:32:02",
            agent_name="indexer",
            message="Scanning 30 historical projects...",
            entry_type="thinking",
        ),
        ReasoningEntryUI(
            timestamp="17:32:03",
            agent_name="indexer",
            message="Indexed 847 units across 30 projects",
            entry_type="result",
        ),
        ReasoningEntryUI(
            timestamp="17:32:04",
            agent_name="matcher",
            message='Searching for "Temeljne trake" + "beton C25/30"',
            entry_type="thinking",
        ),
        ReasoningEntryUI(
            timestamp="17:32:05",
            agent_name="matcher",
            message=(
                "Pronađeno 5 sličnih stavki u bazi historijskih podataka"
            ),
            entry_type="result",
        ),
        ReasoningEntryUI(
            timestamp="17:32:06",
            agent_name="matcher",
            message=(
                "Best match: troskovnik korigirano 7.4.24. (87% confidence)"
            ),
            entry_type="result",
        ),
        ReasoningEntryUI(
            timestamp="17:32:07",
            agent_name="pricer",
            message=(
                "Analyzing price distribution: avg=201.61, "
                "std=22.4, range=[165.00, 240.00]"
            ),
            entry_type="thinking",
        ),
        ReasoningEntryUI(
            timestamp="17:32:08",
            agent_name="pricer",
            message=(
                "Suggested price: 201.61 EUR/m\u00b3 "
                "(confidence: 0.82, based on 5 historic prices)"
            ),
            entry_type="result",
        ),
    ]


def generate_mock_pipeline() -> list[PipelineStepUI]:
    return [
        PipelineStepUI(name="Upload", status=PipelineStepStatus.DONE),
        PipelineStepUI(name="Parse", status=PipelineStepStatus.DONE),
        PipelineStepUI(
            name="Index",
            status=PipelineStepStatus.DONE,
            detail="847 units indexed",
        ),
        PipelineStepUI(
            name="Match",
            status=PipelineStepStatus.ACTIVE,
            detail="Processing unit 3/8...",
        ),
        PipelineStepUI(name="Suggest", status=PipelineStepStatus.PENDING),
        PipelineStepUI(name="Review", status=PipelineStepStatus.PENDING),
    ]
