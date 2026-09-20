from app.services.tax_engine import calculate_tax, TaxBreakdown


def test_basic_calculation():
    result = calculate_tax(5_000_000)  # €50,000 annual
    assert result.gross_cents == 5_000_000
    assert result.income_tax_cents > 0
    assert result.tax_prepayment_cents >= 0
    assert result.social_security_cents > 0
    assert result.net_cents < result.gross_cents
    assert 0 < result.effective_rate < 100


def test_low_income():
    result = calculate_tax(500_000)  # €5,000 annual
    assert result.income_tax_cents > 0
    assert result.net_cents > 0


def test_progressive_brackets():
    low = calculate_tax(3_000_000)   # €30K
    mid = calculate_tax(6_000_000)   # €60K
    high = calculate_tax(10_000_000)  # €100K
    assert low.effective_rate <= mid.effective_rate <= high.effective_rate


def test_tax_prepayment_first_year():
    result = calculate_tax(5_000_000, years_active=1)
    assert result.tax_prepayment_cents > 0
    assert result.tax_prepayment_cents == result.income_tax_cents * 275 // 1000


def test_tax_prepayment_after_first_filing():
    result_first = calculate_tax(5_000_000, years_active=1)
    result_later = calculate_tax(5_000_000, years_active=5)
    assert result_first.tax_prepayment_cents < result_later.tax_prepayment_cents
    assert result_later.tax_prepayment_cents == result_later.income_tax_cents * 55 // 100


def test_net_excludes_prepayment():
    result = calculate_tax(5_000_000, years_active=1)
    assert result.net_cents == (
        result.gross_cents - result.income_tax_cents - result.social_security_cents
    )


def test_fifty_thousand_category_one_exact():
    result = calculate_tax(5_000_000, efka_category=1)
    assert result.social_security_cents == 312_924
    assert result.income_tax_cents == 1_157_959
    assert result.net_cents == 3_529_117


def test_one_month_does_not_charge_annual_efka():
    annual = calculate_tax(5_000_000, efka_category=1, period_months=12)
    month = calculate_tax(5_000_000 // 12, efka_category=1, period_months=1)
    assert month.social_security_cents == annual.social_security_cents // 12
    assert month.social_security_cents == 26_077
    assert month.net_cents > 0


def test_efka_category_override():
    cat1 = calculate_tax(5_000_000, efka_category=1)
    cat6 = calculate_tax(5_000_000, efka_category=6)
    assert cat6.social_security_cents > cat1.social_security_cents


def test_zero_gross_still_owes_efka():
    result = calculate_tax(0, efka_category=1)
    assert result.income_tax_cents == 0
    assert result.social_security_cents == 312_924
    assert result.net_cents == -312_924
    assert result.effective_rate == 0


def test_breakdown_type():
    result = calculate_tax(1_000_000)
    assert isinstance(result, TaxBreakdown)
