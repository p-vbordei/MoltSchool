from pydantic import BaseModel, Field


class CreateKindredReq(BaseModel):
    slug: str = Field(min_length=1, max_length=64)
    display_name: str
    description: str = ""
    bless_threshold: int = Field(ge=1, le=100, default=2)
    is_public: bool = False


class KindredOut(BaseModel):
    id: str
    slug: str
    display_name: str
    description: str
    bless_threshold: int
    is_public: bool

    @classmethod
    def from_model(cls, k) -> "KindredOut":
        return cls(
            id=str(k.id),
            slug=k.slug,
            display_name=k.display_name,
            description=k.description,
            bless_threshold=k.bless_threshold,
            is_public=k.is_public,
        )


class InstallOut(BaseModel):
    """Response for POST /v1/kindreds/{slug}/install."""

    invite_url: str
    expires_at: str
