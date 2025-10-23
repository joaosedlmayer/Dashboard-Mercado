# -*- coding: utf-8 -*-
"""
Created on Thu Oct 23 14:44:04 2025

@author: joaos
"""

import pyettj.ettj 
import datetime as dt 
import pandas as pd 
import yfinance as yf 
import streamlit as st
import altair as alt

st.set_page_config(layout="wide")
st.title("Dashboard de Mercado Financeiro")

ticker_names = {
    '^BVSP': 'Ibovespa', '^GSPC': 'S&P 500', '^IXIC': 'NASDAQ', '^FCHI': 'CAC 40 (França)',
    '^FTSE': 'FTSE 100 (UK)', '^GDAXI': 'DAX (Alemanha)', '^N225': 'Nikkei (Japão)',
    '^HSI': 'Hang Seng (Hong Kong)', '^GSPTSE': 'S&P/TSX (Canadá)', '^AXJO': 'ASX 200 (Austrália)',
    '^NSEI': 'NIFTY 50 (Índia)', '000001.SS': 'Shanghai Composite',
    
    'BRL=X': 'Dólar (USD/BRL)', 'EURBRL=X': 'Euro (EUR/BRL)', 'GBPBRL=X': 'Libra (GBP/BRL)',
    'JPYBRL=X': 'Iene (JPY/BRL)', 'AUDBRL=X': 'Dólar Aus. (AUD/BRL)', 'CADBRL=X': 'Dólar Can. (CAD/BRL)',
    'CHFBRL=X': 'Franco Suíço (CHF/BRL)', 'CNYBRL=X': 'Yuan Chinês (CNY/BRL)',
    
    'DBC': 'Invesco DB Commodity Index', 'GSG': 'iShares S&P GSCI Commodity', 'BDRY': 'Baltic Dry Index (ETF)',
    
    'LE=F': 'Boi Gordo (Live Cattle)', 'HE=F': 'Suíno (Lean Hogs)', 'CC=F': 'Cacau', 'KC=F': 'Café',
    'ZC=F': 'Milho (Corn)', 'CT=F': 'Algodão (Cotton)', 'OJ=F': 'Suco de Laranja',
    'ZS=F': 'Soja (Soybeans)', 'SB=F': 'Açúcar (Sugar)', 'ZW=F': 'Trigo (Wheat)',
    
    'GC=F': 'Ouro (Gold)', 'SI=F': 'Prata (Silver)', 'HG=F': 'Cobre (Copper)', 'JJU': 'Alumínio (ETN)',
    'PA=F': 'Paládio (Palladium)',
    
    'CL=F': 'Petróleo (WTI)', 'BZ=F': 'Petróleo (Brent)', 'NG=F': 'Gás Natural (US)',
    'HO=F': 'Óleo de Aquecimento', 'RB=F': 'Gasolina (RBOB)', 'TTF=F': 'Gás Natural (Holanda TTF)',
    'EH=F': 'Etanol',
    
    'BTC-USD': 'Bitcoin (USD)', 'ETH-USD': 'Ethereum (USD)',
    'BTC-BRL': 'Bitcoin (BRL)', 'ETH-BRL': 'Ethereum (BRL)'
}

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
def get_mercado_data(ticker_map):
    tickers = {
        'Bolsas': [
            '^BVSP', '^GSPC', '^IXIC', '^FCHI', '^FTSE', '^GDAXI', '^N225', 
            '^HSI', '^GSPTSE', '^AXJO', '^NSEI', '000001.SS'
        ],
        'Moedas_em_BRL': [
            'BRL=X', 'EURBRL=X', 'GBPBRL=X', 'JPYBRL=X', 'AUDBRL=X', 
            'CADBRL=X', 'CHFBRL=X', 'CNY=X'
        ],
        'Commodity_Indices': ['DBC', 'GSG', 'BDRY'],
        'Commodity_Agricolas': [
            'LE=F', 'HE=F', 'CC=F', 'KC=F', 'ZC=F', 'CT=F', 'OJ=F', 
            'ZS=F', 'SB=F', 'ZW=F'
        ],
        'Commodity_Metais': ['GC=F', 'SI=F', 'HG=F', 'JJU', 'PA=F'],
        'Commodity_Energia': [
            'CL=F', 'BZ=F', 'NG=F', 'HO=F', 'RB=F', 'TTF=F', 'EH=F'
        ],
        'Crypto_USD': ['BTC-USD', 'ETH-USD']
    }

    all_tickers = [ticker for group in tickers.values() for ticker in group]

    data_fim = dt.date.today()
    data_inicio = data_fim - dt.timedelta(days=365)
    data_fim_download = data_fim + dt.timedelta(days=1)

    raw_data = yf.download(all_tickers, start=data_inicio, end=data_fim_download)

    data_diaria = raw_data['Close']
    data_diaria = data_diaria.ffill()
    data_diaria = data_diaria.dropna(how='all')

    dataframes_mercado_renomeados = {}
    performance_list = []
    
    grupos_para_iterar = list(tickers.keys())
    
    dataframes_mercado_orig = {}
    for group_name, group_tickers in tickers.items():
        available_tickers = [t for t in group_tickers if t in data_diaria.columns]
        if available_tickers:
            dataframes_mercado_orig[group_name] = data_diaria[available_tickers].copy()

    if 'Moedas_em_BRL' in dataframes_mercado_orig:
        df_moedas = dataframes_mercado_orig['Moedas_em_BRL']
        if 'BRL=X' in df_moedas.columns and 'CNY=X' in df_moedas.columns:
            df_moedas['CNYBRL=X'] = df_moedas['BRL=X'] / df_moedas['CNY=X']
            df_moedas.drop(columns=['CNY=X'], inplace=True)

    if ('Moedas_em_BRL' in dataframes_mercado_orig and 
        'Crypto_USD' in dataframes_mercado_orig and 
        'BRL=X' in dataframes_mercado_orig['Moedas_em_BRL'].columns):
        
        dolar_brl = dataframes_mercado_orig['Moedas_em_BRL']['BRL=X']
        crypto_usd = dataframes_mercado_orig['Crypto_USD']
        crypto_brl = crypto_usd.multiply(dolar_brl, axis=0)
        
        crypto_brl = crypto_brl.rename(columns={'BTC-USD': 'BTC-BRL', 'ETH-USD': 'ETH-BRL'})
        
        dataframes_mercado_orig['Crypto_BRL'] = crypto_brl
        grupos_para_iterar.append('Crypto_BRL')
        grupos_para_iterar.remove('Crypto_USD')

    for group_name in grupos_para_iterar:
        df = dataframes_mercado_orig[group_name]
        
        df_renomeado = df.rename(columns=ticker_map)
        dataframes_mercado_renomeados[group_name] = df_renomeado
        
        today = df.index[-1]
        last = df.iloc[-1]
        
        yoy_price = df.iloc[0]
        mom_price = df.asof(today - pd.DateOffset(months=1))
        ytd_price = df.asof(f"{today.year}-01-01")
        mtd_price = df.asof(today.replace(day=1))
        
        perf = pd.DataFrame({'Último': last})
        perf['YoY %'] = (last / yoy_price) - 1
        perf['MoM %'] = (last / mom_price) - 1
        perf['YTD %'] = (last / ytd_price) - 1
        perf['MTD %'] = (last / mtd_price) - 1
        
        if group_name == 'Moedas_em_BRL' or group_name == 'Crypto_BRL':
            perf_cols = ['YoY %', 'MoM %', 'YTD %', 'MTD %']
            perf[perf_cols] = perf[perf_cols] * -1
        
        perf['Grupo'] = group_name
        performance_list.append(perf)

    performance_table = pd.concat(performance_list)
    performance_table.index.name = "Ativo"
    
    performance_table = performance_table.rename(index=ticker_map)
    
    return dataframes_mercado_renomeados, performance_table

