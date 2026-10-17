from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from app.finance.models import Category, Subcategory
from app.identity.dependencies import CurrentUser, Db
from app.identity.workspaces import require_member

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["categories"])
DEFAULTS = (
    ("Casa", "#123A62", ("Aluguel", "Internet", "Energia")),
    ("Alimentação", "#E9650B", ("Mercado", "Restaurantes", "Café")),
    ("Transporte", "#29699A", ("Combustível", "Aplicativos", "Transporte público")),
    ("Lazer", "#B64D2C", ("Passeios", "Streaming", "Compras")),
)


class CategoryInput(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    color: str = Field(default="#647CAB", pattern=r"^#[0-9A-Fa-f]{6}$")

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = " ".join(value.split())
        if not value:
            raise ValueError("Informe o nome da categoria.")
        return value


class SubcategoryInput(BaseModel):
    name: str = Field(min_length=1, max_length=40)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = " ".join(value.split())
        if not value:
            raise ValueError("Informe o nome da subcategoria.")
        return value


def seed_categories(db, workspace_id):
    for name, color, names in DEFAULTS:
        category = Category(
            workspace_id=workspace_id, name=name, name_key=name.casefold(), color=color
        )
        db.add(category)
        db.flush()
        for sub in names:
            db.add(Subcategory(category_id=category.id, name=sub, name_key=sub.casefold()))


def category_or_404(db, workspace_id, category_id):
    category = db.get(Category, category_id)
    if category is None or category.workspace_id != workspace_id:
        raise HTTPException(404, "Categoria não encontrada.")
    return category


def subcategory_or_404(db, category_id, subcategory_id):
    sub = db.get(Subcategory, subcategory_id)
    if sub is None or sub.category_id != category_id:
        raise HTTPException(404, "Subcategoria não encontrada.")
    return sub


def serialize(db, category):
    subs = db.scalars(
        select(Subcategory)
        .where(Subcategory.category_id == category.id)
        .order_by(Subcategory.name, Subcategory.id)
    ).all()
    return {
        "id": category.id,
        "name": category.name,
        "color": category.color,
        "active": category.active,
        "subcategories": [{"id": sub.id, "name": sub.name, "active": sub.active} for sub in subs],
    }


@router.get("/categories")
def list_categories(workspace_id: UUID, db: Db, user: CurrentUser):
    require_member(db, workspace_id, user.id)
    rows = db.scalars(
        select(Category)
        .where(Category.workspace_id == workspace_id)
        .order_by(Category.name, Category.id)
    ).all()
    return [serialize(db, row) for row in rows]


@router.post("/categories", status_code=201)
def create_category(workspace_id: UUID, data: CategoryInput, db: Db, user: CurrentUser):
    require_member(db, workspace_id, user.id, lock=True)
    existing = db.scalar(
        select(Category).where(
            Category.workspace_id == workspace_id,
            Category.name_key == data.name.casefold(),
        )
    )
    if existing:
        if existing.active:
            raise HTTPException(409, "Esta categoria já existe.")
        existing.active = True
        existing.name = data.name
        existing.color = data.color
        category = existing
    else:
        category = Category(
            workspace_id=workspace_id,
            name=data.name,
            name_key=data.name.casefold(),
            color=data.color,
        )
        db.add(category)
    db.commit()
    return serialize(db, category)


@router.post("/categories/{category_id}/subcategories", status_code=201)
def create_subcategory(
    workspace_id: UUID, category_id: UUID, data: SubcategoryInput, db: Db, user: CurrentUser
):
    require_member(db, workspace_id, user.id, lock=True)
    category = category_or_404(db, workspace_id, category_id)
    if not category.active:
        raise HTTPException(409, "Ative a categoria antes de cadastrar subcategorias.")
    existing = db.scalar(
        select(Subcategory).where(
            Subcategory.category_id == category.id,
            Subcategory.name_key == data.name.casefold(),
        )
    )
    if existing:
        if existing.active:
            raise HTTPException(409, "Esta subcategoria já existe.")
        existing.active = True
        existing.name = data.name
        sub = existing
    else:
        sub = Subcategory(category_id=category.id, name=data.name, name_key=data.name.casefold())
        db.add(sub)
    db.commit()
    return {"id": sub.id, "name": sub.name, "active": sub.active}


@router.delete("/categories/{category_id}", status_code=204)
def deactivate_category(workspace_id: UUID, category_id: UUID, db: Db, user: CurrentUser):
    require_member(db, workspace_id, user.id, lock=True)
    category = category_or_404(db, workspace_id, category_id)
    category.active = False
    db.commit()


@router.delete("/categories/{category_id}/subcategories/{subcategory_id}", status_code=204)
def deactivate_subcategory(
    workspace_id: UUID, category_id: UUID, subcategory_id: UUID, db: Db, user: CurrentUser
):
    require_member(db, workspace_id, user.id, lock=True)
    category_or_404(db, workspace_id, category_id)
    sub = subcategory_or_404(db, category_id, subcategory_id)
    sub.active = False
    db.commit()
