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
    ["Losse productielijn analyseren", "Productielijnen vergelijken", "Overig verkennende analyse"]
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
with st.expander("📂 Bekijk data tabel"):
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
                x=lijn_data['DD-MM-YY'], y=lijn_data['OEE'], name=f"Lijn {lijn_naam}",
                mode='lines+markers', customdata=cd_oee,
                hovertemplate=f"<b>Lijn {lijn_naam}</b><br>Datum: %{{x}}<br>OEE: %{{y:.2f}}%<br><b>Hoeveelheid: %{{customdata[3]}}</b><br>Lid: %{{customdata[0]}}<extra></extra>",
                opacity=0.4 if (toon_linear or toon_week_gem) else 1,
                line=dict(color=c_oee, width=3)
            ))

            fig_qty.add_trace(go.Scatter(
                x=lijn_data['DD-MM-YY'], y=lijn_data['Hoeveelheid'], name=f"Lijn {lijn_naam}",
                mode='lines', customdata=cd_qty,
                hovertemplate=f"<b>Lijn {lijn_naam}</b><br>Datum: %{{x}}<br>Hoeveelheid: %{{y}}<br><b>OEE: %{{customdata[3]:.2f}}%</b><br>Product: %{{customdata[1]}}<extra></extra>",
                opacity=0.4 if (toon_linear or toon_week_gem) else 1,
                line=dict(color=c_qty, width=2),
            ))

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

    # ==========================================
    # BOXPLOT ANALYSE (Onder de lijngrafieken)
    # ==========================================
    st.markdown("### Spreiding OEE")

    fig_box = go.Figure()

    for lijn_naam in geselecteerde_lijnen:
        lijn_data_box = df_filtered[df_filtered['Lijn'] == lijn_naam]
        
        if not lijn_data_box.empty:
            fig_box.add_trace(go.Box(
                y=lijn_data_box['OEE'],
                name=f"Lijn {lijn_naam}",
                boxpoints='all',      # Toont alle individuele datapunten naast de box
                jitter=0.3,           # Verspreidt de punten een beetje voor leesbaarheid
                pointpos=-1.8,        # Positie van de punten t.o.v. de box
                marker_color=kleuren_palet[geselecteerde_lijnen.index(lijn_naam) % len(kleuren_palet)],
                boxmean='sd'          # Toont ook het gemiddelde en de standaarddeviatie (stippellijn)
            ))

    fig_box.update_layout(
        height=500,
        yaxis_title="OEE (%)",
        showlegend=False,
        # Pas hier ook de rasters toe voor consistentie
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGrey'),
        xaxis=dict(showgrid=False)
    )

    st.plotly_chart(fig_box, use_container_width=True, config=plot_config)

    import plotly.express as px

# ==========================================
# PLOTTING LOGICA
# ==========================================

