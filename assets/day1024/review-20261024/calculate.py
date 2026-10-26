"""报告配套的确定性计算；只读输入，结果写到同目录 model-results.json。"""
from decimal import Decimal, ROUND_CEILING
import json
from pathlib import Path
import sys


def d(value):
    return Decimal(str(value))


def output(value):
    if isinstance(value, Decimal):
        return float(value.quantize(Decimal("0.000001")))
    raise TypeError(type(value).__name__)


def calculate(model):
    costs = {row["id"]: d(row["amount"]) for row in model["customer_costs"]}
    vendor = {row["id"]: d(row["amount"]) for row in model["vendor_direct_costs"]}
    if any(value < 0 for value in [*costs.values(), *vendor.values()]):
        raise ValueError("费用不能为负")
    cost = sum(costs.values())
    unit_revenue = d(model["net_revenue_per_order"])
    margin = d(model["pre_marketing_contribution_rate"])
    incremental = d(model["incremental_share"])
    if cost <= 0 or unit_revenue <= 0 or not 0 <= margin <= 1 or not 0 <= incremental <= 1:
        raise ValueError("成本、单笔净收入或比例无效")
    unit_contribution = unit_revenue * margin

    def break_even(share):
        denominator = unit_contribution * share
        return int((cost / denominator).to_integral_value(rounding=ROUND_CEILING)) if denominator > 0 else None

    scenarios = []
    for row in model["scenarios"]:
        leads, accepted, customers = row["qualified_leads"], row["sales_accepted"], row["new_customers"]
        if not (isinstance(leads, int) and isinstance(accepted, int) and isinstance(customers, int)):
            raise ValueError("人数必须为整数")
        if not 0 <= customers <= accepted <= leads:
            raise ValueError("漏斗数量必须递减且非负")
        revenue = d(customers) * unit_revenue
        contribution = revenue * margin * incremental
        scenarios.append({
            **row, "net_revenue": revenue, "incremental_pre_marketing_contribution": contribution,
            "net_contribution_after_marketing": contribution - cost,
            "marketing_roi": (contribution - cost) / cost,
            "listed_cost_cpl": cost / d(leads) if leads else None,
            "listed_cost_cac": cost / d(customers) if customers else None,
        })
    revenue = d(model["vendor_service_revenue"])
    vendor_cost = sum(vendor.values())
    source = model["source_numbers_for_arithmetic_only"]
    total_opportunity = sum(d(value) for value in source["opportunity_amounts_wan"])
    base = next(row for row in scenarios if row["id"] == "base")
    return {
        "status": model["status"], "currency": model["currency"], "horizon_days": model["horizon_days"],
        "customer_total_listed_cost": cost,
        "customer_assumed_external_payments": cost - costs["internal_labor"],
        "unit_pre_marketing_contribution": unit_contribution,
        "break_even_orders": break_even(incremental),
        "break_even_orders_at_50_percent_incrementality": break_even(d("0.5")),
        "base_roi_at_50_percent_incrementality": (d(base["new_customers"]) * unit_contribution * d("0.5") - cost) / cost,
        "vendor_service_revenue": revenue, "vendor_direct_cost": vendor_cost,
        "vendor_delivery_contribution": revenue - vendor_cost,
        "vendor_delivery_contribution_margin": (revenue - vendor_cost) / revenue if revenue > 0 else None,
        "scenarios": scenarios,
        "source_arithmetic": {
            "opportunity_total_wan": total_opportunity,
            "overseas_amount_share": d(source["overseas_amount_wan"]) / total_opportunity,
            "touch_to_opportunity_ratio": d(source["opportunities"]) / d(source["touches"]),
            "reply_lift_vs_manual_pp": d(source["reply_rate_percent"]) - d(source["manual_baseline_percent"]),
            "reply_lift_r16_r27_pp": d(source["reply_rate_percent"]) - d(source["r16_percent"]),
            "agency_flow_assumption_not_saving": d(source["unverified_monthly_marketing"]) * d(source["unverified_agency_share"]),
        },
        "limitations": model["limitations"],
    }


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    root = Path(__file__).resolve().parent
    inputs = json.loads((root / "model-inputs.json").read_text(encoding="utf-8"))
    results = calculate(inputs)
    text = json.dumps(results, ensure_ascii=False, indent=2, default=output)
    (root / "model-results.json").write_text(text + "\n", encoding="utf-8")
    print(text)
