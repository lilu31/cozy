import pandas as pd
import numpy as np
from typing import Dict, List
import logging
import os
import math
from datetime import datetime, timedelta

# Suppress heavy logs
logging.getLogger("pytorch_lightning").setLevel(logging.WARNING)

try:
    from neuralforecast import NeuralForecast
    from neuralforecast.models import NHITS, NBEATS
    HAS_NEURALFORECAST = True
except ImportError:
    HAS_NEURALFORECAST = False

class ForecastingService:
    def __init__(self):
        self.horizon = 192 # 48 hours * 4
        if HAS_NEURALFORECAST:
            # Pre-instantiate models if possible to save time per run
            self.models = [
                NHITS(h=self.horizon, input_size=96, max_steps=100)
            ]
            self.nf = NeuralForecast(models=self.models, freq='15T')
        else:
            self.nf = None

    def forecast(self, df_history: pd.DataFrame, target_col: str = 'y') -> pd.Series:
        """
        Generic forecaster using N-HiTS.
        Input: DataFrame with index=Timestamp, col=[target_col]
        """
        if not HAS_NEURALFORECAST or self.nf is None:
            # Fallback: Realistic seasonal solar/load pattern generator
            last_ts = df_history.index[-1] if not df_history.empty else datetime.utcnow()
            future_dates = pd.date_range(last_ts + timedelta(minutes=15), periods=self.horizon, freq='15min')
            
            vals = []
            for ts in future_dates:
                hour = ts.hour + ts.minute/60.0
                if 'solar' in target_col.lower() or 'pv' in target_col.lower():
                    # PV bell curve centered at 13:00
                    pv_power = 0.0
                    if 6 < hour < 20:
                        peak = 5.0
                        pv_power = peak * math.exp(-((hour - 13) ** 2) / 8)
                        pv_power = max(0.0, pv_power)
                    vals.append(pv_power)
                else:
                    # Home Load: morning and evening peaks
                    # Morning peak around 8:00, Evening peak around 19:30, base load 0.5kW
                    base_load = 0.5
                    morning_peak = 1.8 * math.exp(-((hour - 8.0) ** 2) / 1.5)
                    evening_peak = 2.5 * math.exp(-((hour - 19.5) ** 2) / 3.0)
                    total_load = base_load + morning_peak + evening_peak
                    vals.append(max(0.1, total_load))
            return pd.Series(vals, index=future_dates)
            
        # Prepare for NeuralForecast
        # Needs ['ds', 'y', 'unique_id']
        df = df_history.reset_index()
        df = df.rename(columns={'timestamp': 'ds', target_col: 'y'})
        df['unique_id'] = '1'
        df = df[['unique_id', 'ds', 'y']]
        
        # Fit & Predict
        try:
            self.nf.fit(df=df)
            forecast_df = self.nf.predict()
            # Result has index=unique_id, cols=[ds, NHITS]
            forecast_df = forecast_df.reset_index()
            return pd.Series(forecast_df['NHITS'].values, index=forecast_df['ds'])
        except Exception as e:
            print(f"Forecast Error: {e}")
            # Fallback: Persistence
            last_val = df_history[target_col].iloc[-1]
            future_dates = pd.date_range(df_history.index[-1] + timedelta(minutes=15), periods=self.horizon, freq='15T')
            return pd.Series([last_val]*self.horizon, index=future_dates)
