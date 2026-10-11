"""Datas dos ciclos de cartão, incluindo meses curtos e virada de ano."""

from calendar import monthrange
from datetime import date


def shift_month(month: date, offset: int) -> date:
    number = month.year * 12 + month.month - 1 + offset
    year, index = divmod(number, 12)
    if not 1 <= year <= 9999:
        raise ValueError("Data fora do intervalo permitido.")
    return date(year, index + 1, 1)


def day_in_month(month: date, day: int) -> date:
    return date(month.year, month.month, min(day, monthrange(month.year, month.month)[1]))


def cycle_for_close(card, close_month: date) -> tuple[date, date, date]:
    closes_on = day_in_month(close_month, card.closing_day)
    due_month = close_month
    due_on = day_in_month(due_month, card.due_day)
    if due_on <= closes_on:
        due_month = shift_month(close_month, 1)
        due_on = day_in_month(due_month, card.due_day)
    return due_month, closes_on, due_on


def first_cycle(card, purchased_on: date) -> tuple[date, date, date]:
    close_month = purchased_on.replace(day=1)
    closes_on = day_in_month(close_month, card.closing_day)
    if purchased_on > closes_on or (purchased_on == closes_on and card.closing_day_next_bill):
        close_month = shift_month(close_month, 1)
    return cycle_for_close(card, close_month)


def cycle_for_due_month(card, month: date) -> tuple[date, date, date]:
    for close_month in (month, shift_month(month, -1)):
        result = cycle_for_close(card, close_month)
        if result[0] == month:
            return result
    raise ValueError("Não foi possível calcular o ciclo da fatura.")


def split_cents(amount: int, count: int) -> list[int]:
    if count < 1 or amount < count:
        raise ValueError("O valor precisa cobrir ao menos um centavo por parcela.")
    each, rest = divmod(amount, count)
    return [each] * (count - 1) + [each + rest]
