import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Pagina instellingen
st.set_page_config(page_title="OEE Dashboard", layout="wide")

@st.cache_data
def load_data():
    file_path = 'Data Lijnen boven OEE .xlsx'
    tabbladen = ['2', '11', '24', '25', '29', '31']
    all_sheets = []
    
    try:
        xls = pd.ExcelFile(file_path)
        for sheet in tabbladen:
            if sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet)
                df['Lijn'] = str(sheet)
                df['DD-MM-YY'] = pd.to_datetime(df['DD-MM-YY'], errors='coerce')
                for col in ['OEE', 'Hoeveelheid', 'Aantal personen']:
                     if col in df.columns:
                        if df[col].dtype == 'object':
                            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
                        else:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                
                if 'Bandleidster' in df.columns:
                    df['Bandleidster'] = df['Bandleidster'].astype(str)
                    
                all_sheets.append(df)
        full_df = pd.concat(all_sheets, ignore_index=True)
        return full_df.dropna(subset=['DD-MM-YY', 'OEE'])
    except Exception as e:
        st.error(f"Fout bij laden bestand: {e}")
        return pd.DataFrame()

df = load_data()

# --- HELPER FUNCTIE VOOR LINEAIRE REGRESSIE ---
def bereken_lineaire_trend(df_in, x_col, y_col):
    df_clean = df_in.dropna(subset=[x_col, y_col])
    if len(df_clean) < 2:
        return None, None
    x_dates = df_clean[x_col]
    x_num = (x_dates - x_dates.min()).dt.days
    y = df_clean[y_col]
    z = np.polyfit(x_num, y, 1)
    p = np.poly1d(z)
    return x_dates, p(x_num)

# --- SIDEBAR NAVIGATIE ---
st.sidebar.header("Analyse Selectie")

analyse_type = st.sidebar.radio(
    "Wat wilt u doen?",
    ["Losse productielijn analyseren", "Productielijnen vergelijken"]
)

st.sidebar.markdown("---")

if analyse_type == "Losse productielijn analyseren":
    st.sidebar.subheader("Instellingen Individueel")
    geselecteerde_lijnen = [st.sidebar.selectbox(
        "Kies een machine lijn", 
        options=sorted(df['Lijn'].unique())
    )]
    weergave = st.sidebar.radio("Weergave methode:", ["Samen", "Apart"])
    modus = "Single"
    st.title(f"Analyse Lijn {geselecteerde_lijnen[0]}")

else:
    st.sidebar.subheader("Instellingen Vergelijking")
    geselecteerde_lijnen = st.sidebar.multiselect(
        "Selecteer lijnen om te vergelijken", 
        options=sorted(df['Lijn'].unique()),
        default=[sorted(df['Lijn'].unique())[0], sorted(df['Lijn'].unique())[1]]
    )
    weergave = st.sidebar.radio("Weergave methode:", ["Samen", "Apart"])
    modus = "Multi"
    st.title("Vergelijking Productielijnen")

# --- DATA BASIS FILTERING ---
df_lijn_basis = df[df['Lijn'].isin(geselecteerde_lijnen)].sort_values('DD-MM-YY')

# ==========================================
# FILTERS
# ==========================================
toon_filters = st.toggle("Filters op Bezetting of Leiding")

df_filtered = df_lijn_basis.copy()

if toon_filters:
    st.markdown("##### Selecteer specifieke medewerkers of leidinggevenden")
    f_col1, f_col2 = st.columns(2)

    lead_counts = df_lijn_basis['Bandleidster'].value_counts()
    lead_options = [f"{naam} ({count}x)" for naam, count in lead_counts.items()]
    lead_map = {f"{naam} ({count}x)": naam for naam, count in lead_counts.items()}

    with f_col1:
        gekozen_leads = st.multiselect("Selecteer Bandleidster(s):", options=lead_options, placeholder="Kies bandleiders (leeg = alles)")

    pers_counts = df_lijn_basis['Aantal personen'].value_counts().sort_index()
    pers_options = [f"{int(num)} personen ({count}x)" for num, count in pers_counts.items() if num > 0]
    pers_map = {f"{int(num)} personen ({count}x)": num for num, count in pers_counts.items() if num > 0}

    with f_col2:
        gekozen_pers = st.multiselect("Selecteer Bezetting:", options=pers_options, placeholder="Kies bezetting (leeg = alles)")

    if gekozen_leads:
        echte_namen = [lead_map[x] for x in gekozen_leads]
        df_filtered = df_filtered[df_filtered['Bandleidster'].isin(echte_namen)]
    
    if gekozen_pers:
        echte_aantallen = [pers_map[x] for x in gekozen_pers]
        df_filtered = df_filtered[df_filtered['Aantal personen'].isin(echte_aantallen)]

