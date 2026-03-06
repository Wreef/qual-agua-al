import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh


st.set_page_config(page_title="Qualidade da Água - AL", layout="wide")

st.markdown("""
<style>

/* espaço superior */
.block-container {
    padding-top: 2rem;
}

/* fundo geral */
.stApp {
    background-color: #f7fbf7;
}

/* cartões */
[data-testid="stMetric"],
[data-testid="stExpander"],
[data-testid="stDataFrame"] {
    background-color: #ffffff;
    border: 1px solid #d9ead9;
    border-radius: 10px;
    padding: 10px;
}

/* títulos */
h1, h2, h3 {
    color: #2e7d32;
}

/* filtros selecionados (multiselect / selectbox) */
[data-baseweb="tag"] {
    background-color: #dff3e1 !important;
    color: #2e7d32 !important;
}

/* hover nos dropdowns */
[data-baseweb="select"] div:hover {
    background-color: #edf7ee;
}

/* sliders */
.stSlider > div > div > div > div {
    background-color: #81c784;
}

/* checkbox e radio */
input[type="checkbox"]:checked,
input[type="radio"]:checked {
    accent-color: #66bb6a;
}

</style>
""", unsafe_allow_html=True)

# Auto atualização a cada 300 segundos
st_autorefresh(interval=300000, key="auto_refresh")


# =========================
# CARGA DE DADOS
# =========================
@st.cache_data(ttl=300)
def carregar_dados() -> pd.DataFrame:
    url_google_sheet = "https://docs.google.com/spreadsheets/d/1_JoIoqNbFCX6QMkEPzVtQKG4H5PKNkjlDf361JoErUA/gviz/tq?tqx=out:csv&gid=1859408028"
    df = pd.read_csv(url_google_sheet)
    df = df.drop_duplicates().reset_index(drop=True)
    return df


# =========================
# FILTROS
# =========================
def aplicar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filtros")

    concessionarias = sorted(df["Sigla da Instituição"].dropna().unique().tolist())
    municipios = sorted(df["Município"].dropna().unique().tolist())
    anos = sorted(df["Ano de referência"].dropna().unique().tolist())
    meses = sorted(df["Mês de referência"].dropna().unique().tolist())

    filtro_concessionaria = st.sidebar.multiselect(
        "Concessionária",
        options=concessionarias,
        default=concessionarias,
        key="filtro_concessionaria",
    )

    filtro_municipio = st.sidebar.multiselect(
        "Município",
        options=municipios,
        default=municipios,
        key="filtro_municipio",
    )

    filtro_ano = st.sidebar.multiselect(
        "Ano",
        options=anos,
        default=[max(anos)] if anos else [],
        key="filtro_ano",
    )

    filtro_mes = st.sidebar.multiselect(
        "Mês",
        options=meses,
        default=meses,
        key="filtro_mes",
    )

    df_filtrado = df[
        df["Sigla da Instituição"].isin(filtro_concessionaria)
        & df["Município"].isin(filtro_municipio)
        & df["Ano de referência"].isin(filtro_ano)
        & df["Mês de referência"].isin(filtro_mes)
    ].copy()

    return df_filtrado


# =========================
# LAYOUT
# =========================
st.title("Monitoramento da Qualidade da Água em Alagoas")
st.caption("SISAGUA")

df = carregar_dados()
df_filtrado = aplicar_filtros(df)

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()


# =========================
# CARTÕES
# =========================
valor_total = df_filtrado["Valor"].sum()
ok_total = df_filtrado["OK"].sum()

iqa = round(ok_total * 100 / valor_total, 2) if valor_total > 0 else 0
amostras_totais = int(valor_total)

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.metric(
            label="Índice de Qualidade da Água",
            value=f"{iqa:.2f}%"
        )

with col2:
    with st.container(border=True):
        st.metric(
            label="Amostras Totais",
            value=f"{amostras_totais:,}".replace(",", ".")
        )


# =========================
# PREPARAÇÃO DO GRÁFICO DE LINHA
# =========================
linha_df = (
    df_filtrado.groupby(["Ano de referência", "Mês de referência"], as_index=False)
    .agg(
        OK=("OK", "sum"),
        Valor=("Valor", "sum"),
    )
    .sort_values(["Ano de referência", "Mês de referência"])
)

