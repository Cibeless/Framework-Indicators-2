
# =========================
# app3.py - Smart Green Innovation Indicators (App3)
# Versão com Plotly (sem matplotlib) e mapeamento PT ↔ EN
# =========================

import streamlit as st
import pandas as pd
import datetime
import os
import unicodedata
import re
import difflib
import plotly.express as px

# =========================
# CONFIGURAÇÕES GERAIS
# =========================
st.set_page_config(
    page_title="Smart Green Innovation Indicators - App3",
    layout="wide"
)

BRAND_PRIMARY = "#184868"   # azul petróleo
BRAND_SECONDARY = "#6a9739" # verde oliva
BRAND_ACCENT = "#f0b323"    # amarelo suave

# Caminhos dos arquivos (ajuste se necessário no seu ambiente local)
PATH_INO_TAGS = r"C:\Users\User\Formulario3\InoDescTagsEng.xlsx"
PATH_IND_META = r"C:\Users\User\Formulario3\IndDescMensCat.xlsx"
PATH_LINK_INV_IND = r"C:\Users\User\Formulario3\Inovação_Ind.xlsx"
PATH_IND_REF = r"C:\Users\User\Formulario3\indicadores_classificados_114.xlsx"
RESULTS_FILE = r"C:\Users\User\Formulario3\Resultados_Inovacoes.xlsx"

# Logos
LOGO_CETRAD = r"C:\Users\User\Formulario3\cetrad.png"
LOGO_VINEWINE = r"C:\Users\User\Formulario3\vinewine.png"

