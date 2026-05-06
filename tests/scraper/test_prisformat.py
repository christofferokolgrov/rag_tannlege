import pytest

from scraper.prisformat import ParsedPrice, Prisformat, PrisformatError, parse_price


def test_parse_price_bare_integer_is_fast():
    assert parse_price("1595") == ParsedPrice(1595, 1595, Prisformat.FAST)


def test_parse_price_period_thousands_separator():
    assert parse_price("1.595 kr") == ParsedPrice(1595, 1595, Prisformat.FAST)


def test_parse_price_space_thousands_separator():
    assert parse_price("1 595 kr") == ParsedPrice(1595, 1595, Prisformat.FAST)


def test_parse_price_accepts_nok_and_case_variants():
    assert parse_price("NOK 1500") == ParsedPrice(1500, 1500, Prisformat.FAST)
    assert parse_price("Kr 1500") == ParsedPrice(1500, 1500, Prisformat.FAST)
    assert parse_price("kr 1500") == ParsedPrice(1500, 1500, Prisformat.FAST)


def test_parse_price_fra_prefix_with_norwegian_dash_suffix():
    assert parse_price("Fra kr 1.500,-") == ParsedPrice(1500, None, Prisformat.FRA)
    assert parse_price("fra 1500") == ParsedPrice(1500, None, Prisformat.FRA)


def test_parse_price_hyphen_range_is_spread():
    assert parse_price("950 - 1545") == ParsedPrice(950, 1545, Prisformat.SPREAD)


def test_parse_price_spread_with_thousands_separators():
    assert parse_price("NOK 11 900 - 32 000") == ParsedPrice(
        11900, 32000, Prisformat.SPREAD
    )
    assert parse_price("950 - 1.545") == ParsedPrice(950, 1545, Prisformat.SPREAD)


def test_parse_price_accepts_en_dash_and_em_dash_as_range():
    assert parse_price("950–1545") == ParsedPrice(950, 1545, Prisformat.SPREAD)
    assert parse_price("950—1545") == ParsedPrice(950, 1545, Prisformat.SPREAD)


def test_parse_price_etter_konsultasjon_without_number():
    assert parse_price("Etter konsultasjon") == ParsedPrice(
        None, None, Prisformat.ETTER_KONSULTASJON
    )


def test_parse_price_empty_string_is_etter_konsultasjon():
    assert parse_price("") == ParsedPrice(None, None, Prisformat.ETTER_KONSULTASJON)
    assert parse_price("   ") == ParsedPrice(None, None, Prisformat.ETTER_KONSULTASJON)


def test_parse_price_per_halvtime():
    assert parse_price("650 per halvtime") == ParsedPrice(
        650, 650, Prisformat.PER_HALVTIME
    )


def test_parse_price_per_dose_accepts_space_or_underscore():
    assert parse_price("290 per dose") == ParsedPrice(290, 290, Prisformat.PER_DOSE)
    assert parse_price("290 per_dose") == ParsedPrice(290, 290, Prisformat.PER_DOSE)
    assert parse_price("Bedøvelse 290 per dose") == ParsedPrice(
        290, 290, Prisformat.PER_DOSE
    )


def test_parse_price_per_stk():
    assert parse_price("215 per stk") == ParsedPrice(215, 215, Prisformat.PER_STK)
    assert parse_price("215 per_stk") == ParsedPrice(215, 215, Prisformat.PER_STK)


def test_parse_price_garbage_with_digits_raises():
    with pytest.raises(PrisformatError):
        parse_price("abc 1 2 3 def")
