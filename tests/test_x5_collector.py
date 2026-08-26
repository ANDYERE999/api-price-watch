from pricewatch.collectors.x5_pricing_page import _price


def test_price_parser_handles_currency_and_missing_values() -> None:
    assert _price("¥1.848") == 1.848
    assert _price("—") is None
