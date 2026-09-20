"""
Greek income tax + social security (ΕΦΚΑ) for self-employed individuals.
VERIFIED: 2026-09-19 — update annually.

Sources:
- Income tax scale (tax year 2026): ν. 5246/2025 article 3, replacing KFE article 15;
  applied to business profits via article 29. Confirmed by TaxHeaven and Grant Thornton.
  https://www.taxheaven.gr/law/5246/2025/arthro/3
  https://www.grant-thornton.gr/insights/article/neos-forologikos-nomos-5246-2025/
  0–10k 9%, 10–20k 20%, 20–30k 26%, 30–40k 34%, 40–60k 39%, 60k+ 44%.
  Employee tax credit (KFE art. 16) does NOT apply to business profits.
- ΕΦΚΑ 2026: e-ΕΦΚΑ circular 6/2026 (2.5% CPI). Six fixed monthly categories,
  freely chosen by the insured — NOT a % of income.
  https://www.taxheaven.gr/circulars/52023/egkyklios-e-efka-6-2026
  Cat 1 €250.77 … Cat 6 €675.87, plus €10/mo OAED unemployment.
- Tax prepayment (προκαταβολή): 55% of income tax; 27.5% on first filing.
  Prepayment is a cash-timing item credited next year, not extra tax on this year.
"""

from dataclasses import dataclass

# Progressive brackets as (lower_cents, upper_cents_or_None, percent)
INCOME_BRACKETS_CENTS = [
    (0, 1_000_000, 9),
    (1_000_000, 2_000_000, 20),
    (2_000_000, 3_000_000, 26),
    (3_000_000, 4_000_000, 34),
    (4_000_000, 6_000_000, 39),
    (6_000_000, None, 44),
]

# Monthly main pension + health, in cents. Source: e-ΕΦΚΑ εγκ. 6/2026.
EFKA_CATEGORY_MONTHLY_CENTS = {
    1: 25_077,
    2: 30_093,
    3: 36_063,
    4: 43_347,
    5: 51_945,
    6: 67_587,
}
OAED_UNEMPLOYMENT_MONTHLY_CENTS = 1_000  # €10
DEFAULT_EFKA_CATEGORY = 1

TAX_PREPAYMENT_RATE_BPS = 5500  # 55.00%
TAX_PREPAYMENT_FIRST_FILING_BPS = 2750  # 27.50%


@dataclass
class TaxBreakdown:
    gross_cents: int
    taxable_income_cents: int
    income_tax_cents: int
    social_security_cents: int
    net_cents: int
    effective_rate: float
    tax_prepayment_cents: int = 0


def _progressive_tax_cents(taxable_cents: int) -> int:
    tax = 0
    for lower, upper, pct in INCOME_BRACKETS_CENTS:
        if taxable_cents <= lower:
            break
        slice_end = taxable_cents if upper is None else min(taxable_cents, upper)
        band = slice_end - lower
        if band > 0:
            tax += band * pct // 100
    return tax


def calculate_tax(
    gross_cents: int,
    years_active: int = 1,
    efka_category: int = DEFAULT_EFKA_CATEGORY,
    period_months: int = 12,
) -> TaxBreakdown:
    months = max(1, min(12, period_months))
    category = efka_category if efka_category in EFKA_CATEGORY_MONTHLY_CENTS else DEFAULT_EFKA_CATEGORY
    monthly_ss = EFKA_CATEGORY_MONTHLY_CENTS[category] + OAED_UNEMPLOYMENT_MONTHLY_CENTS
    annual_ss = monthly_ss * 12
    social_security_cents = monthly_ss * months

    income = max(0, gross_cents)
    annual_gross = income * 12 // months
    taxable_annual = max(0, annual_gross - annual_ss)
    annual_tax = _progressive_tax_cents(taxable_annual)
    income_tax_cents = annual_tax * months // 12

    prepayment_bps = (
        TAX_PREPAYMENT_FIRST_FILING_BPS if years_active <= 1 else TAX_PREPAYMENT_RATE_BPS
    )
    annual_prepayment = annual_tax * prepayment_bps // 10_000
    tax_prepayment_cents = annual_prepayment * months // 12

    net_cents = gross_cents - income_tax_cents - social_security_cents
    effective_rate = (
        round((gross_cents - net_cents) / gross_cents * 100, 1) if gross_cents > 0 else 0.0
    )

    return TaxBreakdown(
        gross_cents=gross_cents,
        taxable_income_cents=taxable_annual * months // 12,
        income_tax_cents=income_tax_cents,
        tax_prepayment_cents=tax_prepayment_cents,
        social_security_cents=social_security_cents,
        net_cents=net_cents,
        effective_rate=effective_rate,
    )
