# economic_calendar.py

import investpy
import pandas as pd
from datetime import datetime

def get_economic_calendar(start_date: str, end_date: str):
    """
    Obtiene los eventos del calendario económico y los devuelve en un orden consistente.
    """
    print("--- Obteniendo datos del calendario con investpy ---")
    
    try:
        start_date_investpy = datetime.strptime(start_date, '%Y-%m-%d').strftime('%d/%m/%Y')
        end_date_investpy = datetime.strptime(end_date, '%Y-%m-%d').strftime('%d/%m/%Y')

        countries = [
            'united states', 'euro zone', 'japan', 'united kingdom', 
            'germany', 'france', 'italy', 'spain',
            'canada', 'australia', 'new zealand', 'switzerland', 'china'
        ]

        df = investpy.economic_calendar(
            countries=countries,
            from_date=start_date_investpy,
            to_date=end_date_investpy
        )

        if df.empty:
            return pd.DataFrame()

        # --- CAMBIO CLAVE: Asegurar un orden consistente ---
        # Ordenamos el DataFrame por varias columnas para garantizar que .equals() funcione
        df = df.sort_values(by=['date', 'time', 'zone', 'event']).reset_index(drop=True)
        # --- FIN DEL CAMBIO ---

        df['time'] = df['time'].replace('All Day', '00:00')
        datetime_combined = df['date'] + ' ' + df['time']
        df['Fecha y Hora'] = pd.to_datetime(datetime_combined, format='%d/%m/%Y %H:%M', errors='coerce')
        df.dropna(subset=['Fecha y Hora'], inplace=True)
        
        impact_map = {'low': 'low', 'medium': 'medium', 'high': 'high'}
        df['Impacto'] = df['importance'].map(impact_map).fillna('low')

        columnas_map = {
            'zone': 'País', 'event': 'Evento', 'actual': 'Actual',
            'forecast': 'Consenso', 'previous': 'Previo'
        }
        df.rename(columns=columnas_map, inplace=True)
        
        columnas_finales = ['Fecha y Hora', 'País', 'Evento', 'Impacto', 'Actual', 'Consenso', 'Previo']
        for col in columnas_finales:
            if col not in df.columns: df[col] = ''
        df = df[columnas_finales]

        df.fillna('', inplace=True)
        
        print(f"--- Se procesaron {len(df)} eventos con éxito. ---")
        return df.sort_values(by='Fecha y Hora', ascending=True)

    except Exception as e:
        print(f"!!! Error al obtener datos con investpy: {e}")
        return pd.DataFrame()