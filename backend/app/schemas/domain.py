from pydantic import BaseModel


class DomainBase(BaseModel):
    domain: str
    display_name: str
    search_url_template: str | None = None
    fetch_mode: str = "static"
    vat_included: bool = True
    shipping_policy: str = "unknown"
    currency: str = "EUR"
    locale: str = "hr"
    enabled: bool = True


class DomainCreate(DomainBase):
    pass


class DomainUpdate(BaseModel):
    domain: str | None = None
    display_name: str | None = None
    search_url_template: str | None = None
    fetch_mode: str | None = None
    vat_included: bool | None = None
    shipping_policy: str | None = None
    currency: str | None = None
    locale: str | None = None
    enabled: bool | None = None


class DomainSchema(DomainBase):
    id: str
    is_default: bool

    model_config = {"from_attributes": True}
