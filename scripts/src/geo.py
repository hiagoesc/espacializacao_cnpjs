"""Apoio a dados geográficos: tipos compatíveis com GeoPackage, conferência de CRS e distâncias."""
import numpy as np
import pandas as pd


def para_gpkg(df):
    """Converte colunas do pandas "novas" (string, Int32, boolean...) para tipos que o GeoPackage aceita.

    Inteiros sem nulos continuam inteiros (ano 2025, não 2025.0); com nulos viram decimais.
    Verdadeiro/falso vira 1/0. A geometria não é alterada.
    """
    out = df.copy()
    for col in out.columns:
        if col == "geometry":
            continue
        tipo = out[col].dtype
        if pd.api.types.is_bool_dtype(tipo):
            out[col] = out[col].astype("int8")
        elif pd.api.types.is_integer_dtype(tipo):
            out[col] = out[col].astype("int64") if not out[col].isna().any() else out[col].astype("float64")
        elif pd.api.types.is_numeric_dtype(tipo):
            out[col] = out[col].astype("float64")
        elif not pd.api.types.is_object_dtype(tipo):
            out[col] = out[col].astype(object).where(out[col].notna(), None)
    return out


def checar_crs(gdf, esperado: str, nome: str = "camada"):
    """Para com erro claro se o CRS da camada não for o esperado (ex.: 'EPSG:31983')."""
    atual = gdf.crs.to_string() if gdf.crs is not None else None
    if atual != esperado:
        raise ValueError(f"CRS inesperado em {nome}: {atual} (esperado {esperado})")


def distancia_metros(lat1, lon1, lat2, lon2):
    """
    Calcula a distância em metros, em linha reta sobre a superfície da Terra,
    entre dois pontos dados por latitude e longitude (fórmula de haversine).
    Funciona com colunas inteiras de uma vez.
    """
    # Raio médio da Terra, em metros.
    raio = 6_371_000
    # As funções de seno e cosseno precisam dos ângulos em radianos, não em graus.
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    # Diferença de latitude e de longitude entre os dois pontos.
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    # Fórmula de haversine: calcula a "abertura" do arco entre os dois pontos.
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    # Transforma o arco em distância em metros.
    return 2 * raio * np.arcsin(np.sqrt(a))
