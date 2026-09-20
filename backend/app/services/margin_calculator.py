from dataclasses import dataclass
from app.services.tax_engine import calculate_tax, TaxBreakdown

TAX_DISCLAIMER = (
    "Tax estimates are approximate and based on 2026 Greek rates for self-employed "
    "individuals. Always consult your accountant."
)


@dataclass
class MarginResult:
    invoiced_cents: int
    fees_cents: int
    expenses_cents: int
    profit_cents: int
    income_tax_cents: int
    tax_prepayment_cents: int
    social_security_cents: int
    vat_cents: int
    net_cents: int
    keep_percent: float
    effective_hourly_cents: int | None
    tax: TaxBreakdown
    disclaimer: str = TAX_DISCLAIMER


VAT_STANDARD_RATE = 24
VAT_INCLUSIVE_DIVISOR = 100 + VAT_STANDARD_RATE


def _vat_from_inclusive(cents: int) -> int:
    if cents <= 0:
        return 0
    return cents * VAT_STANDARD_RATE // VAT_INCLUSIVE_DIVISOR


def calculate_margin(
    transactions: list[dict],
    expenses: list[dict],
    hours_worked: float = 0,
    efka_category: int = 1,
    years_active: int = 1,
    period_months: int = 12,
    charges_vat: bool = False,
) -> MarginResult:
    invoiced_cents = sum(int(txn.get("amount_cents", 0)) for txn in transactions)
    fees_cents = sum(int(txn.get("fee_cents", 0)) for txn in transactions)
    net_after_fees = sum(int(txn.get("net_cents", 0)) for txn in transactions)
    expenses_cents = sum(int(exp.get("amount_cents", 0)) for exp in expenses)
    vat_cents = _vat_from_inclusive(invoiced_cents) if charges_vat else 0
    raw_profit = net_after_fees - vat_cents - expenses_cents
    profit_cents = max(0, raw_profit)

    tax = calculate_tax(
        profit_cents,
        years_active=years_active,
        efka_category=efka_category,
        period_months=period_months,
    )

    net_cents = raw_profit - tax.income_tax_cents - tax.social_security_cents
    keep_percent = round(net_cents / invoiced_cents * 100, 1) if invoiced_cents else 0.0
    hourly = None
    if hours_worked > 0:
        hourly = round(net_cents / hours_worked)

    return MarginResult(
        invoiced_cents=invoiced_cents,
        fees_cents=fees_cents,
        expenses_cents=expenses_cents,
        profit_cents=profit_cents,
        income_tax_cents=tax.income_tax_cents,
        tax_prepayment_cents=tax.tax_prepayment_cents,
        social_security_cents=tax.social_security_cents,
        vat_cents=vat_cents,
        net_cents=net_cents,
        keep_percent=keep_percent,
        effective_hourly_cents=hourly,
        tax=tax,
    )
