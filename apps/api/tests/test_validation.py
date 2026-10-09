import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.identity.auth import NameInput
from app.main import create_app
from app.validation import validation_message


@pytest.mark.parametrize(
    "payload, expected",
    [
        (
            {"email": "nome@gmail,sa", "password": "senha-segura-123"},
            "Informe um e-mail válido. Exemplo: nome@exemplo.com.",
        ),
        (
            {"email": "nome@example.com", "password": "curta"},
            "A senha deve ter de 10 a 128 caracteres.",
        ),
        ({"password": "senha-segura-123"}, "Informe um e-mail válido. Exemplo: nome@exemplo.com."),
        (
            {"email": "nome@example.com", "password": None},
            "A senha deve ter de 10 a 128 caracteres.",
        ),
    ],
)
def test_public_validation_in_portuguese(payload, expected):
    settings = Settings(_env_file=None, database_url="postgresql://u:p@localhost:1/no_db")
    with TestClient(create_app(settings)) as client:
        response = client.post("/auth/login", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["message"] == expected
    assert "input" not in response.text
    assert "Value error" not in response.text


def test_name_validator_does_not_leak_english_prefix():
    with pytest.raises(ValidationError) as caught:
        NameInput(name="   ")
    error = caught.value.errors()[0]
    assert validation_message(error) == "Informe um nome de 1 a 80 caracteres."


def test_unknown_error_has_portuguese_fallback():
    assert validation_message(
        {"loc": ["body", "other"], "type": "new_type", "msg": "Internal English text"}
    ) == ("Confira os dados informados e tente novamente.")


def test_invalid_json_in_portuguese():
    settings = Settings(_env_file=None, database_url="postgresql://u:p@localhost:1/no_db")
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/auth/login", content="{", headers={"Content-Type": "application/json"}
        )
    assert response.status_code == 422
    assert response.json()["detail"][0]["message"] == (
        "Não foi possível ler os dados enviados. Tente novamente."
    )