linha_df["Percentual"] = linha_df.apply(
    lambda row: round(row["OK"] * 100 / row["Valor"], 2) if row["Valor"] > 0 else 0,
    axis=1,
)

linha_df["Periodo"] = (
    linha_df["Ano de referência"].astype(str)
    + "-"
    + linha_df["Mês de referência"].astype(str).str.zfill(2)
)

# =========================
# PREPARAÇÃO DO GRÁFICO DE BARRAS
# =========================
barra_df = (
    df_filtrado.groupby(["Parâmetro", "Status"], as_index=False)
    .agg(
        Valor=("Valor", "sum"),
    )
)

# Calcular percentual dentro de cada parâmetro
barra_df["Percentual"] = (
    barra_df["Valor"]
    / barra_df.groupby("Parâmetro")["Valor"].transform("sum")
    * 100
).round(2)

# =========================
# PREPARAÇÃO DO GRÁFICO DE ROSCA
# =========================
rosca_df = (
    df_filtrado.groupby("Status", as_index=False)
    .agg(
        Valor=("Valor", "sum")
    )
)

# =========================
# GRÁFICO DE LINHA
# =========================
fig_linha = px.line(
    linha_df,
    x="Periodo",
    y="Percentual",
    markers=True,
    title="Evolução Mensal do IQA",
)

fig_linha.update_layout(
    height=420,
    yaxis_title="IQA (%)",
    xaxis_title="Mês",
)

# =========================
# GRÁFICO DE BARRAS
# =========================
fig_barra = px.bar(
    barra_df,
    x="Percentual",
    y="Parâmetro",
    color="Status",
    orientation="h",
    title="Status das Análises por Parâmetro em Relação aos Limites (%)",
    category_orders={
        "Status": [
            "Dentro do Limite",
            "Abaixo do Limite",
            "Regra não encontrada",
            "Acima do Limite",
        ]
    },
    color_discrete_map={
        "Dentro do Limite": "#2ca02c",
        "Abaixo do Limite": "#ffcc00",
        "Regra não encontrada": "#7f7f7f",
        "Acima do Limite": "#d62728",
    },
)

fig_barra.update_layout(
    height=420,
    xaxis_title="Percentual (%)",
    yaxis_title="Parâmetro",
    barmode="stack",
)

# =========================
# GRÁFICO DE ROSCA
# =========================
fig_rosca = px.pie(
    rosca_df,
    names="Status",
    values="Valor",
    title="Situação das Amostras em Relação aos Limites de Qualidade",
    color="Status",
    color_discrete_map={
        "Dentro do Limite": "#2ca02c",
        "Abaixo do Limite": "#ffcc00",
        "Regra não encontrada": "#7f7f7f",
        "Acima do Limite": "#d62728",
    },
)

fig_rosca.update_traces(textposition="inside", textinfo="percent+label")
fig_rosca.update_layout(height=420)

# =========================
# EXIBIÇÃO DOS 3 GRÁFICOS LADO A LADO
# =========================
col_graf1, col_graf2, col_graf3 = st.columns([1, 1.2, 1])

with col_graf1:
    st.plotly_chart(fig_linha, use_container_width=True)

with col_graf2:
    st.plotly_chart(fig_barra, use_container_width=True)

with col_graf3:
    st.plotly_chart(fig_rosca, use_container_width=True)


# =========================
# TABELA OPCIONAL
# =========================

colunas = ["Sigla da Instituição",
           "Ano de referência", 
           "Mês de referência", 
           "Nome da Forma de Abastecimento",
           "Ponto de Monitoramento",
           "Parâmetro",
           "Campo",
           "Valor",
           "Status"]

# ordenar
df_tabela = df_filtrado.sort_values(
    by=["Ano de referência", "Mês de referência"],
    ascending=[False, False]
)

with st.expander("Tabela de Dados"):
    st.dataframe(
        df_tabela[colunas],
        column_config={
            "Sigla da Instituição": "Concessionária",
            "Ano de referência": "Ano",
            "Mês de referência": "Mês",
            "Nome da Forma de Abastecimento": "Forma de Abastecimento",
        },
        use_container_width=True
    )