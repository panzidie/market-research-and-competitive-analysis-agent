import pytest
import pandas as pd
from utils.data_processor import DataProcessor


class TestDataProcessor:
    def setup_method(self):
        self.processor = DataProcessor()

    def test_calculate_market_metrics_basic(self):
        data = [
            {"value": 100, "date": "2024-01-01"},
            {"value": 200, "date": "2024-02-01"},
            {"value": 300, "date": "2024-03-01"},
        ]
        metrics = self.processor.calculate_market_metrics(data)
        assert metrics["total"] == 600
        assert metrics["mean"] == 200
        assert metrics["count"] == 3

    def test_calculate_market_metrics_empty(self):
        assert self.processor.calculate_market_metrics([]) == {}

    def test_calculate_market_metrics_single_value(self):
        data = [{"value": 42}]
        metrics = self.processor.calculate_market_metrics(data)
        assert metrics["total"] == 42
        assert metrics["count"] == 1

    def test_build_comparison_matrix(self):
        products = [
            {"name": "A", "price": 100, "features": "x"},
            {"name": "B", "price": 200, "features": "y"},
        ]
        df = self.processor.build_comparison_matrix(products, ["name", "price"])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_rank_products(self):
        df = pd.DataFrame({"name": ["A", "B"], "score": [80, 90]})
        ranked = self.processor.rank_products(df, "score")
        assert ranked.iloc[0]["name"] == "B"
