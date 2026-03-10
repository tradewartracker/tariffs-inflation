"""
config.py — All user-facing parameters for the tariff PCE pass-through pipeline.

Adjust the values in this file to change methodology assumptions or the time period
being analyzed. No edits to pipeline.py or the notebook should be needed for routine
updates.
"""

import os

# ── BEA API key ───────────────────────────────────────────────────────────────
# Set the BEA_KEY environment variable to avoid committing credentials.
# Falls back to the literal key if the env var is not set.
BEA_KEY: str = os.environ.get("BEA_KEY", "1B069F6A-DB45-4EBF-8324-2F4A83E223EF")

# ── Data ──────────────────────────────────────────────────────────────────────
IMPORTS_FILE: str = "data/imports/TOTALnaics-data-2025-12.parquet"

# ── BEA IO tables ─────────────────────────────────────────────────────────────
IO_YEAR: int = 2022          # Year of BEA Supply (Table 262) and Use (Table 259) tables

# ── Tariff rates ──────────────────────────────────────────────────────────────
TARIFF_BASELINE_YEAR: int  = 2024       # Annual-average baseline (all 12 months pooled)
TARIFF_CURRENT_MONTH: str  = "2025-12"  # Single month for "current" tariff rates (YYYY-MM)

# ── Leontief inverse source ──────────────────────────────────────────────────
# Controls which Leontief inverse is used for supply-chain propagation.
#
#   "computed"  → derived from scratch by inverting (I - A) built from BEA Use
#                 Table 259.  Differences vs. BEA's published table are confined
#                 to service-industry rows (wholesale/retail trade) that have
#                 near-zero import shares and no tariff exposure, so results are
#                 unaffected in practice.  This is the default.
#
#   "bea"       → fetches BEA's pre-computed Commodity-by-Commodity Total
#                 Requirements (TableID 59), which uses BEA's full Make/Use
#                 model including trade and transport margins.  Methodologically
#                 closer to Yale Budget Lab.  A is still built from Table 259
#                 (needed for the column-sum sanity check) but L is replaced.
LEONTIEF_SOURCE: str = "computed"

# ── Pass-through / markup assumption ─────────────────────────────────────────
# Controls how the tariff effect is aggregated from producer to consumer prices
# using the PCE bridge table (methodology §7 / Minton & Somale 2025 §4).
#
#   "constant_dollar"  → retailers preserve a fixed dollar margin; only the
#                        producers' value portion of consumer spending passes
#                        through.  This is the conservative baseline used in
#                        the Fed papers and is the recommended default.
#
#   "constant_percent" → retailers preserve a fixed percentage margin; the
#                        full purchasers' value is the relevant weight.  This
#                        yields a larger predicted consumer price effect.
MARKUP_ASSUMPTION: str = "constant_dollar"

# ── Inflation measure for monthly counterfactual ─────────────────────────────
# Selects the NIPA T20804 series used in the monthly (Dec-to-Dec) comparison.
#
#   "core_pce"        → PCE excluding food and energy (T20804)
#   "headline_pce"    → Total PCE (T20804)
#   "core_goods_pce"  → Core goods only (T20404, quarterly); skips the monthly
#                        step in Cell 7 and uses only the quarterly index in Cell 8.
#
# For the quarterly core-goods-only index (Cell 8), see CORE_GOODS_CATEGORIES
# and NIPA_CROSSWALK below; that index is always constructed from T20404.
INFLATION_MEASURE: str = "core_pce"

# ── Counterfactual baseline month ─────────────────────────────────────────────
# The pre-tariff reference month used in the monthly counterfactual comparison.
# Must be a YYYY-MM string that appears in the T20804 data.
COUNTERFACTUAL_BASELINE_MONTH: str = "2024-12"

# ── Excess-inflation baseline window ─────────────────────────────────────────
# Defines the "normal" pre-tariff trend used in the category-level scatter plot
# (Cell 9 / methodology §9).  Each year t in the range contributes one YoY
# growth rate: (P_t - P_{t-1}) / P_{t-1}.  These are averaged to form the
# baseline.  Evaluated inclusive of both endpoints.
#
#   Example:  EXCESS_BASELINE_START=2015, EXCESS_BASELINE_END=2018
#             → averages 2015, 2016, 2017, 2018 YoY rates (i.e. 2014→2018 data)
EXCESS_BASELINE_START: int = 2000
EXCESS_BASELINE_END:   int = 2019

# ── Excess-inflation current window ──────────────────────────────────────────
# The growth window for the "current" period in the excess-inflation scatter
# (Cell 9 / methodology §9).  Both values are 'YYYY-MM' strings.
#
#   Default (Dec-over-Dec, full year):
#     EXCESS_CURRENT_START_MONTH = "2024-12"
#     EXCESS_CURRENT_END_MONTH   = "2025-12"
#
#   To use a narrower window, e.g. Dec 2024 → Mar 2025 vs. baseline Dec→Mar:
#     EXCESS_CURRENT_START_MONTH = "2024-12"
#     EXCESS_CURRENT_END_MONTH   = "2025-03"
#
# The baseline comparison always uses the same calendar months, shifted to each
# baseline year (e.g. Dec 2014 → Mar 2015 for baseline year 2015).
EXCESS_CURRENT_START_MONTH: str = "2024-12"
EXCESS_CURRENT_END_MONTH:   str = "2025-12"

