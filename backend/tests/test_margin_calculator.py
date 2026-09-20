from app.services.margin_calculator import calculate_margin


def test_empty_inputs_still_include_efka():
    result = calculate_margin([], [])
    assert result.invoiced_cents == 0
    assert result.keep_percent == 0
    assert result.effective_hourly_cents is None
    assert result.social_security_cents == 312_924
    assert result.net_cents == -312_924


def test_margin_after_fees_expenses_and_tax():
    transactions = [
        {"amount_cents": 100_000, "fee_cents": 290, "net_cents": 99_710},
    ]
    expenses = [{"amount_cents": 10_000}]
    result = calculate_margin(transactions, expenses, efka_category=1)
    assert result.invoiced_cents == 100_000
    assert result.fees_cents == 290
    assert result.expenses_cents == 10_000
    assert result.profit_cents == 89_710
    assert result.net_cents == result.tax.net_cents
    assert result.net_cents < result.invoiced_cents
    assert result.keep_percent == round(result.net_cents / 100_000 * 100, 1)


def test_effective_hourly_when_hours_provided():
    transactions = [{"amount_cents": 200_000, "fee_cents": 0, "net_cents": 200_000}]
    result = calculate_margin(transactions, [], hours_worked=10, efka_category=1)
    assert result.effective_hourly_cents == round(result.net_cents / 10)


def test_disclaimer_present():
    result = calculate_margin([], [])
    assert "accountant" in result.disclaimer.lower()


def test_monthly_period_charges_one_month_of_efka():
    transactions = [{"amount_cents": 416_666, "fee_cents": 0, "net_cents": 416_666}]
    month = calculate_margin(transactions, [], efka_category=1, period_months=1)
    year = calculate_margin(transactions, [], efka_category=1, period_months=12)
    assert month.social_security_cents * 12 == year.social_security_cents


def test_expenses_without_income_reduce_net():
    result = calculate_margin([], [{"amount_cents": 5000}], efka_category=1, period_months=1)
    assert result.expenses_cents == 5000
    assert result.net_cents == -5000 - 26_077
    assert result.vat_cents == 0


def test_charges_vat_extracts_standard_rate_from_inclusive_gross():
    transactions = [{"amount_cents": 124_000, "fee_cents": 0, "net_cents": 124_000}]
    without = calculate_margin(transactions, [], charges_vat=False, period_months=1)
    with_vat = calculate_margin(transactions, [], charges_vat=True, period_months=1)
    assert without.vat_cents == 0
    assert with_vat.vat_cents == 24_000
    assert with_vat.profit_cents == 100_000
    assert with_vat.net_cents < without.net_cents
