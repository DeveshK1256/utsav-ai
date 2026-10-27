import statistics
from typing import Any

from backend.app.schemas.quotes import (
    BenchmarkComparisonSchema,
    HiddenCostAlertSchema,
    QuoteComparisonItemSchema,
    QuoteComparisonResponseSchema,
)


class QuoteComparisonEngine:

    @classmethod
    def compute_median_benchmark(
        cls,
        category: str,
        city_tier: str,
        benchmark_samples: list[float],
        quote_unit_cost: float
    ) -> BenchmarkComparisonSchema:
        """
        Computes median benchmark for category and city tier.
        Enforces DEC-014 strict rule: if sample_size < 5, flags as 'limited_data'.
        All math computed deterministically.
        """
        n = len(benchmark_samples)
        if n < 5:
            return BenchmarkComparisonSchema(
                category=category,
                city_tier=city_tier,
                sample_size=n,
                median_unit_cost=round(statistics.median(benchmark_samples), 2) if n > 0 else None,
                quote_unit_cost=round(quote_unit_cost, 2),
                cost_status="limited_data",
                percentage_diff_vs_median=None,
                is_limited_data=True,
                reasoning={
                    "rule": "DEC-014: Sample size below statistical reliability threshold (n < 5)",
                    "sample_count": n,
                    "city_tier": city_tier,
                    "status_label": "Limited data"
                }
            )

        median_val = round(float(statistics.median(benchmark_samples)), 2)
        diff_pct = round(((quote_unit_cost - median_val) / median_val) * 100.0, 1)

        if diff_pct > 10.0:
            status = "above_median"
        elif diff_pct < -10.0:
            status = "below_median"
        else:
            status = "near_median"

        return BenchmarkComparisonSchema(
            category=category,
            city_tier=city_tier,
            sample_size=n,
            median_unit_cost=median_val,
            quote_unit_cost=round(quote_unit_cost, 2),
            cost_status=status,
            percentage_diff_vs_median=diff_pct,
            is_limited_data=False,
            reasoning={
                "formula": f"(({quote_unit_cost:.2f} - {median_val:.2f}) / {median_val:.2f}) * 100 = {diff_pct:.1f}%",
                "sample_count": n,
                "city_tier": city_tier,
                "benchmark_basis": f"Median of {n} verified {category} vendor contracts in {city_tier}"
            }
        )

    @classmethod
    def normalize_quote_to_guest_count(
        cls,
        raw_total: float,
        quoted_guest_count: int,
        target_guest_count: int,
        category: str
    ) -> float:
        """
        Normalizes variable per-guest quotes (e.g. catering, extra plate buffer)
        to the target event guest count. Fixed-cost categories (decor, photography) remain fixed.
        """
        if quoted_guest_count <= 0 or target_guest_count <= 0:
            return raw_total

        # Caterers are primarily per-plate variable costs
        if "cater" in category.lower():
            per_head = raw_total / float(quoted_guest_count)
            return round(per_head * float(target_guest_count), 2)

        # Venues with per-person charges
        return raw_total

    @classmethod
    def compare_quotes(
        cls,
        event_id: str,
        category: str,
        target_guest_count: int,
        quotes_data: list[dict[str, Any]],
        benchmark_samples: list[float] | None = None
    ) -> QuoteComparisonResponseSchema:
        """
        Compares multiple quotes side-by-side, adding conservative buffers for missing hidden costs.
        """
        benchmark_samples = benchmark_samples or []
        compared_items: list[QuoteComparisonItemSchema] = []

        for q in quotes_data:
            quote_id = q["id"]
            vendor_name = q["vendor_name"]
            raw_total = float(q["total_amount"])
            quoted_guests = q.get("quoted_guest_count", target_guest_count)
            normalized_base = cls.normalize_quote_to_guest_count(raw_total, quoted_guests, target_guest_count, category)

            # Analyze hidden cost risks
            alerts: list[HiddenCostAlertSchema] = q.get("hidden_cost_alerts", [])
            missing_risks = [a.name for a in alerts if a.status == "missing_from_quote"]

            # Estimate conservative buffer (e.g. ₹15,000 per major missing unmentioned item)
            risk_buffer = len(missing_risks) * 12500.0
            effective_total = round(normalized_base + risk_buffer, 2)
            per_guest = round(effective_total / float(max(1, target_guest_count)), 2)

            compared_items.append(
                QuoteComparisonItemSchema(
                    quote_id=quote_id,
                    vendor_name=vendor_name,
                    raw_total=raw_total,
                    effective_total_with_hidden_buffer=effective_total,
                    normalized_cost_per_guest=per_guest,
                    line_items=q.get("line_items", []),
                    hidden_cost_risk_count=len(missing_risks),
                    hidden_cost_risks=missing_risks
                )
            )

        # Find best value: minimum effective total with lowest hidden risks
        best_quote = min(compared_items, key=lambda x: (x.effective_total_with_hidden_buffer, x.hidden_cost_risk_count)) if compared_items else None

        n_samples = len(benchmark_samples)
        median_unit = round(float(statistics.median(benchmark_samples)), 2) if n_samples >= 5 else None

        return QuoteComparisonResponseSchema(
            event_id=event_id,
            category=category,
            guest_count=target_guest_count,
            compared_quotes=compared_items,
            benchmark_median_unit_cost=median_unit,
            benchmark_sample_size=n_samples,
            benchmark_is_limited_data=(n_samples < 5),
            best_value_quote_id=best_quote.quote_id if best_quote else None,
            reasoning={
                "formula": "Effective Total = Normalized Base Quote + (Missing Hidden Cost Items * ₹12,500 Risk Buffer)",
                "normalized_guest_count": target_guest_count,
                "benchmark_sample_size": n_samples,
                "comparison_metric": "Effective Total Cost after normalizing headcounts and risk buffers"
            }
        )
