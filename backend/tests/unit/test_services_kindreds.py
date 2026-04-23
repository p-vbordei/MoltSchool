import pytest

from kindred.crypto.keys import generate_keypair
from kindred.errors import ConflictError, ValidationError
from kindred.services.kindreds import create_kindred, get_kindred_by_slug
from kindred.services.users import register_user


async def test_create_kindred(db_session):
    _, pk = generate_keypair()
    u = await register_user(db_session, email="a@b.c", display_name="A", pubkey=pk)
    k = await create_kindred(
        db_session,
        owner_id=u.id,
        slug="heist-crew",
        display_name="Heist Crew",
        description="desc",
    )
    assert k.slug == "heist-crew"


async def test_create_kindred_duplicate_slug_raises(db_session):
    _, pk = generate_keypair()
    u = await register_user(db_session, email="a@b.c", display_name="A", pubkey=pk)
    await create_kindred(db_session, owner_id=u.id, slug="x", display_name="X")
    with pytest.raises(ConflictError):
        await create_kindred(db_session, owner_id=u.id, slug="x", display_name="Y")


async def test_slug_validation(db_session):
    _, pk = generate_keypair()
    u = await register_user(db_session, email="a@b.c", display_name="A", pubkey=pk)
    with pytest.raises(ValidationError):
        await create_kindred(
            db_session, owner_id=u.id, slug="Invalid Slug!", display_name="X"
        )


@pytest.mark.parametrize(
    "slug",
    [
        "kindred",
        "kindred-official",
        "official",
        "admin",
        "root",
        "anthropic",
        "sigstore",
        "kindred-totally-real",
        "anthropic-evil",
        "sigstore-fake",
        "official-scam",
    ],
)
async def test_reserved_slugs_rejected(db_session, slug):
    _, pk = generate_keypair()
    u = await register_user(db_session, email="r@b.c", display_name="R", pubkey=pk)
    with pytest.raises(ValidationError, match="reserved"):
        await create_kindred(
            db_session, owner_id=u.id, slug=slug, display_name="X"
        )


async def test_get_by_slug(db_session):
    _, pk = generate_keypair()
    u = await register_user(db_session, email="a@b.c", display_name="A", pubkey=pk)
    await create_kindred(db_session, owner_id=u.id, slug="x", display_name="X")
    k = await get_kindred_by_slug(db_session, "x")
    assert k.display_name == "X"