# ==========================================
# KPI DASHBOARD
# ==========================================
st.markdown("---")
if not df_filtered.empty:
    st.markdown("### Key Performance Indicators")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    avg_oee = df_filtered['OEE'].mean()
    total_prod = df_filtered['Hoeveelheid'].sum()
    max_oee = df_filtered['OEE'].max()
    
    if pd.notna(max_oee):
        best_day_row = df_filtered.loc[df_filtered['OEE'].idxmax()]
        best_day_str = best_day_row['DD-MM-YY'].strftime('%d-%m')
    else:
        best_day_str = "-"
    
    kpi1.metric("Gemiddelde OEE", f"{avg_oee:.1f}%", delta_color="normal")
    kpi2.metric("Totale Productie", f"{total_prod:,.0f}".replace(",", "."), "Stuks")
    kpi3.metric("Hoogste Piek", f"{max_oee:.1f}%", f"op {best_day_str}")
    kpi4.metric("Dagen in Selectie", len(df_filtered), "Records")
else:
    st.warning("Geen data gevonden met deze combinatie van filters.")

# --- RUWE DATA ---
with st.expander("📂 Bekijk gefilterde data tabel"):
    st.dataframe(df_filtered, use_container_width=True)

# ==========================================
# GRAFIEK INSTELLINGEN
# ==========================================
st.markdown("#### Grafiek Instellingen")
c1, c2, c3 = st.columns(3)
with c1:
    # AANGEPASTE KNOP: Weekgemiddelde
    toon_week_gem = st.toggle("Weekgemiddelde", value=False)
with c2:
    toon_linear = st.toggle("Lineaire Trend", value=True)
with c3:
    toon_gemiddelde = st.toggle("Totaal Gemiddelde")

kleuren_palet = ['#1f77b4', '#9467bd', '#2ca02c', '#d62728', '#8c564b', '#e377c2']
hover_cols_basis = ['Bandleidster', 'Product', 'Aantal personen']

plot_config = {
    'displayModeBar': True,
    'displaylogo': False,
    'toImageButtonOptions': {'format': 'png', 'filename': 'oee_export', 'height': 800, 'width': 1200, 'scale': 2}
}

