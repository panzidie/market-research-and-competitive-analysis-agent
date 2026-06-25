import pandas as pd


class DataProcessor:
    """确定性计算层：数据聚合、指标计算，杜绝 LLM 算术幻觉"""

    @staticmethod
    def calculate_market_metrics(data: list[dict], value_field: str = "value", date_field: str = "date") -> dict:
        """计算市场指标：环比、同比、均值、趋势"""
        df = pd.DataFrame(data)
        if df.empty:
            return {}

        metrics = {
            "total": float(df[value_field].sum()),
            "mean": float(df[value_field].mean()),
            "median": float(df[value_field].median()),
            "max": float(df[value_field].max()),
            "min": float(df[value_field].min()),
            "count": int(len(df)),
        }

        if date_field in df.columns:
            df[date_field] = pd.to_datetime(df[date_field])
            df = df.sort_values(date_field)
            if len(df) >= 2:
                latest = df[value_field].iloc[-1]
                previous = df[value_field].iloc[-2]
                if previous != 0:
                    metrics["qoq_change"] = float((latest - previous) / previous * 100)
                else:
                    metrics["qoq_change"] = None

        return metrics

    @staticmethod
    def build_comparison_matrix(products: list[dict], dimensions: list[str]) -> pd.DataFrame:
        """构建竞品对比矩阵"""
        records = []
        for product in products:
            row = {"name": product.get("name", "")}
            for dim in dimensions:
                row[dim] = product.get(dim, "N/A")
            records.append(row)
        return pd.DataFrame(records)

    @staticmethod
    def rank_products(matrix_df: pd.DataFrame, score_column: str) -> pd.DataFrame:
        """按评分列对竞品排序"""
        if score_column not in matrix_df.columns:
            return matrix_df
        return matrix_df.sort_values(score_column, ascending=False).reset_index(drop=True)
