"""Regional Supplier Database - Croatian, Slovenian, Serbian, Bosnian construction material suppliers.

Comprehensive list of approved supplier domains for web crawling and price search.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class RegionalSupplier:
    """Configuration for a regional construction material supplier."""
    
    # Domain information
    domain: str
    display_name: str
    country: Literal["HR", "SI", "RS", "BA", "ME", "MK"]  # Country code
    
    # Search configuration
    search_url_template: str | None = None  # URL template with {query} placeholder
    search_enabled: bool = True
    
    # Fetching configuration
    fetch_mode: Literal["static", "render"] = "static"
    allowed_paths: list[str] = field(default_factory=lambda: ["/"])
    
    # Pricing configuration
    currency: str = "EUR"
    vat_included: bool | None = True  # None = unknown
    vat_rate: float = 25.0  # Default Croatian rate
    locale: str = "hr"
    
    # Categories this supplier specializes in
    categories: list[str] = field(default_factory=list)
    
    # Notes about this supplier
    notes: str = ""


# ============================================================================
# CROATIAN SUPPLIERS (HR)
# ============================================================================

CROATIAN_SUPPLIERS: list[RegionalSupplier] = [
    # Major DIY chains
    RegionalSupplier(
        domain="bauhaus.hr",
        display_name="Bauhaus Hrvatska",
        country="HR",
        search_url_template="https://www.bauhaus.hr/trazilica?text={query}",
        categories=["building_materials", "tools", "garden", "paint", "flooring"],
        notes="Largest DIY chain in Croatia, comprehensive catalog",
    ),
    RegionalSupplier(
        domain="pevex.hr",
        display_name="Pevex",
        country="HR",
        search_url_template="https://www.pevex.hr/search?q={query}",
        categories=["building_materials", "tools", "garden", "plumbing", "electrical"],
        notes="Croatian DIY chain, competitive prices",
    ),
    RegionalSupplier(
        domain="mr.bricolage.hr",
        display_name="Mr. Bricolage",
        country="HR",
        search_url_template="https://www.mr-bricolage.hr/trazilica?q={query}",
        categories=["building_materials", "tools", "garden", "decor"],
        notes="French chain with Croatian presence",
    ),
    
    # Specialized construction suppliers
    RegionalSupplier(
        domain="gradja.hr",
        display_name="Gradja.hr",
        country="HR",
        search_url_template="https://www.gradja.hr/pretraga?q={query}",
        categories=["structural_materials", "insulation", "roofing"],
        notes="Online construction materials marketplace",
    ),
    RegionalSupplier(
        domain="wuerth.com.hr",
        display_name="Würth Hrvatska",
        country="HR",
        search_url_template="https://eshop.wuerth.com.hr/ProductSearch.aspx?search={query}",
        categories=["fasteners", "tools", "chemicals", "safety"],
        fetch_mode="render",  # Heavy JavaScript site
        notes="Professional fasteners and tools, requires JS rendering",
    ),
    RegionalSupplier(
        domain="era-commerce.hr",
        display_name="ERA Commerce",
        country="HR",
        search_url_template="https://www.era-commerce.hr/pretraga?q={query}",
        categories=["plumbing", "heating", "ventilation"],
        notes="HVAC and plumbing specialist",
    ),
    
    # Cement and concrete
    RegionalSupplier(
        domain="ducem.hr",
        display_name="Ducem",
        country="HR",
        search_url_template="https://www.ducem.hr/pretraga?q={query}",
        categories=["cement", "concrete", "mortar"],
        notes="Cement and concrete products manufacturer",
    ),
    RegionalSupplier(
        domain="beton.hr",
        display_name="Beton Lučko",
        country="HR",
        categories=["concrete", "prefabricated"],
        notes="Ready-mix concrete supplier",
    ),
    
    # Insulation specialists
    RegionalSupplier(
        domain="knaufinsulation.hr",
        display_name="Knauf Insulation",
        country="HR",
        search_url_template="https://www.knaufinsulation.hr/pretraga?q={query}",
        categories=["insulation", "thermal", "acoustic"],
        notes="Insulation materials specialist",
    ),
    RegionalSupplier(
        domain="rockwool.hr",
        display_name="ROCKWOOL",
        country="HR",
        search_url_template="https://www.rockwool.hr/pretraga?q={query}",
        categories=["insulation", "stone_wool", "fire_protection"],
        notes="Stone wool insulation products",
    ),
    
    # Flooring and tiles
    RegionalSupplier(
        domain="salonit.hr",
        display_name="Salonit",
        country="HR",
        categories=["flooring", "tiles", "facade"],
        notes="Fiber cement products and flooring",
    ),
    RegionalSupplier(
        domain="cerovo.com",
        display_name="Cerovo",
        country="HR",
        search_url_template="https://www.cerovo.com/pretraga?q={query}",
        categories=["tiles", "ceramics", "bathroom"],
        notes="Tiles and ceramics specialist",
    ),
    
    # Paint and coatings
    RegionalSupplier(
        domain="tikkurila.hr",
        display_name="Tikkurila",
        country="HR",
        search_url_template="https://www.tikkurila.hr/pretraga?q={query}",
        categories=["paint", "coatings", "protective"],
        notes="Premium paint manufacturer",
    ),
    RegionalSupplier(
        domain="dulux.hr",
        display_name="Dulux",
        country="HR",
        search_url_template="https://www.dulux.hr/pretraga?q={query}",
        categories=["paint", "decorative", "protective"],
        notes="Decorative paints and coatings",
    ),
    
    # Tools and equipment
    RegionalSupplier(
        domain="bosch-professional.com/hr",
        display_name="Bosch Professional",
        country="HR",
        search_url_template="https://www.bosch-professional.com/hr/hr/productsearch?search={query}",
        categories=["power_tools", "hand_tools", "accessories"],
        fetch_mode="render",
        notes="Professional power tools",
    ),
    RegionalSupplier(
        domain="makita.hr",
        display_name="Makita Hrvatska",
        country="HR",
        search_url_template="https://www.makita.hr/pretraga?q={query}",
        categories=["power_tools", "gardening", "accessories"],
        notes="Power tools and equipment",
    ),
    
    # Plumbing and heating
    RegionalSupplier(
        domain="vailant.hr",
        display_name="Vaillant",
        country="HR",
        search_url_template="https://www.vailant.hr/pretraga?q={query}",
        categories=["heating", "boilers", "heat_pumps"],
        notes="Heating systems specialist",
    ),
    RegionalSupplier(
        domain="geberit.hr",
        display_name="Geberit",
        country="HR",
        search_url_template="https://www.geberit.hr/pretraga?q={query}",
        categories=["plumbing", "bathroom", "pipework"],
        notes="Sanitary and plumbing systems",
    ),
    
    # Electrical
    RegionalSupplier(
        domain="schneider-electric.com/hr",
        display_name="Schneider Electric",
        country="HR",
        search_url_template="https://www.schneider-electric.com/hr/hr/search/?q={query}",
        categories=["electrical", "automation", "energy"],
        notes="Electrical distribution and automation",
    ),
    
    # Windows and doors
    RegionalSupplier(
        domain="velux.hr",
        display_name="VELUX",
        country="HR",
        search_url_template="https://www.velux.hr/pretraga?q={query}",
        categories=["roof_windows", "skylights", "blinds"],
        notes="Roof windows and skylights",
    ),
    RegionalSupplier(
        domain="drutex.hr",
        display_name="Drutex",
        country="HR",
        search_url_template="https://www.drutex.hr/pretraga?q={query}",
        categories=["windows", "doors", "facades"],
        notes="Windows and doors manufacturer",
    ),
    
    # Roofing
    RegionalSupplier(
        domain="crem.hr",
        display_name="Crem",
        country="HR",
        categories=["roofing", "tiles", "accessories"],
        notes="Roofing systems and tiles",
    ),
    RegionalSupplier(
        domain="bramac.hr",
        display_name="Bramac",
        country="HR",
        search_url_template="https://www.bramac.hr/pretraga?q={query}",
        categories=["roofing", "tiles", "solar"],
        notes="Concrete roof tiles",
    ),
]

# ============================================================================
# SLOVENIAN SUPPLIERS (SI)
# ============================================================================

SLOVENIAN_SUPPLIERS: list[RegionalSupplier] = [
    RegionalSupplier(
        domain="merkur.si",
        display_name="Merkur",
        country="SI",
        search_url_template="https://www.merkur.si/iskanje?q={query}",
        categories=["building_materials", "tools", "hardware"],
        currency="EUR",
        locale="sl",
        notes="Largest Slovenian hardware chain",
    ),
    RegionalSupplier(
        domain="obi.si",
        display_name="OBI Slovenija",
        country="SI",
        search_url_template="https://www.obi.si/suche?q={query}",
        categories=["building_materials", "garden", "decor"],
        currency="EUR",
        locale="sl",
        notes="German DIY chain in Slovenia",
    ),
    RegionalSupplier(
        domain="bauhaus.si",
        display_name="Bauhaus Slovenija",
        country="SI",
        search_url_template="https://www.bauhaus.si/suche?q={query}",
        categories=["building_materials", "tools", "garden"],
        currency="EUR",
        locale="sl",
        notes="Major DIY chain",
    ),
    RegionalSupplier(
        domain="jager.si",
        display_name="Jager",
        country="SI",
        search_url_template="https://www.jager.si/pretraga?q={query}",
        categories=["tools", "machinery", "workshop"],
        currency="EUR",
        locale="sl",
        notes="Professional tools and machinery",
    ),
    RegionalSupplier(
        domain="topdom.si",
        display_name="Topdom",
        country="SI",
        search_url_template="https://www.topdom.si/iskanje?q={query}",
        categories=["heating", "plumbing", "ventilation"],
        currency="EUR",
        locale="sl",
        notes="HVAC specialist",
    ),
    RegionalSupplier(
        domain="sanitarije.si",
        display_name="Sanitarije",
        country="SI",
        search_url_template="https://www.sanitarije.si/search?q={query}",
        categories=["bathroom", "sanitary", "tiles"],
        currency="EUR",
        locale="sl",
        notes="Bathroom and sanitary products",
    ),
]

# ============================================================================
# SERBIAN SUPPLIERS (RS)
# ============================================================================

SERBIAN_SUPPLIERS: list[RegionalSupplier] = [
    RegionalSupplier(
        domain="uradi-sam.rs",
        display_name="Uradi Sam",
        country="RS",
        search_url_template="https://www.uradi-sam.rs/pretraga?q={query}",
        categories=["building_materials", "tools", "garden"],
        currency="RSD",
        vat_rate=20.0,  # Serbian VAT
        locale="sr",
        notes="Major Serbian DIY chain",
    ),
    RegionalSupplier(
        domain="pekabeta.rs",
        display_name="Pekabeta",
        country="RS",
        search_url_template="https://www.pekabeta.rs/pretraga?q={query}",
        categories=["building_materials", "tools", "hardware"],
        currency="RSD",
        vat_rate=20.0,
        locale="sr",
        notes="Belgrade-based DIY chain",
    ),
    RegionalSupplier(
        domain="wuerth.rs",
        display_name="Würth Srbия",
        country="RS",
        search_url_template="https://eshop.wuerth.rs/ProductSearch.aspx?search={query}",
        categories=["fasteners", "tools", "chemicals"],
        currency="RSD",
        vat_rate=20.0,
        fetch_mode="render",
        locale="sr",
        notes="Professional fasteners",
    ),
    RegionalSupplier(
        domain="lafarge.rs",
        display_name="Lafarge Srbija",
        country="RS",
        categories=["cement", "concrete", "aggregates"],
        currency="RSD",
        vat_rate=20.0,
        locale="sr",
        notes="Cement and concrete manufacturer",
    ),
    RegionalSupplier(
        domain="knauf.rs",
        display_name="Knauf Srbija",
        country="RS",
        search_url_template="https://www.knauf.rs/pretraga?q={query}",
        categories=["drywall", "insulation", "ceilings"],
        currency="RSD",
        vat_rate=20.0,
        locale="sr",
        notes="Drywall and insulation systems",
    ),
]

# ============================================================================
# BOSNIAN SUPPLIERS (BA)
# ============================================================================

BOSNIAN_SUPPLIERS: list[RegionalSupplier] = [
    RegionalSupplier(
        domain="bingo.ba",
        display_name="Bingo",
        country="BA",
        search_url_template="https://www.bingo.ba/pretraga?q={query}",
        categories=["building_materials", "tools", "garden"],
        currency="BAM",
        vat_rate=17.0,  # Bosnian VAT
        locale="bs",
        notes="Major Bosnian retail chain with construction section",
    ),
    RegionalSupplier(
        domain="wuerth.ba",
        display_name="Würth Bosna",
        country="BA",
        search_url_template="https://eshop.wuerth.ba/ProductSearch.aspx?search={query}",
        categories=["fasteners", "tools", "chemicals"],
        currency="BAM",
        vat_rate=17.0,
        fetch_mode="render",
        locale="bs",
        notes="Professional tools and fasteners",
    ),
    RegionalSupplier(
        domain="celo.ba",
        display_name="Celo",
        country="BA",
        search_url_template="https://www.celo.ba/pretraga?q={query}",
        categories=["tiles", "ceramics", "bathroom"],
        currency="BAM",
        vat_rate=17.0,
        locale="bs",
        notes="Tiles and ceramics specialist",
    ),
]

# ============================================================================
# COMBINED REGIONAL DATABASE
# ============================================================================

ALL_SUPPLIERS: list[RegionalSupplier] = (
    CROATIAN_SUPPLIERS +
    SLOVENIAN_SUPPLIERS +
    SERBIAN_SUPPLIERS +
    BOSNIAN_SUPPLIERS
)


def get_supplier_by_domain(domain: str) -> RegionalSupplier | None:
    """Get supplier configuration by domain name."""
    for supplier in ALL_SUPPLIERS:
        if supplier.domain == domain or domain.endswith(supplier.domain):
            return supplier
    return None


def get_suppliers_by_country(country_code: str) -> list[RegionalSupplier]:
    """Get all suppliers for a specific country."""
    return [s for s in ALL_SUPPLIERS if s.country == country_code]


def get_suppliers_by_category(category: str) -> list[RegionalSupplier]:
    """Get all suppliers that carry a specific category."""
    return [s for s in ALL_SUPPLIERS if category in s.categories]


def get_search_url(supplier: RegionalSupplier, query: str) -> str | None:
    """Build search URL for a supplier."""
    if not supplier.search_url_template:
        return None
    
    from urllib.parse import quote
    encoded_query = quote(query, safe='')
    return supplier.search_url_template.format(query=encoded_query)


# ============================================================================
# CATEGORIES REFERENCE
# ============================================================================

CATEGORIES = {
    # Structural materials
    "cement": "Cement and cement products",
    "concrete": "Ready-mix and precast concrete",
    "structural_materials": "Structural building materials",
    "prefabricated": "Prefabricated elements",
    
    # Envelope
    "insulation": "Thermal and acoustic insulation",
    "thermal": "Thermal insulation materials",
    "acoustic": "Sound insulation materials",
    "roofing": "Roofing systems and materials",
    "tiles": "Roof and floor tiles",
    "facade": "Facade systems",
    
    # Interior
    "flooring": "Flooring materials",
    "drywall": "Drywall systems",
    "ceilings": "Ceiling systems",
    "paint": "Paints and coatings",
    "decorative": "Decorative finishes",
    "protective": "Protective coatings",
    
    # Systems
    "plumbing": "Plumbing systems and fixtures",
    "heating": "Heating systems",
    "ventilation": "Ventilation and HVAC",
    "electrical": "Electrical systems",
    "automation": "Building automation",
    
    # Products
    "windows": "Windows and glazing",
    "doors": "Doors and frames",
    "roof_windows": "Roof windows and skylights",
    "bathroom": "Bathroom fixtures and furniture",
    "sanitary": "Sanitary ware",
    "ceramics": "Ceramic products",
    
    # Tools
    "tools": "Hand and power tools",
    "power_tools": "Power tools",
    "fasteners": "Fasteners and fixings",
    "chemicals": "Construction chemicals",
    "safety": "Safety equipment",
    "machinery": "Construction machinery",
    "workshop": "Workshop equipment",
    
    # External
    "garden": "Garden and landscaping",
    "gardening": "Gardening tools and equipment",
    
    # General
    "building_materials": "General building materials",
    "hardware": "Hardware and ironmongery",
    "decor": "Home decor",
    "stone_wool": "Stone wool products",
    "fire_protection": "Fire protection materials",
    "aggregates": "Aggregates and sand",
    "mortar": "Mortar and plaster",
}