# ==========================================
# PLOTTING LOGICA
# ==========================================
if not df_filtered.empty:
    
    # --- SAMEN WEERGAVE ---
    if weergave == "Samen":
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        for i, lijn_naam in enumerate(geselecteerde_lijnen):
            lijn_data = df_filtered[df_filtered['Lijn'] == lijn_naam]
            if lijn_data.empty: continue

            if modus == "Single":
                c_oee, c_qty = '#1f77b4', 'orange'
                c_trend_week = 'red' 
                c_trend_linear = 'darkred'
            else:
                c = kleuren_palet[i % len(kleuren_palet)]
                c_oee, c_qty = c, c
                c_trend_week = c
                c_trend_linear = c

            custom_data_oee = lijn_data[hover_cols_basis + ['Hoeveelheid']]
            
            # 1. Ruwe Data OEE
            fig.add_trace(go.Scatter(
                x=lijn_data['DD-MM-YY'], y=lijn_data['OEE'], name=f"Lijn {lijn_naam} OEE",
                mode='lines+markers', customdata=custom_data_oee,
                hovertemplate=f"<b>Lijn {lijn_naam}</b><br>Datum: %{{x}}<br>OEE: %{{y:.2f}}%<br>Hoeveelheid: %{{customdata[3]}}<br>Lid: %{{customdata[0]}}<extra></extra>",
                opacity=0.5 if (toon_linear or toon_week_gem) else 1,
                line=dict(color=c_oee, width=3)
            ), secondary_y=False)

            # 2. Ruwe Data Hoeveelheid
            fig.add_trace(go.Scatter(
                x=lijn_data['DD-MM-YY'], y=lijn_data['Hoeveelheid'], name=f"Lijn {lijn_naam} H",
                mode='lines',
                hovertemplate=f"<b>Lijn {lijn_naam}</b><br>Hoeveelheid: %{{y}}<extra></extra>",
                line=dict(color=c_qty, width=1.5, dash='dot')
            ), secondary_y=True)

            # 3. WEEKGEMIDDELDE (GroupBy Year+Week)
            if toon_week_gem:
                # We groeperen op Jaar en Weeknummer om weekgemiddeldes te berekenen
                # 'transform' zorgt dat dit gemiddelde voor elke dag in die week wordt ingevuld
                t_oee = lijn_data.groupby([lijn_data['DD-MM-YY'].dt.isocalendar().year, 
                                           lijn_data['DD-MM-YY'].dt.isocalendar().week])['OEE'].transform('mean')
                
                fig.add_trace(go.Scatter(
                    x=lijn_data['DD-MM-YY'], y=t_oee, name=f"Weekgem. {lijn_naam}",
                    # shape='hv' kan ook voor trapjes, maar standaard lijn verbindt de weken mooier
                    line=dict(color=c_trend_week, width=2, dash='solid'), 
                    hoverinfo='skip'
                ), secondary_y=False)

            # 4. LINEAR REGRESSION
            if toon_linear and len(lijn_data) > 1:
                tx, ty = bereken_lineaire_trend(lijn_data, 'DD-MM-YY', 'OEE')
                if tx is not None:
                    fig.add_trace(go.Scatter(
                        x=tx, y=ty, name=f"Trend {lijn_naam}",
                        line=dict(color=c_trend_linear, width=4, dash='longdash'), 
                        opacity=0.9, hoverinfo='skip'
                    ), secondary_y=False)

        if toon_gemiddelde:
            fig.add_hline(y=df_filtered['OEE'].mean(), line_color="black", annotation_text="Gem. OEE")

        fig.update_layout(height=600, hovermode="x unified", legend=dict(orientation="h", y=1.02, x=1, xanchor="right"))
        fig.update_yaxes(title_text="OEE (%)", secondary_y=False, range=[0, 105])
        fig.update_yaxes(title_text="Hoeveelheid (G)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True, config=plot_config)

    # --- APART WEERGAVE ---
    else:
        fig_oee = go.Figure()
        fig_qty = go.Figure()

        for i, lijn_naam in enumerate(geselecteerde_lijnen):
            lijn_data = df_filtered[df_filtered['Lijn'] == lijn_naam]
            if lijn_data.empty: continue

            if modus == "Single":
                c_oee, c_qty = '#1f77b4', 'orange'
                c_trend_linear_oee = 'red'
                c_trend_linear_qty = 'darkorange'
            else:
                c = kleuren_palet[i % len(kleuren_palet)]
                c_oee, c_qty = c, c
                c_trend_linear_oee = c
                c_trend_linear_qty = c

            cd_oee = lijn_data[hover_cols_basis + ['Hoeveelheid']]
            cd_qty = lijn_data[hover_cols_basis + ['OEE']]

            # 1. Ruwe Plots
            fig_oee.add_trace(go.Scatter(
                x=lijn_data['Datum'], y=lijn_data['OEE'], name=f"Lijn {lijn_naam}",
                mode='lines+markers', customdata=cd_oee,
                hovertemplate=f"<b>Lijn {lijn_naam}</b><br>Datum: %{{x}}<br>OEE: %{{y:.2f}}%<br><b>Hoeveelheid: %{{customdata[3]}}</b><br>Lid: %{{customdata[0]}}<extra></extra>",
                opacity=0.4 if (toon_linear or toon_week_gem) else 1,
                line=dict(color=c_oee, width=3)
            ))

            fig_oee.update_xaxes(tickangle=-45)
            fig_oee.update_yaxes(showgrid=True, gridwidth=2, gridcolor='LightGrey', minor=dict(showgrid=True, gridwidth=1, gridcolor='WhiteSmoke'))
            # Verticale lijnen (x-as): dikke hoofdlijnen en dunne tussenlijnen
            fig_oee.update_xaxes(
                showgrid=True, 
                gridwidth=1,           # Dikte verticale hoofdlijnen
                gridcolor='LightGrey', 
                minor=dict(
                    showgrid=True, 
                    gridwidth=0.3,       # Dikte verticale tussenlijnen
                    gridcolor='WhiteSmoke'
                )
            )
            
            fig_qty.add_trace(go.Scatter(
                x=lijn_data['Datum'], y=lijn_data['Hoeveelheid'], name=f"Lijn {lijn_naam}",
                mode='lines', customdata=cd_qty,
                hovertemplate=f"<b>Lijn {lijn_naam}</b><br>Datum: %{{x}}<br>Hoeveelheid: %{{y}}<br><b>OEE: %{{customdata[3]:.2f}}%</b><br>Product: %{{customdata[1]}}<extra></extra>",
                opacity=0.4 if (toon_linear or toon_week_gem) else 1,
                line=dict(color=c_qty, width=2),
            ))

            fig_qty.update_xaxes(tickangle=-45)
            fig_qty.update_yaxes(showgrid=True, gridwidth=2, gridcolor='LightGrey', minor=dict(showgrid=True, gridwidth=1, gridcolor='WhiteSmoke'))
            fig_qty.update_xaxes(
                showgrid=True, 
                gridwidth=1,           # Dikte verticale hoofdlijnen
                gridcolor='LightGrey', 
                minor=dict(
                    showgrid=True, 
                    gridwidth=0.3,       # Dikte verticale tussenlijnen
                    gridcolor='WhiteSmoke'
                )
            )

            # 2. WEEKGEMIDDELDE (GroupBy Year+Week)
            if toon_week_gem:
                # OEE
                t_oee = lijn_data.groupby([lijn_data['DD-MM-YY'].dt.isocalendar().year, 
                                           lijn_data['DD-MM-YY'].dt.isocalendar().week])['OEE'].transform('mean')
                fig_oee.add_trace(go.Scatter(x=lijn_data['DD-MM-YY'], y=t_oee, name=f"Weekgem. {lijn_naam}",
                                             line=dict(color=c_oee, width=2, dash='solid'), hoverinfo='skip'))
                # Qty
                t_qty = lijn_data.groupby([lijn_data['DD-MM-YY'].dt.isocalendar().year, 
                                           lijn_data['DD-MM-YY'].dt.isocalendar().week])['Hoeveelheid'].transform('mean')
                fig_qty.add_trace(go.Scatter(x=lijn_data['DD-MM-YY'], y=t_qty, name=f"Weekgem. {lijn_naam}",
                                             line=dict(color=c_qty, width=2, dash='solid'), hoverinfo='skip'))

            # 3. LINEAR REGRESSION
            if toon_linear and len(lijn_data) > 1:
                # OEE Trend
                tx_oee, ty_oee = bereken_lineaire_trend(lijn_data, 'DD-MM-YY', 'OEE')
                if tx_oee is not None:
                    fig_oee.add_trace(go.Scatter(
                        x=tx_oee, y=ty_oee, name=f"Trend {lijn_naam}",
                        line=dict(color=c_trend_linear_oee, width=4, dash='longdash'), 
                        opacity=1, hoverinfo='skip'
                    ))
                
                # Hoeveelheid Trend
                tx_qty, ty_qty = bereken_lineaire_trend(lijn_data, 'DD-MM-YY', 'Hoeveelheid')
                if tx_qty is not None:
                    fig_qty.add_trace(go.Scatter(
                        x=tx_qty, y=ty_qty, name=f"Trend {lijn_naam}",
                        line=dict(color=c_trend_linear_qty, width=4, dash='longdash'),
                        opacity=1, hoverinfo='skip'
                    ))

        if toon_gemiddelde:
            fig_oee.add_hline(y=df_filtered['OEE'].mean(), line_color="green", line_dash="dash", annotation_text="Gem. OEE")
            fig_qty.add_hline(y=df_filtered['Hoeveelheid'].mean(), line_color="green", line_dash="dash", annotation_text="Gem. H")

        fig_oee.update_layout(title="OEE Percentage (%)", height=400, hovermode="x unified", legend=dict(orientation="h", y=1.1, x=1, xanchor="right"), yaxis=dict(range=[0, 105]))
        fig_qty.update_layout(title="Hoeveelheid (G)", height=400, hovermode="x unified", legend=dict(orientation="h", y=1.1, x=1, xanchor="right"))

        st.plotly_chart(fig_oee, use_container_width=True, config=plot_config)
        st.plotly_chart(fig_qty, use_container_width=True, config=plot_config)