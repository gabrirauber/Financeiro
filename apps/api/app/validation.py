"""Mensagens públicas de validação, sem expor texto interno ou valores enviados."""


def validation_message(error: dict) -> str:
    field = str(error.get("loc", [""])[-1])
    kind = error.get("type", "")
    if kind == "json_invalid":
        return "Não foi possível ler os dados enviados. Tente novamente."
    if field == "email":
        return "Informe um e-mail válido. Exemplo: nome@exemplo.com."
    if field == "password":
        return "A senha deve ter de 10 a 128 caracteres."
    if field == "name":
        return "Informe um nome de 1 a 80 caracteres."
    if field == "code":
        return "Informe um código de convite válido."
    if field == "token":
        return "Link de recuperação inválido. Solicite um novo link."
    if kind.startswith("uuid"):
        return "O identificador informado é inválido."
    if kind == "missing":
        return "Preencha todos os campos obrigatórios."
    return "Confira os dados informados e tente novamente."
