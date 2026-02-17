import pandas as pd
import numpy as np
from typing import Dict, List
import logging
import os

# Suppress heavy logs
logging.getLogger("pytorch_lightning").setLevel(logging.WARNING)

from neuralforecast import NeuralForecast
from neuralforecast.models import NHITS, NBEATS
from datetime import datetime, timedelta

class ForecastingService:
    def __init__(self):
        self.horizon = 192 # 48 hours * 4
        # Pre-instantiate models if possible to save time per run
        self.models = [
            NHITS(h=self.horizon, input_size=96, max_steps=100)
        ]
        self.nf = NeuralForecast(models=self.models, freq='15T')

    def forecast(self, df_history: pd.DataFrame, target_col: str = 'y') -> pd.Series:
        """
        Generic forecaster using N-HiTS.
        Input: DataFrame with index=Timestamp, col=[target_col]
        """
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