try:
    dfs_por_curva = get_ettj_data()
    dataframes_mercado, performance_table = get_mercado_data(ticker_names)

    st.header("Principais Curvas de Juros (ETTJ)")
    st.write("Evolução da curva em 3 datas (Ontem, Semana Passada, Mês Passado)")
    
    curvas_principais = ['DI x pré 252', 'DI x IPCA 252', 'DI x dólar 360']
    
    curvas_filtradas = {
        nome: df for nome, df in dfs_por_curva.items() 
        if nome in curvas_principais
    }
    
    for nome_curva, df_curva_original in curvas_filtradas.items():
        st.subheader(nome_curva)
        
        df_filtrado = df_curva_original.loc[df_curva_original.index <= 2520].copy()
        df_interpolado = df_filtrado.interpolate(method='linear', limit_direction='both')
        
        df_long_para_plotar = df_interpolado.reset_index().melt(
            id_vars='Dias Corridos', 
            var_name='Data', 
            value_name='Taxa'
        )
        
        chart = alt.Chart(df_long_para_plotar).mark_line().encode(
            x=alt.X('Dias Corridos'), 
            y=alt.Y('Taxa', scale=alt.Scale(zero=False)),
            color='Data',
            tooltip=['Data', 'Dias Corridos', 'Taxa']
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)

    st.header("Performance Recente")
    
    formatters = {
        'Último': '{:,.2f}',
        'YoY %': '{:,.2%}',
        'MoM %': '{:,.2%}',
        'YTD %': '{:,.2%}',
        'MTD %': '{:,.2%}'
    }
    
    grupos_performance = performance_table['Grupo'].unique()
    for group in grupos_performance:
        st.subheader(group.replace("_", " "))
        
        df_to_show = performance_table[
            performance_table['Grupo'] == group
        ].drop(columns=['Grupo'])
        
        st.dataframe(
            df_to_show.style.format(formatters), 
            use_container_width=True
        )

    st.header("Mercados Globais (YFinance - Último Ano)")

    for assunto, df_mercado in dataframes_mercado.items():
        st.subheader(assunto.replace("_", " "))
        
        lista_de_ativos = df_mercado.columns
        
        if len(lista_de_ativos) > 0:
            ativo_selecionado = st.selectbox(
                f"Selecione o ativo ({assunto.replace('_', ' ')}):",
                lista_de_ativos,
                key=assunto 
            )
            
            if ativo_selecionado:
                st.line_chart(df_mercado[ativo_selecionado])
        else:
            st.write(f"Nenhum dado encontrado para {assunto}.")

except Exception as e:
    st.error(f"Ocorreu um erro ao carregar os dados: {e}")
    st.exception(e)