# =========================
# ESTILO (CSS)
# =========================
st.markdown(
    f"""
<style>
    .stApp {{
        background: #f5f6fa;
        color: #2c3e50;
        font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Roboto", sans-serif;
    }}
    h1, h2, h3, h4 {{
        color: {BRAND_PRIMARY};
        font-weight: 600;
    }}
    .big-title {{
        font-size: 2.6rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        color: {BRAND_PRIMARY};
        margin-bottom: 0.3rem;
    }}
    .subtitle {{
        font-size: 1.2rem;
        color: {BRAND_SECONDARY};
        margin-bottom: 0.4rem;
    }}
    .subtext {{
        font-size: 1.0rem;
        color: #555555;
        margin-bottom: 1.6rem;
    }}
    .card {{
        border-radius: 18px;
        padding: 20px 22px;
        margin-top: 12px;
        margin-bottom: 12px;
        background: #ffffff;
        border: 1px solid #e0e3ea;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
    }}
    .card-header {{
        font-size: 1.15rem;
        font-weight: 650;
        color: {BRAND_PRIMARY};
        margin-bottom: 0.25rem;
    }}
    .pill {{
        display: inline-block;
        padding: 5px 12px;
        margin: 3px;
        border-radius: 999px;
        background-color: rgba(106,151,57,0.1);
        color: {BRAND_SECONDARY};
        font-size: 0.85rem;
        border: 1px solid rgba(106,151,57,0.35);
    }}
    .footer-logos {{
        margin-top: 32px;
        padding-top: 14px;
        border-top: 1px solid #d0d4dd;
    }}
    .footer-text {{
        font-size: 0.9rem;
        color: #777777;
        text-align: center;
        margin-top: 4px;
    }}
    .stButton>button {{
        border-radius: 999px;
        padding: 0.55rem 1.6rem;
        border: none;
        font-weight: 600;
        font-size: 0.98rem;
        background: linear-gradient(135deg, {BRAND_PRIMARY}, {BRAND_SECONDARY});
        color: white;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.25);
    }}
    .stButton>button:hover {{
        filter: brightness(1.04);
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.35);
    }}
    .small-muted {{
        font-size: 0.88rem;
        color: #7f8c8d;
    }}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# FUNÇÕES AUXILIARES
# =========================

def show_logos_footer():
    """Mostra as duas logos no rodapé de cada página."""
    st.markdown('<div class="footer-logos">', unsafe_allow_html=True)
    col_l, col_r = st.columns(2)
    with col_l:
        if os.path.exists(LOGO_CETRAD):
            st.image(LOGO_CETRAD, width=150)
    with col_r:
        if os.path.exists(LOGO_VINEWINE):
            st.image(LOGO_VINEWINE, width=150)
    st.markdown(
        '<div class="footer-text">Smart Green Innovation Indicators – CETRAD & Vine&Wine • Desenvolvido por Cibele</div>',
        unsafe_allow_html=True,
    )

def normaliza_num(texto: str) -> str:
    if texto is None:
        return ""
    t = str(texto).strip().replace(",", ".")
    return t

def infere_tipo(metrica: str) -> str:
    """Classifica a métrica para validação numérica."""
    if not isinstance(metrica, str):
        return "livre"
    m = metrica.lower()
    if "%" in m or "percent" in m:
        return "percent"
    if "€" in m or "eur" in m or "euro" in m or "r$" in m or "$" in m:
        return "money"
    if any(u in m for u in ["tco2", "t co2", "t co₂", "t co2e", " t", "ton", "kg", "kwh", "m³", "m3", " l", " l/"]):
        return "nonneg"
    if "hora" in m or m.strip() == "h" or " h/" in m:
        return "nonneg"
    if "nº" in m or "num" in m or "publica" in m or "patent" in m or "contagem" in m:
        return "integer"
    return "nonneg"

def valida_valor(valor_texto: str, metrica: str, fracao_percent=False):
    """
    Retorna (ok, valor_normalizado, msg_erro).
    - percent: 0..100 (ou 0..1 se fracao_percent=True, converte para %)
    - money/nonneg: >= 0
    - integer: inteiro >= 0
    """
    tipo = infere_tipo(metrica)
    t = normaliza_num(valor_texto)
    if t == "":
        return False, None, "Obrigatório preencher um valor."
    try:
        if tipo == "percent":
            x = float(t)
            if fracao_percent:
                if 0 <= x <= 1:
                    return True, x * 100, ""
                return False, None, "Para fração, use 0–1 (ex.: 0.25 para 25%)."
            else:
                if 0 <= x <= 100:
                    return True, x, ""
                return False, None, "Percentual deve estar entre 0 e 100."
        elif tipo == "money":
            x = float(t)
            if x < 0:
                return False, None, "Valor monetário deve ser ≥ 0."
            return True, x, ""
        elif tipo == "integer":
            x = int(float(t))
            if x < 0:
                return False, None, "Deve ser inteiro ≥ 0."
            return True, x, ""
        else:
            x = float(t)
            if x < 0:
                return False, None, "Valor deve ser ≥ 0."
            return True, x, ""
    except Exception:
        return False, None, "Formato inválido. Utilize apenas números (ponto ou vírgula)."

@st.cache_data
def load_inov_tags(path: str) -> pd.DataFrame:
    """Carrega a tabela de inovações, tags e descrição."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    df = pd.read_excel(path)
    for col in ["Inovação", "Descrição", "Tags"]:
        if col not in df.columns:
            raise ValueError(f"A planilha InoDescTagsEng.xlsx deve conter a coluna '{col}'.")
    return df

@st.cache_data
def load_ind_meta(path: str) -> pd.DataFrame:
    """Carrega a tabela de metadados de indicadores (modelo do App3)."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    df = pd.read_excel(path)
    for col in ["Indicadores", "Descrição", "Mensuração", "Categoria"]:
        if col not in df.columns:
            raise ValueError(f"A planilha IndDescMensCat.xlsx deve conter as colunas 'Indicadores', 'Descrição', 'Mensuração', 'Categoria'.")
    return df

@st.cache_data
def load_ind_ref(path: str) -> pd.DataFrame:
    """Carrega a tabela de métricas de referência (indicadores_classificados_114.xlsx)."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    df = pd.read_excel(path)
    for col in ["Indicadores", "Descrição", "Mensuração"]:
        if col not in df.columns:
            raise ValueError("A planilha indicadores_classificados_114.xlsx deve conter as colunas 'Indicadores', 'Descrição', 'Mensuração'.")
    df = df.rename(
        columns={
            "Descrição": "Descricao_Ref",
            "Mensuração": "Mensuracao_Ref",
            "Categoria": "Categoria_Ref" if "Categoria" in df.columns else "Categoria_Ref"
        }
    )
    return df

@st.cache_data
def load_link_inv_ind(path: str) -> pd.DataFrame:
    """Carrega a tabela que liga Inovação ↔ Indicador."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    df = pd.read_excel(path)
    for col in ["Inovação", "Indicador"]:
        if col not in df.columns:
            raise ValueError("A planilha Inovação_Ind.xlsx deve conter as colunas 'Inovação' e 'Indicador'.")
    df["Inovação"] = df["Inovação"].ffill()
    return df

def normalize_key(s: str) -> str:
    """Normaliza texto para comparação (sem acentos, minúsculo, sem pontuação)."""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def extract_abbrev_token(name: str):
    """Extrai um token de abreviação entre parênteses, ex.: (ROI), (PBP), (LCC)."""
    m = re.search(r"\(([^)]+)\)", str(name))
    if m:
        content = m.group(1).strip()
        token = re.split(r"[ /]", content)[0].strip()
        if len(token) >= 2:
            return token
    return None

@st.cache_data
def build_indicator_mapping(df_link: pd.DataFrame, df_meta: pd.DataFrame) -> pd.DataFrame:
    """
    Constrói uma tabela de mapeamento entre:
    - Indicador (PT) da Inovação_Ind.xlsx
    - Indicadores (EN/PT misto) da IndDescMensCat.xlsx
    Usa abreviações (ROI, PBP, LCC...) e similaridade.
    """
    pt_list = df_link["Indicador"].dropna().astype(str).unique().tolist()
    en_list = df_meta["Indicadores"].dropna().astype(str).unique().tolist()

    # mapa de abreviações
    meta_abbrev = {}
    for name in en_list:
        ab = extract_abbrev_token(name)
        if ab:
            meta_abbrev.setdefault(ab, []).append(name)

    # mapa de texto normalizado
    meta_norm_map = {normalize_key(n): n for n in en_list}

    mapping_rows = []
    for pt_name in pt_list:
        ab = extract_abbrev_token(pt_name)
        chosen = None
        method = None

        # 1) tentar por abreviação
        if ab and ab in meta_abbrev and len(meta_abbrev[ab]) == 1:
            chosen = meta_abbrev[ab][0]
            method = "abbrev"

        # 2) se ainda não casou, tentar similaridade de texto
        if chosen is None:
            n = normalize_key(pt_name)
            candidates = difflib.get_close_matches(n, list(meta_norm_map.keys()), n=1, cutoff=0.8)
            if candidates:
                chosen = meta_norm_map[candidates[0]]
                method = "similar"

        mapping_rows.append(
            {
                "Indicador_PT": pt_name,
                "Indicador_EN": chosen,
                "Metodo_Mapeamento": method if chosen is not None else "nenhum",
            }
        )
    return pd.DataFrame(mapping_rows)

def set_page(p: int):
    st.session_state.current_page = p

def init_session_state():
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1
    if "selected_inovacao" not in st.session_state:
        st.session_state.selected_inovacao = None
    if "selected_tag" not in st.session_state:
        st.session_state.selected_tag = None
    if "metric_values" not in st.session_state:
        st.session_state.metric_values = {}
    if "metric_errors" not in st.session_state:
        st.session_state.metric_errors = {}
    if "project_name" not in st.session_state:
        st.session_state.project_name = ""

init_session_state()

# =========================
# CARREGAMENTO DAS TABELAS
# =========================
try:
    df_inov_tags = load_inov_tags(PATH_INO_TAGS)
except Exception as e:
    st.error(f"Não foi possível carregar a tabela de Inovações (InoDescTagsEng.xlsx): {e}")
    st.stop()

try:
    df_ind_meta = load_ind_meta(PATH_IND_META)
except Exception as e:
    st.error(f"Não foi possível carregar a tabela de Indicadores (IndDescMensCat.xlsx): {e}")
    st.stop()

try:
    df_ind_ref = load_ind_ref(PATH_IND_REF)
except Exception as e:
    st.error(f"Não foi possível carregar a tabela de métricas de referência (indicadores_classificados_114.xlsx): {e}")
    st.stop()

try:
    df_link = load_link_inv_ind(PATH_LINK_INV_IND)
except Exception as e:
    st.error(f"Não foi possível carregar a tabela de ligação Inovação_Ind.xlsx: {e}")
    st.stop()

df_map_ind = build_indicator_mapping(df_link, df_ind_meta)

# =========================
# Ícone e imagem por inovação
# =========================
def icon_for_innovation(name: str) -> str:
    n = name.lower()
    if "clima" in n or "climate" in n:
        return "🌱"
    if "vine" in n or "wine" in n:
        return "🍇"
    if "energia" in n or "energy" in n:
        return "⚡"
    if "agua" in n or "água" in n or "water" in n:
        return "💧"
    if "digital" in n or "data" in n or "smart" in n:
        return "💻"
    if "carbon" in n or "co2" in n:
        return "🌍"
    return "💡"

def image_url_for_innovation(name: str) -> str:
    slug = name.replace(" ", "-")
    return f"https://source.unsplash.com/320x200/?innovation,{slug}"

# =========================
# PÁGINA 1 – ABERTURA E SELEÇÃO
# =========================
def page_1():
    st.markdown('<div class="big-title">Smart Green Innovation Indicators</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Integrating Eco-Efficiency, Sustainable Competitiveness</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtext">'
        'Trabalho realizado pelo CETRAD em parceria com Vine&Wine.<br>'
        'Equipe de Pesquisadores • Desenvolvedor: <b>Cibele</b> 😊'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### 1️⃣ Escolha a inovação que pretende analisar")

    inovacoes = sorted(df_inov_tags["Inovação"].astype(str).unique().tolist())

    # Tags
    all_tags_series = df_inov_tags["Tags"].astype(str).fillna("")
    all_tags = []
    for t in all_tags_series:
        parts = [p.strip() for p in re.split(r"[;,]", t) if p.strip()]
        all_tags.extend(parts)
    tags_unicas = sorted(set(all_tags))

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("**Selecionar por Inovação**")
        sel_inov = st.selectbox(
            "Inovação:",
            options=["— selecione uma inovação —"] + inovacoes,
            index=0,
        )
    with col_right:
        st.markdown("**Selecionar por Tag**")
        sel_tag = st.selectbox(
            "Tag:",
            options=["— opcional —"] + tags_unicas,
            index=0,
        )

    selected_inovacao = None
    selected_tag = None

    if sel_inov != "— selecione uma inovação —":
        selected_inovacao = sel_inov

    if sel_tag != "— opcional —":
        selected_tag = sel_tag
        mask = df_inov_tags["Tags"].astype(str).str.contains(selected_tag, case=False, na=False)
        rel = df_inov_tags[mask]
        if len(rel) > 0:
            selected_inovacao = str(rel.iloc[0]["Inovação"])

    st.session_state.selected_inovacao = selected_inovacao
    st.session_state.selected_tag = selected_tag

    # cartão da inovação
    if selected_inovacao:
        st.markdown("----")
        st.markdown("#### Resumo da inovação selecionada")
        rel_inv = df_inov_tags[df_inov_tags["Inovação"].astype(str) == selected_inovacao]
        if len(rel_inv) > 0:
            row = rel_inv.iloc[0]
            desc = str(row["Descrição"])
            eng = str(row.get("Engajamento", ""))
            tags_text = str(row["Tags"])
            icon = icon_for_innovation(selected_inovacao)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            c1, c2 = st.columns([0.15, 0.85])
            with c1:
                st.markdown(
                    f"<div style='font-size:3rem; text-align:center;'>{icon}</div>",
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f"<div class='card-header'>{selected_inovacao}</div>",
                    unsafe_allow_html=True,
                )
                if desc and desc.lower() != "nan":
                    st.markdown(
                        f"<p style='font-size:1.0rem; color:#34495e;'>{desc}</p>",
                        unsafe_allow_html=True,
                    )
                if eng and eng.lower() != "nan":
                    st.markdown(
                        f"<p style='font-size:0.95rem; color:#7f8c8d;'><b>Enfoque / Engajamento:</b> {eng}</p>",
                        unsafe_allow_html=True,
                    )
                if tags_text and tags_text.lower() != "nan":
                    st.markdown(
                        "<p style='font-size:0.9rem; color:#7f8c8d; margin-bottom:4px;'>Tags associadas:</p>",
                        unsafe_allow_html=True,
                    )
                    pills = ""
                    for t in [p.strip() for p in re.split(r"[;,]", tags_text) if p.strip()]:
                        pills += f"<span class='pill'>#{t}</span>"
                    st.markdown(pills, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("----")
    col_b1, col_b2 = st.columns([1, 3])
    with col_b1:
        if st.button("Submeter ➜ Página 2"):
            if not st.session_state.selected_inovacao:
                st.warning("Selecione pelo menos uma inovação ou uma tag antes de avançar.")
            else:
                set_page(2)

    show_logos_footer()

# =========================
# PÁGINA 2 – DESCRIÇÃO DETALHADA
# =========================
def page_2():
    selected_inovacao = st.session_state.get("selected_inovacao", None)
    if not selected_inovacao:
        st.warning("Nenhuma inovação selecionada. Volte para a Página 1.")
        if st.button("⬅ Voltar para Página 1"):
            set_page(1)
        show_logos_footer()
        return

    st.markdown("### 2️⃣ Descrição detalhada da inovação")

    rel_inv = df_inov_tags[df_inov_tags["Inovação"].astype(str) == selected_inovacao]
    if len(rel_inv) == 0:
        st.error("Não foi possível localizar a inovação na tabela InoDescTagsEng.")
        if st.button("⬅ Voltar para Página 1"):
            set_page(1)
        show_logos_footer()
        return

    row = rel_inv.iloc[0]
    desc = str(row["Descrição"])
    eng = str(row.get("Engajamento", ""))
    tags_text = str(row["Tags"])
    icon = icon_for_innovation(selected_inovacao)
    img_url = image_url_for_innovation(selected_inovacao)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    c1, c2 = st.columns([0.75, 0.25])
    with c1:
        st.markdown(
            f"<div class='card-header'>{icon} {selected_inovacao}</div>",
            unsafe_allow_html=True,
        )
        if desc and desc.lower() != "nan":
            st.markdown(
                f"<p style='font-size:1.02rem; color:#2c3e50; margin-top:8px;'>{desc}</p>",
                unsafe_allow_html=True,
            )
        if eng and eng.lower() != "nan":
            st.markdown(
                f"<p style='font-size:0.98rem; color:#7f8c8d;'><b>O que esta inovação faz?</b> {eng}</p>",
                unsafe_allow_html=True,
            )
        if tags_text and tags_text.lower() != "nan":
            st.markdown(
                "<p style='font-size:0.95rem; color:#7f8c8d; margin-bottom:4px;'>Tags relacionadas:</p>",
                unsafe_allow_html=True,
            )
            pills = ""
            for t in [p.strip() for p in re.split(r"[;,]", tags_text) if p.strip()]:
                pills += f"<span class='pill'>#{t}</span>"
            st.markdown(pills, unsafe_allow_html=True)
    with c2:
        st.image(img_url, caption="Inovação (imagem ilustrativa)", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.info(
        "Esta página apresenta a inovação de forma visual e clara, preparando o utilizador para a fase de métricas."
    )

    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("⬅ Voltar para Página 1"):
            set_page(1)
    with col_next:
        if st.button("Processar ➜ Página 3 (Métricas)"):
            set_page(3)

    show_logos_footer()

# =========================
# PÁGINA 3 – MÉTRICAS E TOMADA DE DECISÃO
# =========================
def page_3():
    selected_inovacao = st.session_state.get("selected_inovacao", None)
    if not selected_inovacao:
        st.warning("Nenhuma inovação selecionada. Volte para a Página 1.")
        if st.button("⬅ Voltar para a Página 1"):
            set_page(1)
        show_logos_footer()
        return

    st.markdown("### 3️⃣ Preenchimento de métricas para tomada de decisão")

    st.session_state.project_name = st.text_input(
        "Nome do projeto / caso de uso:",
        value=st.session_state.project_name,
    ).strip()

    inv_links = df_link[df_link["Inovação"].astype(str) == str(selected_inovacao)].copy()
    if len(inv_links) == 0:
        st.warning("Não há indicadores associados a esta inovação na planilha Inovação_Ind.xlsx.")
        col_back, _ = st.columns([1, 3])
        with col_back:
            if st.button("⬅ Voltar para Página 2"):
                set_page(2)
        show_logos_footer()
        return

    # juntar com mapeamento PT ↔ EN
    df_inv = inv_links.merge(
        df_map_ind,
        left_on="Indicador",
        right_on="Indicador_PT",
        how="left",
    )
    df_inv["Indicadores_EN"] = df_inv["Indicador_EN"]

    # merge com metadados do modelo (IndDescMensCat)
    df_inv_inds = df_inv.merge(
        df_ind_meta,
        left_on="Indicadores_EN",
        right_on="Indicadores",
        how="left",
        suffixes=("", "_modelo"),
    )

    # merge com métricas de referência (indicadores_classificados_114)
    df_inv_inds = df_inv_inds.merge(
        df_ind_ref,
        left_on="Indicadores_EN",
        right_on="Indicadores",
        how="left",
        suffixes=("", "_ref"),
    )

    st.markdown(
        f"**Inovação selecionada:** `{selected_inovacao}` – preencha os valores dos indicadores abaixo."
    )
    st.markdown(
        "<p class='small-muted'>Para cada indicador, são apresentadas: a <b>descrição</b>, a "
        "<b>mensuração no modelo da inovação</b> e a <b>métrica de referência oficial</b> "
        "(tabela de 114 indicadores), quando disponível. Insira os valores medidos com base "
        "nessas referências.</p>",
        unsafe_allow_html=True,
    )

    # opcional: mostrar mapeamento técnico
    with st.expander("Ver mapeamento técnico Indicador (PT) → Indicadores (modelo/ref)", expanded=False):
        st.dataframe(
            df_inv[["Indicador", "Indicadores_EN", "Metodo_Mapeamento"]],
            use_container_width=True,
        )

    for i, row in df_inv_inds.iterrows():
        indicador_pt = str(row["Indicador"])
        indicador_en = str(row.get("Indicadores_EN", "")) if pd.notna(row.get("Indicadores_EN", "")) else ""
        desc = str(row.get("Descrição", "")) if pd.notna(row.get("Descrição", "")) else ""
        metr = str(row.get("Mensuração", "")) if pd.notna(row.get("Mensuração", "")) else ""
        categ = str(row.get("Categoria", "")) if pd.notna(row.get("Categoria", "")) else ""

        desc_ref = str(row.get("Descricao_Ref", "")) if pd.notna(row.get("Descricao_Ref", "")) else ""
        metr_ref = str(row.get("Mensuracao_Ref", "")) if pd.notna(row.get("Mensuracao_Ref", "")) else ""

        key_txt = f"val_{i}"
        key_frac = f"frac_{i}"

        st.markdown('<div class="card">', unsafe_allow_html=True)
        c1, c2 = st.columns([0.72, 0.28])
        with c1:
            titulo = indicador_pt if indicador_pt and indicador_pt.lower() != "nan" else indicador_en
            st.markdown(
                f"<div class='card-header'>📊 {titulo}</div>",
                unsafe_allow_html=True,
            )

            if desc:
                st.markdown(
                    f"<p style='font-size:0.98rem; color:#34495e;'><b>Descrição (modelo da inovação):</b> {desc}</p>",
                    unsafe_allow_html=True,
                )
            if metr:
                st.markdown(
                    f"<p style='font-size:0.95rem; color:#7f8c8d;'><b>Mensuração no modelo da inovação:</b><br>{metr}</p>",
                    unsafe_allow_html=True,
                )

            if metr_ref:
                with st.expander("Ver métrica de referência oficial (114 indicadores)", expanded=False):
                    if desc_ref:
                        st.markdown(
                            f"<p style='font-size:0.95rem; color:#34495e;'><b>Descrição de referência:</b> {desc_ref}</p>",
                            unsafe_allow_html=True,
                        )
                    st.markdown(
                        f"<p style='font-size:0.95rem; color:#7f8c8d;'><b>Mensuração / fórmula de referência:</b><br>{metr_ref}</p>",
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    "<p class='small-muted'>Sem métrica de referência explícita associada na tabela de 114 indicadores.</p>",
                    unsafe_allow_html=True,
                )

            if categ:
                st.markdown(
                    f"<p style='font-size:0.9rem; color:#7f8c8d;'><b>Categoria (modelo da inovação):</b> {categ}</p>",
                    unsafe_allow_html=True,
                )

        with c2:
            metr_lower = (metr or "").lower()
            if "%" in metr_lower:
                fr = st.toggle("Valor em fração (0–1)", key=key_frac, value=False)
            else:
                fr = False

        valor_bruto = st.text_input(
            f"Valor para '{titulo}':",
            key=key_txt,
            placeholder="ex.: 12,5  |  0.25  |  3500",
        )

        ok, val_norm, msg = valida_valor(valor_bruto, metr, fracao_percent=fr)
        if ok:
            st.session_state.metric_values[(selected_inovacao, i)] = val_norm
            st.session_state.metric_errors.pop((selected_inovacao, i), None)
            st.markdown(
                "<span style='color:#27ae60; font-size:0.9rem;'>✔ Valor válido</span>",
                unsafe_allow_html=True,
            )
        else:
            if valor_bruto.strip() != "":
                st.session_state.metric_errors[(selected_inovacao, i)] = msg
                st.markdown(
                    f"<span style='color:#c0392b; font-size:0.9rem;'>✖ {msg}</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<span class='small-muted'>Preencha o valor para este indicador.</span>",
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("----")
    col_back, col_process, col_next = st.columns([1, 1, 1])
    with col_back:
        if st.button("⬅ Voltar para Página 2"):
            set_page(2)

    with col_process:
        if st.button("Processar e guardar resultados"):
            erros = []
            registros = []
            for i, row in df_inv_inds.iterrows():
                chave = (selected_inovacao, i)
                indicador_pt = str(row["Indicador"])
                indicador_en = str(row.get("Indicadores_EN", "")) if pd.notna(row.get("Indicadores_EN", "")) else ""
                desc = str(row.get("Descrição", "")) if pd.notna(row.get("Descrição", "")) else ""
                metr = str(row.get("Mensuração", "")) if pd.notna(row.get("Mensuração", "")) else ""
                categ = str(row.get("Categoria", "")) if pd.notna(row.get("Categoria", "")) else ""
                desc_ref = str(row.get("Descricao_Ref", "")) if pd.notna(row.get("Descricao_Ref", "")) else ""
                metr_ref = str(row.get("Mensuracao_Ref", "")) if pd.notna(row.get("Mensuracao_Ref", "")) else ""

                if chave in st.session_state.metric_errors:
                    erros.append((indicador_pt or indicador_en, st.session_state.metric_errors[chave]))
                    continue
                if chave not in st.session_state.metric_values:
                    erros.append((indicador_pt or indicador_en, "Valor não preenchido."))
                    continue

                registros.append(
                    {
                        "Projeto": st.session_state.project_name if st.session_state.project_name else "",
                        "Inovação": selected_inovacao,
                        "Indicador (PT)": indicador_pt,
                        "Indicador (modelo/ref)": indicador_en,
                        "Descrição (modelo)": desc,
                        "Mensuração (modelo)": metr,
                        "Categoria": categ,
                        "Descrição Referência": desc_ref,
                        "Mensuração Referência": metr_ref,
                        "Valor Normalizado": st.session_state.metric_values[chave],
                        "Data/Hora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

            if erros:
                st.error("Existem valores inválidos ou em falta. Corrija antes de finalizar.")
                df_erros = pd.DataFrame(erros, columns=["Indicador", "Problema"])
                st.dataframe(df_erros, use_container_width=True)
            elif not registros:
                st.warning("Nenhum valor foi preenchido para esta inovação.")
            else:
                novo = pd.DataFrame(registros)
                if os.path.exists(RESULTS_FILE):
                    try:
                        antigo = pd.read_excel(RESULTS_FILE)
                        combinado = pd.concat([antigo, novo], ignore_index=True)
                    except Exception:
                        combinado = novo.copy()
                else:
                    combinado = novo.copy()
                combinado.to_excel(RESULTS_FILE, index=False)
                st.success(f"✅ Resultados processados e guardados em '{RESULTS_FILE}'")
                st.dataframe(novo, use_container_width=True)

    with col_next:
        if st.button("Ir para Página 4 – Resultados e Gráficos"):
            set_page(4)

    show_logos_footer()

# =========================
# PÁGINA 4 – RESULTADOS E GRÁFICOS (Plotly)
# =========================
def page_4():
    st.markdown("### 4️⃣ Resultados consolidados e gráficos para decisão")

    df_res_file = None
    if os.path.exists(RESULTS_FILE):
        try:
            df_res_file = pd.read_excel(RESULTS_FILE)
        except Exception as e:
            st.error(f"Não foi possível ler o ficheiro de resultados: {e}")
            df_res_file = None

    if df_res_file is None or df_res_file.empty:
        if "metric_values" in st.session_state and st.session_state.metric_values:
            st.info(
                "Ainda não há ficheiro de resultados guardado, "
                "mas existem valores na sessão atual. Usando-os para gerar os gráficos."
            )
            selected_inovacao = st.session_state.get("selected_inovacao", None)
            if selected_inovacao is None:
                st.warning("Não foi possível identificar a inovação atual para gerar resultados.")
                if st.button("⬅ Voltar para Página 3"):
                    set_page(3)
                show_logos_footer()
                return

            inv_links = df_link[df_link["Inovação"].astype(str) == str(selected_inovacao)].copy()
            df_inv = inv_links.merge(
                df_map_ind,
                left_on="Indicador",
                right_on="Indicador_PT",
                how="left",
            )
            df_inv["Indicadores_EN"] = df_inv["Indicador_EN"]
            df_inv_inds = df_inv.merge(
                df_ind_meta,
                left_on="Indicadores_EN",
                right_on="Indicadores",
                how="left",
            )
            df_inv_inds = df_inv_inds.merge(
                df_ind_ref,
                left_on="Indicadores_EN",
                right_on="Indicadores",
                how="left",
            )

            registros = []
            for i, row in df_inv_inds.iterrows():
                chave = (selected_inovacao, i)
                if chave not in st.session_state.metric_values:
                    continue
                indicador_pt = str(row["Indicador"])
                indicador_en = str(row.get("Indicadores_EN", "")) if pd.notna(row.get("Indicadores_EN", "")) else ""
                desc = str(row.get("Descrição", "")) if pd.notna(row.get("Descrição", "")) else ""
                metr = str(row.get("Mensuração", "")) if pd.notna(row.get("Mensuração", "")) else ""
                categ = str(row.get("Categoria", "")) if pd.notna(row.get("Categoria", "")) else ""
                desc_ref = str(row.get("Descricao_Ref", "")) if pd.notna(row.get("Descricao_Ref", "")) else ""
                metr_ref = str(row.get("Mensuracao_Ref", "")) if pd.notna(row.get("Mensuracao_Ref", "")) else ""
                registros.append(
                    {
                        "Projeto": st.session_state.project_name if st.session_state.project_name else "",
                        "Inovação": selected_inovacao,
                        "Indicador (PT)": indicador_pt,
                        "Indicador (modelo/ref)": indicador_en,
                        "Descrição (modelo)": desc,
                        "Mensuração (modelo)": metr,
                        "Categoria": categ,
                        "Descrição Referência": desc_ref,
                        "Mensuração Referência": metr_ref,
                        "Valor Normalizado": st.session_state.metric_values[chave],
                        "Data/Hora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
            if not registros:
                st.warning("Não há valores preenchidos na sessão atual. Volte à Página 3 e processe os dados.")
                if st.button("⬅ Voltar para Página 3"):
                    set_page(3)
                show_logos_footer()
                return
            df_res = pd.DataFrame(registros)
        else:
            st.info("Ainda não há resultados guardados. Volte à Página 3, preencha os indicadores e processe os dados.")
            if st.button("⬅ Voltar para Página 3"):
                set_page(3)
            show_logos_footer()
            return
    else:
        df_res = df_res_file.copy()

    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        projetos = ["(todos)"] + sorted(df_res["Projeto"].fillna("").astype(str).unique().tolist())
        proj_sel = st.selectbox("Filtrar por projeto:", projetos)
    with col_f2:
        inovs = ["(todas)"] + sorted(df_res["Inovação"].fillna("").astype(str).unique().tolist())
        inov_sel = st.selectbox("Filtrar por inovação:", inovs)

    dfv = df_res.copy()
    if proj_sel != "(todos)":
        dfv = dfv[dfv["Projeto"].astype(str) == proj_sel]
    if inov_sel != "(todas)":
        dfv = dfv[dfv["Inovação"].astype(str) == inov_sel]

    if dfv.empty:
        st.warning("Não há dados para os filtros selecionados.")
        if st.button("⬅ Voltar para Página 3"):
            set_page(3)
        show_logos_footer()
        return

    st.markdown("#### 4.1 Comparação dos valores com as métricas de referência")
    st.markdown(
        "<p class='small-muted'>Tabela com o valor inserido para cada indicador, "
        "a mensuração no modelo da inovação e a mensuração de referência (tabela de 114 indicadores).</p>",
        unsafe_allow_html=True,
    )

    cols_to_show = [
        "Inovação",
        "Categoria",
        "Indicador (PT)",
        "Indicador (modelo/ref)",
        "Valor Normalizado",
        "Mensuração (modelo)",
        "Mensuração Referência",
    ]
    cols_exist = [c for c in cols_to_show if c in dfv.columns]
    st.dataframe(dfv[cols_exist], use_container_width=True)

    st.markdown("----")
    st.markdown("#### 4.2 Média dos valores por categoria")

    dfv_num = dfv.copy()
    dfv_num["Valor Numérico"] = pd.to_numeric(dfv_num["Valor Normalizado"], errors="coerce")
    grp_mean = (
        dfv_num.groupby("Categoria")["Valor Numérico"]
        .mean()
        .dropna()
        .sort_values(ascending=False)
    )

    if grp_mean.empty:
        st.info("Não há valores numéricos suficientes para calcular médias por categoria.")
    else:
        df_mean = grp_mean.rename("Média por Categoria").reset_index()
        st.dataframe(df_mean, use_container_width=True)
        fig_mean = px.bar(
            df_mean,
            x="Categoria",
            y="Média por Categoria",
            title="Média dos valores por categoria",
        )
        fig_mean.update_layout(xaxis_title="Categoria", yaxis_title="Média dos valores")
        st.plotly_chart(fig_mean, use_container_width=True)

    st.markdown("----")
    st.markdown("#### 4.3 Distribuição – contagem de indicadores preenchidos por categoria")

    grp_count = (
        dfv_num.dropna(subset=["Valor Numérico"])
        .groupby("Categoria")["Indicador (modelo/ref)"]
        .count()
        .sort_values(ascending=False)
    )

    if grp_count.empty:
        st.info("Não há indicadores preenchidos suficientes para a contagem por categoria.")
    else:
        df_count = grp_count.rename("Nº de indicadores preenchidos").reset_index()
        st.dataframe(df_count, use_container_width=True)
        fig_count = px.bar(
            df_count,
            x="Categoria",
            y="Nº de indicadores preenchidos",
            title="Distribuição de indicadores preenchidos por categoria",
        )
        fig_count.update_layout(xaxis_title="Categoria", yaxis_title="Nº de indicadores preenchidos")
        st.plotly_chart(fig_count, use_container_width=True)

    st.markdown("----")
    col_back3, col_back1 = st.columns(2)
    with col_back3:
        if st.button("⬅ Voltar para Página 3"):
            set_page(3)
    with col_back1:
        if st.button("⬅ Voltar para Página 1"):
            set_page(1)

    show_logos_footer()

# =========================
# ROTEAMENTO ENTRE PÁGINAS
# =========================
page = st.session_state.current_page

if page == 1:
    page_1()
elif page == 2:
    page_2()
elif page == 3:
    page_3()
elif page == 4:
    page_4()
else:
    set_page(1)
    page_1()
