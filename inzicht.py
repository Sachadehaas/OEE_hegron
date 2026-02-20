import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Lijn 24 - Analyse", layout="wide")

def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "Data Lijnen boven OEE .xlsx")
    
    if not os.path.exists(file_path):
        st.error(f"❌ Bestand niet gevonden op: {file_path}")
        return None, []

    try:
        df = pd.read_excel(file_path, sheet_name="inzicht 24")
        
        # --- DATA OPSCHONEN (REGEL 54) ---
        df = df.iloc[:54]
        df.columns = df.columns.astype(str).str.strip()
        
        # --- DATUM FIX ---
        if 'DD-MM-YY' in df.columns:
            df['Datum_Schoon'] = pd.to_datetime(df['DD-MM-YY'], dayfirst=True, errors='coerce')
            if df['Datum_Schoon'].isna().all():
                df['Datum_Schoon'] = df['DD-MM-YY'].astype(str).apply(lambda x: x[2:] if len(str(x)) > 8 else x)
                df['Datum_Schoon'] = pd.to_datetime(df['Datum_Schoon'], dayfirst=True, errors='coerce')
            
            df = df.dropna(subset=['Datum_Schoon'])
            df = df.sort_values('Datum_Schoon')
            df['Week'] = df['Datum_Schoon'].dt.isocalendar().week
        else:
            st.error("Kolom 'DD-MM-YY' niet gevonden.")
            return None, []

        # --- FLEXIBELE KOLOM DETECTIE ---
        target_keywords = ['Pauze', 'Opstart', 'Monteur', 'QA', 'product', 'Ombouw', 'Schoonmake', 'Diversen']
        
        bestaande_kolommen = []
        for keyword in target_keywords:
            found_col = [c for c in df.columns if keyword.lower() in c.lower()]
            if found_col:
                real_col = found_col[0]
                df[real_col] = pd.to_numeric(df[real_col], errors='coerce').fillna(0)
                bestaande_kolommen.append(real_col)
        
        return df, bestaande_kolommen

    except Exception as e:
        st.error(f"Fout bij inladen: {e}")
        return None, []

# --- UI START ---
st.title("📊 Lijn 24: Trend & Weekanalyse")

df, wait_cols = load_data()

if df is not None and wait_cols:
    st.sidebar.header("Instellingen")
    selected = st.sidebar.multiselect("Selecteer categorieën:", options=wait_cols, default=wait_cols)
    
    st.sidebar.divider()
    show_trend = st.sidebar.checkbox("Toon Trendlijn (OLS)", value=False)
    show_weekly = st.sidebar.toggle("Toon Weekgemiddelde Grafiek", value=False)

    if selected:
        if not show_weekly:
            # GEBRUIK SCATTER VOOR TRENDLINE ONDERSTEUNING
            # Door mode='lines+markers' ziet het eruit als een lijndiagram
            fig = px.scatter(
                df, x='Datum_Schoon', y=selected,
                title="Dagelijks Verloop Lijn 24",
                template="plotly_white",
                trendline="ols" if show_trend else None,
                render_mode="svg" 
            )
            # Voeg handmatig de lijnen toe tussen de punten
            fig.update_traces(mode='lines+markers')
            
            fig.update_layout(hovermode="x unified", xaxis_title="Datum", yaxis_title="Minuten")
            st.plotly_chart(fig, use_container_width=True)
        else:
            # WEEKGEMIDDELDE
            st.subheader("Gemiddelde minuten per weeknummer")
            df_weekly = df.groupby('Week')[selected].mean().reset_index()
            fig_weekly = px.bar(
                df_weekly, x='Week', y=selected,
                title="Weekgemiddelde",
                barmode='group',
                template="plotly_white"
            )
            st.plotly_chart(fig_weekly, use_container_width=True)

        with st.expander("Tabel met data (max 54 rijen)"):
            st.dataframe(df[['Datum_Schoon', 'Week'] + selected])
    else:
        st.info("Kies een categorie.")