if not df_filtered.empty:
    
    # OPTIE 1 & 2: De standaard OEE Lijn grafieken
    if analyse_type in ["Volledig en verkennende analyse"]:
        
        # --- HIER KOMT JE BESTAANDE CODE VOOR DE LIJNGRAFIEKEN (Samen/Apart) ---
        if weergave == "Samen":
            # ... je bestaande code voor fig ...
            st.plotly_chart(fig, use_container_width=True)
        else:
            # ... je bestaande code voor fig_oee & fig_qty ...
            st.plotly_chart(fig_oee, use_container_width=True)
            st.plotly_chart(fig_qty, use_container_width=True)
            
        # De Boxplot die je ook alleen bij de eerste twee opties wilt zien
        st.markdown("### Spreiding OEE (Boxplot)")
        # ... je boxplot code ...

    # OPTIE 3: Alleen de verkennende analyses
    elif analyse_type == "Overig verkennende analyse":
        
        # --- 1. SCATTER PLOT ---
        st.markdown("---")
        st.subheader("Efficiency: Hoeveelheid vs. OEE")
        df_scatter = df_filtered.dropna(subset=['Aantal personen'])
        df_scatter['size_display'] = df_scatter['Aantal personen'].apply(lambda x: max(x, 1))

        if not df_scatter.empty:
            fig_scatter = px.scatter(
                df_scatter, x="Hoeveelheid", y="OEE", color="Bandleidster",
                size="size_display", hover_data=["Product", "DD-MM-YY", "Aantal personen"],
                color_discrete_sequence=px.colors.qualitative.Safe,
                labels={"Hoeveelheid": "Geproduceerde Hoeveelheid", "OEE": "OEE %", "size_display": "Bezetting"}
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

        # --- 2. HEATMAP ---
            st.subheader("Heatmap: Optimale Bezetting per Lijn")
            heatmap_data = df_filtered.groupby(['Lijn', 'Aantal personen'])['OEE'].mean().reset_index()
            
            fig_heat = px.density_heatmap(
                heatmap_data, 
                x="Aantal personen", 
                y="Lijn", 
                z="OEE", 
                color_continuous_scale="RdYlGn", 
                text_auto=".1f"
            )

            # FORCEER DE Y-AS OM ELKE LIJN TE TONEN
            fig_heat.update_yaxes(type='category', dtick=1)
            
            # Optioneel: Forceer ook de X-as op categorie als de bezetting verspringt
            fig_heat.update_xaxes(type='category')

            st.plotly_chart(fig_heat, use_container_width=True)

# --- 3. BAR CHART ---
        st.subheader("Product Analyse: Gemiddelde OEE")
        
        # We groeperen op Product en berekenen zowel het gemiddelde als de frequentie
        product_stats = df_filtered.groupby('Product')['OEE'].agg(['mean', 'count']).reset_index()
        
        # We hernoemen de kolommen voor de duidelijkheid
        product_stats.columns = ['Product', 'Gemiddelde_OEE', 'Frequentie']
        
        # Sorteren op OEE
        product_stats = product_stats.sort_values(by='Gemiddelde_OEE', ascending=True)

        fig_prod = px.bar(
            product_stats, 
            x='Gemiddelde_OEE', 
            y='Product', 
            orientation='h', 
            color='Gemiddelde_OEE', 
            color_continuous_scale='RdYlGn',
            # Voeg de frequentie toe aan de hover data
            hover_data={'Gemiddelde_OEE': ':.2f', 'Frequentie': True},
            labels={'Gemiddelde_OEE': 'Gemiddelde OEE (%)', 'Frequentie': 'Aantal keer geproduceerd'}
        )
        
        # Hoogte aanpassen op basis van het aantal producten
        fig_prod.update_layout(height=max(400, len(product_stats) * 20))
        
        st.plotly_chart(fig_prod, use_container_width=True)

# --- 5. ANALYSE: Bezetting t.o.v. Gemiddelde vs. OEE ---
        st.subheader("Impact van de bezetting-afwijking op OEE")

        # Stap 1: Bereken het gemiddelde aantal personen per lijn
        df_mean_pers = df_filtered.groupby('Lijn')['Aantal personen'].transform('mean')
        
        # Stap 2: Bereken de afwijking (verschil)
        df_filtered['Bezetting_Verschil'] = df_filtered['Aantal personen'] - df_mean_pers

        # Stap 3: Maak de plot
        fig_impact = px.scatter(
            df_filtered,
            x='Bezetting_Verschil',
            y='OEE',
            color='Lijn',
            trendline="ols", # Voegt een trendlijn toe om de correlatie te zien
            hover_data=['DD-MM-YY', 'Aantal personen', 'Bandleidster'],
            labels={
                "Bezetting_Verschil": "Verschil t.o.v. Gemiddelde Bezetting",
                "OEE": "OEE %"
            },
            title="Prestatie bij meer/minder personeel dan gemiddeld"
        )

        # Layout aanpassen voor een duidelijke '0' lijn (het gemiddelde)
        fig_impact.add_vline(x=0, line_dash="dash", line_color="black", annotation_text="Gemiddelde bezetting")
        fig_impact.update_layout(xaxis=dict(dtick=1)) # Zorg voor hele getallen op de x-as
        
        st.plotly_chart(fig_impact, use_container_width=True)

        # Korte uitleg bij de plot
        st.info("""
        **Hoe lees je deze grafiek?**
        * **Links van de stippellijn (negatief):** Dagen waarop er *minder* mensen waren dan normaal.
        * **Rechts van de stippellijn (positief):** Dagen waarop er *meer* mensen waren dan normaal.
        * **Trendlijn:** Loopt de lijn omhoog? Dan helpt extra personeel. Loopt de lijn omlaag? Dan is extra personeel mogelijk inefficiënt.
        """)

# ----- 4. PARETO TABEL ---
        st.subheader("Top 5 Laagste OEE")
        worst_days = df_filtered.sort_values('OEE', ascending=True).head(5)
        st.table(worst_days[['DD-MM-YY', 'Lijn', 'OEE', 'Product', 'Bandleidster', 'Hoeveelheid']].style.format({
            'OEE': '{:.2f}%', 'Hoeveelheid': '{:.0f}'
        }))