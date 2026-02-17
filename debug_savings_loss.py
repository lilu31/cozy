from sqlmodel import Session, select
from datetime import datetime, timedelta
from backend.database import engine
from backend.models import MeterReading, MarketPrice, Asset, AssetType

def analyze_savings():
    with Session(engine) as session:
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        start = now - timedelta(hours=48)
        
        print(f"Analyzing Window: {start} to {now}")
        
        # Fetch Data
        readings = session.exec(select(MeterReading).where(
            MeterReading.timestamp >= start,
            MeterReading.timestamp < now
        ).order_by(MeterReading.timestamp)).all()
        
        prices = session.exec(select(MarketPrice).where(
            MarketPrice.timestamp >= start,
            MarketPrice.timestamp < now
        )).all()
        price_map = {p.timestamp: p.price_eur_per_mwh / 1000.0 for p in prices}
        
        # Aggregate
        total_real_cost = 0.0
        total_benchmark_cost = 0.0
        
        total_pv = 0.0
        total_bat_charge = 0.0
        total_bat_discharge = 0.0
        total_lost_export_revenue = 0.0
        
        # Group by TS
        data_map = {}
        for r in readings:
            if r.timestamp not in data_map: data_map[r.timestamp] = {'pv':0,'bat':0}
            asset = session.get(Asset, r.asset_id)
            if not asset: continue
            if asset.asset_type == AssetType.PV: data_map[r.timestamp]['pv'] += r.power_kw
            elif asset.asset_type == AssetType.BATTERY: data_map[r.timestamp]['bat'] += r.power_kw
            
        sorted_ts = sorted(list(data_map.keys()))
        
        for ts in sorted_ts:
            vals = data_map[ts]
            pv = vals['pv']
            bat = vals['bat'] # >0 Discharge, <0 Charge
            load = 0.5
            price = price_map.get(ts, 0.30)
            
            # Real
            real_grid = load - pv - bat
            real_cost = real_grid * 0.25 * price
            total_real_cost += real_cost
            
            # Benchmark
            bench_grid = load - pv
            bench_cost = bench_grid * 0.25 * price
            total_benchmark_cost += bench_cost
            
            # Analysis
            total_pv += pv * 0.25
            if bat > 0: total_bat_discharge += bat * 0.25
            if bat < 0: total_bat_charge += abs(bat) * 0.25
            
            # Export Revenue Comparison
            # If Benchmark exports (Grid < 0), it earns money.
            # If Optimized stores instead (Real Grid > Bench Grid), it earns LESS money.
            diff = bench_cost - real_cost
            # If diff > 0, Benchmark cost was higher (we saved money).
            # If diff < 0, Benchmark cost was lower (we lost money).
            
        savings = total_benchmark_cost - total_real_cost
        
        print(f"\n--- Results ---")
        print(f"Total PV Generation: {total_pv:.2f} kWh")
        print(f"Total Battery Charge: {total_bat_charge:.2f} kWh")
        print(f"Total Battery Discharge: {total_bat_discharge:.2f} kWh")
        print(f"Net Stored Energy (Delta): {total_bat_charge - total_bat_discharge:.2f} kWh")
        
        print(f"\nBenchmark Cost (Net): €{total_benchmark_cost:.2f} (Negative = Profit)")
        print(f"Real Cost (Net):      €{total_real_cost:.2f}")
        print(f"Cash Flow Savings:    €{savings:.2f}")
        
        # Estimate Value of Stored Energy
        # Assuming avg price of last 48h or current price
        avg_price = sum(price_map.values()) / len(price_map) if price_map else 0.30
        stored_value = (total_bat_charge - total_bat_discharge) * avg_price
        
        print(f"\nEst. Value of Net Stored Energy: €{stored_value:.2f} (at avg price €{avg_price:.2f}/kWh)")
        print(f"Total Economic Savings: €{savings + stored_value:.2f}")

if __name__ == "__main__":
    analyze_savings()
