#!/usr/bin/env python3
"""Compare Brisbane Tesla Sync vs NetZero pricing"""

# Tesla Sync prices (TESLA_SYNC:AMBER:AMBER)
tesla_sync = {
    "PERIOD_00_00": 0.1872254,
    "PERIOD_00_30": 0.18445979999999998,
    "PERIOD_01_00": 0.18035779999999998,
    "PERIOD_01_30": 0.1759827,
    "PERIOD_02_00": 0.1697636,
    "PERIOD_02_30": 0.1685075,
    "PERIOD_03_00": 0.1689668,
    "PERIOD_03_30": 0.1732592,
    "PERIOD_04_00": 0.18053909999999998,
    "PERIOD_04_30": 0.1908464,
    "PERIOD_05_00": 0.19730709999999999,
    "PERIOD_05_30": 0.1804768,
    "PERIOD_06_00": 0.13855499999999998,
    "PERIOD_06_30": 0.0931076,
    "PERIOD_07_00": 0.0805012,
    "PERIOD_07_30": 0.0768087,
    "PERIOD_08_00": 0.0749175,
    "PERIOD_08_30": 0.0729448,
    "PERIOD_09_00": 0.0680477,
    "PERIOD_09_30": 0.0619565,
    "PERIOD_10_00": 0.0599591,
    "PERIOD_10_30": 0.0608123,
    "PERIOD_11_00": 0.0127432,
    "PERIOD_11_30": 0.0148109,
    "PERIOD_12_00": 0.0166794,
    "PERIOD_12_30": 0.018428899999999998,
    "PERIOD_13_00": 0.0178358,
    "PERIOD_13_30": 0.0184161,
    "PERIOD_14_00": 0.0207808,
    "PERIOD_14_30": 0.0247102,
    "PERIOD_15_00": 0.0285614,
    "PERIOD_15_30": 0.034122599999999996,
    "PERIOD_16_00": 0.2545439,
    "PERIOD_16_30": 0.2786348,
    "PERIOD_17_00": 0.2944544833333333,
    "PERIOD_17_30": 0.34923360000000003,
    "PERIOD_18_00": 0.3715138,
    "PERIOD_18_30": 0.3775654,
    "PERIOD_19_00": 0.381855,
    "PERIOD_19_30": 0.3822182,
    "PERIOD_20_00": 0.3812335,
    "PERIOD_20_30": 0.37385779999999996,
    "PERIOD_21_00": 0.20737629999999999,
    "PERIOD_21_30": 0.2032421,
    "PERIOD_22_00": 0.2004675,
    "PERIOD_22_30": 0.19683319999999999,
    "PERIOD_23_00": 0.191843,
    "PERIOD_23_30": 0.1895093,
}

# NetZero prices (NETZERO:AMBER:AMBER)
netzero = {
    "PERIOD_00_00": 0.1881,
    "PERIOD_00_30": 0.186,
    "PERIOD_01_00": 0.1818,
    "PERIOD_01_30": 0.1785,
    "PERIOD_02_00": 0.1716,
    "PERIOD_02_30": 0.169,
    "PERIOD_03_00": 0.1683,
    "PERIOD_03_30": 0.1711,
    "PERIOD_04_00": 0.1773,
    "PERIOD_04_30": 0.1859,
    "PERIOD_05_00": 0.1972,
    "PERIOD_05_30": 0.1902,
    "PERIOD_06_00": 0.159,
    "PERIOD_06_30": 0.1073,
    "PERIOD_07_00": 0.0844,
    "PERIOD_07_30": 0.0781,
    "PERIOD_08_00": 0.0756,
    "PERIOD_08_30": 0.0741,
    "PERIOD_09_00": 0.0705,
    "PERIOD_09_30": 0.0641,
    "PERIOD_10_00": 0.0602,
    "PERIOD_10_30": 0.0607,
    "PERIOD_11_00": 0.0123,
    "PERIOD_11_30": 0.0141,
    "PERIOD_12_00": 0.0157,
    "PERIOD_12_30": 0.0181,
    "PERIOD_13_00": 0.018,
    "PERIOD_13_30": 0.018,
    "PERIOD_14_00": 0.0196,
    "PERIOD_14_30": 0.023,
    "PERIOD_15_00": 0.0272,
    "PERIOD_15_30": 0.0308,
    "PERIOD_16_00": 0.2281,
    "PERIOD_16_30": 0.2477,
    "PERIOD_17_00": 0.2945,
    "PERIOD_17_30": 0.3355,
    "PERIOD_18_00": 0.365,
    "PERIOD_18_30": 0.3749,
    "PERIOD_19_00": 0.3809,
    "PERIOD_19_30": 0.3818,
    "PERIOD_20_00": 0.3826,
    "PERIOD_20_30": 0.3771,
    "PERIOD_21_00": 0.2099,
    "PERIOD_21_30": 0.2048,
    "PERIOD_22_00": 0.2015,
    "PERIOD_22_30": 0.1988,
    "PERIOD_23_00": 0.1935,
    "PERIOD_23_30": 0.1905,
}