# ── PCE category lists ────────────────────────────────────────────────────────
# These lists use the exact PCE_category strings that appear in the BEA PCE
# Bridge workbook.  They define which categories count as "core goods" for the
# counterfactual and scatter-plot steps.

FOOD_CATEGORIES: list = [
    "Food furnished to employees",
    "Food produced and consumed on farms",
    "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Alcoholic beverages purchased for off-premises consumption",
    "Purchased meals and beverages",
]

ENERGY_CATEGORIES: list = [
    "Fuel oil and other fuels",
    "Motor vehicle fuels, lubricants, and fluids",
    "Electricity",
    "Natural gas",
]

DURABLE_GOODS_CATEGORIES: list = [
    "New motor vehicles",
    "Net purchases of used motor vehicles",
    "Motor vehicle parts and accessories",
    "Sports and recreational vehicles",
    "Furniture and furnishings",
    "Household appliances",
    "Glassware, tableware, and household utensils",
    "Tools and equipment for house and garden",
    "Recreational items",
    "Sporting equipment, supplies, guns, and ammunition",
    "Musical instruments",
    "Jewelry and watches",
    "Therapeutic appliances and equipment",
    "Telephone and related communication equipment",
    "Video, audio, photographic, and information processing equipment and media",
]

NONDURABLE_GOODS_CATEGORIES: list = [
    "Men's and boys' clothing",
    "Women's and girls' clothing",
    "Children's and infants' clothing",
    "Other clothing materials and footwear",
    "Luggage and similar personal items",
    "Household supplies",
    "Pharmaceutical and other medical products",
    "Personal care products",
    "Magazines, newspapers, and stationery",
    "Educational books",
    "Recreational books",
    "Tobacco",
]

# Combined: core goods = durables + nondurables (ex food and energy)
CORE_GOODS_CATEGORIES: list = DURABLE_GOODS_CATEGORIES + NONDURABLE_GOODS_CATEGORIES

# ── NIPA T20404 crosswalk ─────────────────────────────────────────────────────
# Maps our PCE bridge category names (keys) → exact LineDescription strings in
# BEA NIPA Table T20404.  Used to pull quarterly price indexes for each of the
# 27 core goods categories.
#
# If BEA renames a T20404 line in a future data release, update the value here.
NIPA_CROSSWALK: dict = {
    "New motor vehicles":
        "New motor vehicles (55)",
    "Net purchases of used motor vehicles":
        "Net purchases of used motor vehicles (56)",
    "Motor vehicle parts and accessories":
        "Motor vehicle parts and accessories (58)",
    "Sports and recreational vehicles":
        "Sports and recreational vehicles (79)",
    "Furniture and furnishings":
        "Furniture and furnishings (parts of 31 and 32)",
    "Household appliances":
        "Household appliances (part of 33)",
    "Glassware, tableware, and household utensils":
        "Glassware, tableware, and household utensils (34)",
    "Tools and equipment for house and garden":
        "Tools and equipment for house and garden (35)",
    "Recreational items":
        "Recreational items (parts of 80, 92, and 93)",
    "Sporting equipment, supplies, guns, and ammunition":
        "Sporting equipment, supplies, guns, and ammunition (part of 80)",
    "Musical instruments":
        "Musical instruments (part of 80)",
    "Jewelry and watches":
        "Jewelry and watches (part of 119)",
    "Therapeutic appliances and equipment":
        "Therapeutic appliances and equipment (42)",
    "Video, audio, photographic, and information processing equipment and media":
        "Video, audio, photographic, and information processing equipment and media (75, 76, and part of 93)",
    "Telephone and related communication equipment":
        "Telephone and related communication equipment",
    "Men's and boys' clothing":
        "Men's and boys' clothing (11)",
    "Women's and girls' clothing":
        "Women's and girls' clothing (10)",
    "Children's and infants' clothing":
        "Children's and infants' clothing (12)",
    "Other clothing materials and footwear":
        "Other clothing materials and footwear (13 and 17)",
    "Luggage and similar personal items":
        "Luggage and similar personal items (part of 119)",
    "Household supplies":
        "Household supplies (parts of 32 and 36)",
    "Pharmaceutical and other medical products":
        "Pharmaceutical and other medical products (40 and 41)",
    "Personal care products":
        "Personal care products (part of 118)",
    "Magazines, newspapers, and stationery":
        "Magazines, newspapers, and stationery (part of 90)",
    "Educational books":
        "Educational books (96)",
    "Recreational books":
        "Recreational books (part of 90)",
    "Tobacco":
        "Tobacco (127)",
}
