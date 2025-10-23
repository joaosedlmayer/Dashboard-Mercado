# -*- coding: utf-8 -*-
"""
Created on Thu Oct 23 14:44:04 2025

@author: joaos
"""
import pyettj.ettj as ettj 
import datetime as dt 
import pandas as pd 
import yfinance as yf 
import streamlit as st

st.set_page_config(layout="wide")
st.title("Dashboard de Mercado Financeiro")

# --- FUNÇÃO CACHEADA PARA DADOS ETTJ ---
@st.cache_data
def get_ettj_data():
    hoje = dt.date.today()
    ontem = hoje - dt.timedelta(days=1)
    semana_passada = ontem - dt.timedelta(days=7) 
    mes_passado = ontem - dt.timedelta(days=30) 

    target_dates_dt = pd.to_datetime([ontem, semana_passada, mes_passado])

    data_inicio_str = (mes_passado - dt.timedelta(days=5)).strftime("%d/%m/%Y")
    data_fim_str = (hoje + dt.timedelta(days=5)).strftime("%d/%m/%Y")

    datas_uteis_str = ettj.listar_dias_uteis(data_inicio_str, data_fim_str)
    datas_uteis_idx = pd.to_datetime(datas_uteis_str) 

    indices = datas_uteis_idx.get_indexer(target_dates_dt, method='bfill')
    datas_para_request_dt = datas_uteis_idx[indices]

    datas_para_request = [d.strftime("%d/%m/%Y") for d in datas_para_request_dt]

    curvas_ettj = {}
    for data_req in datas_para_request:
        dados = ettj.get_ettj(data_req)
        curvas_ettj[data_req] = dados

    master_df_wide = pd.concat(curvas_ettj.values(), ignore_index=True)

    id_cols = ['Data', 'Dias Corridos']
    value_cols = [col for col in master_df_wide.columns if col not in id_cols]

    master_df_long = master_df_wide.melt(
        id_vars=id_cols,
        value_vars=value_cols,
        var_name='Curva',
        value_name='Taxa'
    )

    dfs_por_curva = {}

    datas_ordenadas = sorted(
        curvas_ettj.keys(), 
        key=lambda d: pd.to_datetime(d, format='%d/%m/%Y'), 
        reverse=True
    )

    for nome_curva, group_df in master_df_long.groupby('Curva'):
        pivot_df = group_df.pivot_table(index='Dias Corridos', 
                                        columns='Data', 
                                        values='Taxa')

        colunas_presentes_ordenadas = [d for d in datas_ordenadas if d in pivot_df.columns]
        pivot_df = pivot_df[colunas_presentes_ordenadas]
        
        dfs_por_curva[nome_curva] = pivot_df
    
    return dfs_por_curva

# --- FUNÇÃO CACHEADA PARA DADOS YFINANCE ---
@st.cache_data
def get_mercado_data():
    tickers = {
        'Bolsas': [
            '^BVSP', '^GSPC', '^IXIC', '^FCHI', '^FTSE', '^GDAXI', '^N225', 
            '^HSI', '^GSPTSE', '^AXJO', '^NSEI', '000001.SS'
        ],
        'Moedas_em_BRL': [
            'BRL=X',    # USD/BRL
            'EURBRL=X', # EUR/BRL
            'GBPBRL=X', # GBP/BRL
            'JPYBRL=X', # JPY/BRL
            'AUDBRL=X', # AUD/BRL
            'CADBRL=X', # CAD/BRL
            'CHFBRL=X', # CHF/BRL
            'CNY=X'     # Baixa USD/CNY para calcular
        ],
        'Commodity_Indices': [
            'DBC', 'GSG', 'BDRY'
        ],
        'Commodity_Agricolas': [
            'LE=F', 'HE=F', 'CC=F', 'KC=F', 'ZC=F', 'CT=F', 'OJ=F', 
            'ZS=F', 'SB=F', 'ZW=F'
        ],
        'Commodity_Metais': [
            'GC=F', 'SI=F', 'HG=F', 'JJU', 'PA=F'
        ],
        'Commodity_Energia': [
            'CL=F', 'BZ=F', 'NG=F', 'HO=F', 'RB=F', 'TTF=F', 'EH=F'
        ],
        'Crypto_USD': [
            'BTC-USD', 'ETH-USD'
        ]
    }

    all_tickers = [ticker for group in tickers.values() for ticker in group]

    data_fim = dt.date.today()
    data_inicio = data_fim - dt.timedelta(days=365)
    data_fim_download = data_fim + dt.timedelta(days=1)

    raw_data = y
