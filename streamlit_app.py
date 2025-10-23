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

    raw_data = yf.download(
        all_tickers, 
        start=data_inicio, 
        end=data_fim_download
    )

    data_diaria = raw_data['Close']
    data_diaria = data_diaria.ffill()
    data_diaria = data_diaria.dropna(how='all')

    dataframes_mercado = {}
    for group_name, group_tickers in tickers.items():
        available_tickers = [t for t in group_tickers if t in data_diaria.columns]
        if available_tickers:
            dataframes_mercado[group_name] = data_diaria[available_tickers].copy()

    if 'Moedas_em_BRL' in dataframes_mercado:
        df_moedas = dataframes_mercado['Moedas_em_BRL']
        if 'BRL=X' in df_moedas.columns and 'CNY=X' in df_moedas.columns:
            df_moedas['CNYBRL=X'] = df_moedas['BRL=X'] / df_moedas['CNY=X']
            df_moedas.drop(columns=['CNY=X'], inplace=True)

    if ('Moedas_em_BRL' in dataframes_mercado and 
        'Crypto_USD' in dataframes_mercado and 
        'BRL=X' in dataframes_mercado['Moedas_em_BRL'].columns):
        
        dolar_brl = dataframes_mercado['Moedas_em_BRL']['BRL=X']
        crypto_usd = dataframes_mercado['Crypto_USD']
        
        crypto_brl = crypto_usd.multiply(dolar_brl, axis=0)
        
        crypto_brl = crypto_brl.rename(columns={
            'BTC-USD': 'BTC-BRL',
            'ETH-USD': 'ETH-BRL'
        })
        
        dataframes_mercado['Crypto_BRL'] = crypto_brl
        del dataframes_mercado['Crypto_USD']
    
    return dataframes_mercado


try:
    dfs_por_curva = get_ettj_data()
    dataframes_mercado = get_mercado_data()

    # --- SEÇÃO 1: CURVAS DE JUROS ---
    st.header("Curvas de Juros (ETTJ)")
    st.write("Evolução da curva em 3 datas (Ontem, Semana Passada, Mês Passado)")
    
    for nome_curva, df_curva in dfs_por_curva.items():
        st.subheader(nome_curva)
        st.line_chart(df_curva)

    # --- SEÇÃO 2: MERCADOS GLOBAIS ---
    st.header("Mercados Globais (YFinance - Último Ano)")

    for assunto, df_mercado in dataframes_mercado.items():
        st.subheader(assunto)
        
        # Pega a lista de colunas (ativos) para o selectbox
        lista_de_ativos = df_mercado.columns
        
        if len(lista_de_ativos) > 0:
            # Cria o "botão de seleção" (selectbox)
            ativo_selecionado = st.selectbox(
                f"Selecione o ativo ({assunto}):",
                lista_de_ativos,
                key=assunto # Chave única para cada selectbox
            )
            
            # Plota o gráfico da coluna selecionada
            if ativo_selecionado:
                st.line_chart(df_mercado[ativo_selecionado])
        else:
            st.write(f"Nenhum dado encontrado para {assunto}.")

except Exception as e:
    st.error(f"Ocorreu um erro ao carregar os dados: {e}")
    st.write("Verifique sua conexão com a internet ou as bibliotecas pyettj/yfinance.")