from pydantic import BaseModel


class PresetBase(BaseModel):
    name: str
    description: str = ""
    groups: list[str]


class PresetCreate(PresetBase):
    pass


class PresetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    groups: list[str] | None = None


class PresetSchema(PresetBase):
    id: str
    is_default: bool

    model_config = {"from_attributes": True}