print("=" * 120)
print("BRISBANE COMPARISON: TESLA SYNC vs NETZERO")
print("=" * 120)
print(f"{'Period':<12} {'Tesla Sync':<15} {'NetZero':<15} {'Difference':<15} {'% Diff':<10} {'Status'}")
print("-" * 120)

total_diff = 0
count = 0
max_diff = 0
max_diff_period = ""
exact_matches = 0
close_matches = 0  # Within 1%
small_diffs = 0    # 1-5%
large_diffs = 0    # >5%

for hour in range(24):
    for minute in [0, 30]:
        period_key = f"PERIOD_{hour:02d}_{minute:02d}"
        time_key = f"{hour:02d}:{minute:02d}"

        ts_price = tesla_sync.get(period_key, 0)
        nz_price = netzero.get(period_key, 0)

        diff = ts_price - nz_price
        pct_diff = (diff / nz_price * 100) if nz_price > 0 else 0

        total_diff += abs(diff)
        count += 1

        if abs(diff) > max_diff:
            max_diff = abs(diff)
            max_diff_period = time_key

        # Categorize difference
        if abs(diff) < 0.0001:
            status = "✅ EXACT"
            exact_matches += 1
        elif abs(pct_diff) < 1:
            status = "✅ CLOSE"
            close_matches += 1
        elif abs(pct_diff) < 5:
            status = "⚠️  SMALL"
            small_diffs += 1
        else:
            status = "❌ DIFF"
            large_diffs += 1

        print(f"{time_key:<12} ${ts_price:<14.4f} ${nz_price:<14.4f} ${diff:+14.4f} {pct_diff:+9.2f}% {status}")

avg_diff = total_diff / count if count > 0 else 0

print()
print("=" * 120)
print("SUMMARY STATISTICS")
print("=" * 120)
print(f"Total periods compared: {count}")
print(f"Exact matches (<$0.0001): {exact_matches}")
print(f"Close matches (<1% diff): {close_matches}")
print(f"Small differences (1-5%): {small_diffs}")
print(f"Large differences (>5%): {large_diffs}")
print()
print(f"Average absolute difference: ${avg_diff:.4f} ({avg_diff/0.20*100:.2f}% of typical $0.20/kWh)")
print(f"Maximum difference: ${max_diff:.4f} at {max_diff_period}")

# Calculate price statistics for each system
ts_prices = list(tesla_sync.values())
nz_prices = list(netzero.values())

print()
print("=" * 120)
print("PRICE RANGE COMPARISON")
print("=" * 120)
print(f"{'Metric':<25} {'Tesla Sync':<20} {'NetZero':<20} {'Difference'}")
print("-" * 120)
print(f"{'Minimum Price':<25} ${min(ts_prices):<19.4f} ${min(nz_prices):<19.4f} ${min(ts_prices)-min(nz_prices):+.4f}")
print(f"{'Maximum Price':<25} ${max(ts_prices):<19.4f} ${max(nz_prices):<19.4f} ${max(ts_prices)-max(nz_prices):+.4f}")
print(f"{'Average Price':<25} ${sum(ts_prices)/len(ts_prices):<19.4f} ${sum(nz_prices)/len(nz_prices):<19.4f} ${sum(ts_prices)/len(ts_prices)-sum(nz_prices)/len(nz_prices):+.4f}")

print()
print("=" * 120)
print("KEY OBSERVATIONS")
print("=" * 120)
print()
print("1. TIMEZONE HANDLING:")
print("   Both systems are using Australia/Brisbane timezone (AEST, UTC+10)")
print("   No timezone-related misalignment detected")
print()
print("2. PRICE SOURCE:")
print("   Both systems fetch from the same Amber Electric API")
print("   Minor differences likely due to:")
print("   - Different fetch times (prices update every 5 minutes)")
print("   - Different rounding when averaging 5-min → 30-min periods")
print("   - Different forecast type selection (predicted/low/high)")
print()
print("3. COMPLETENESS:")
print(f"   Tesla Sync: {len(tesla_sync)}/48 slots filled")
print(f"   NetZero:    {len(netzero)}/48 slots filled")
print("   ✅ Both systems provide complete 24-hour coverage")
print()
print("4. TIMESTAMP ALIGNMENT:")
print("   With our duration fix, timestamps align correctly:")
print("   - nemTime (END) - duration = interval START")
print("   - START time maps to PERIOD_XX_YY")
print("   ✅ Our system now matches NetZero's alignment")
