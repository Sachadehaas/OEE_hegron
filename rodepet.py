import streamlit as st
import pandas as pd
import os
from datetime import datetime, time

# --- CONFIGURATIE ---
EIND_DATA_FILE = 'hegron_oee_dagtotalen_definitief.csv'
st.set_page_config(page_title="Hegron Operator Logboek", layout="wide")

# --- LIJSTEN EN CATEGORIEËN ---
machine_types = {
    "2": "Pot", "11": "Pot",
    "24": "Parfum", "25": "Parfum", "29": "Parfum", "31": "Parfum",
    "13": "Tube", "14": "Tube", "15": "Tube", "16": "Tube", 
    "17": "Tube", "18": "Tube", "19": "Tube"
}

cat_productie = ["Productie (Draaien)"]

# AANGEPAST: Geplande tijden zoals jij aangaf
cat_gepland = [
    "start/einde productie", 
    "ombouw (omstellen)", 
    "schoonmaken", 
    "pauze", 
    "overnemen"
]

cat_ongepland = [
    "storing (technisch)", # Dit wordt Monteur
    "QC",                  # Dit wordt QC
    "wachten op product",  # Dit wordt Product
    "etiket storing", 
    "etiket wissel", 
    "krat wissel", 
    "verpakking", 
    "wachten op pomp", 
    "tubes",
    "diversen"
]

alle_categorieen = cat_productie + cat_gepland + cat_ongepland

# --- INITIALISATIE GEHEUGEN ---
if 'volgende_starttijd' not in st.session_state:
    st.session_state.volgende_starttijd = time(7, 15)
if 'vorige_eindtijd' not in st.session_state:
    st.session_state.vorige_eindtijd = time(8, 00)
if 'huidig_logboek' not in st.session_state:
    st.session_state.huidig_logboek = []

# ==========================================
# ZIJBALK NAVIGATIE
# ==========================================
st.sidebar.title("Navigatie")
pagina = st.sidebar.radio("Ga naar:", ["Dagstaat Invoeren", "Data Beheren"])

# ==========================================
# PAGINA 1: DAGSTAAT & OEE BEREKENEN
# ==========================================
if pagina == "Dagstaat Invoeren":
    st.title("Operator Dagstaat & OEE Calculator")

    # --- STAP 1: KOPTEKST ---
    with st.container():
        st.subheader("1. Algemene Gegevens")
        c1, c2, c3 = st.columns(3)
        
        with c1:
            datum = st.date_input("Datum", datetime.now())
            machine = st.selectbox("Machine Nummer", list(machine_types.keys()))
            machine_soort = machine_types[machine]
        with c2:
            bandleider = st.selectbox("Bandleider", ["Marla", "Shirley", "Abdel", "Sasi", "Jennifer", "Anders"])
            aantal_mensen = st.number_input("Aantal mensen aan lijn", min_value=1, value=8)
        with c3:
            artikel_nr = st.text_input("Product Nummer", placeholder="Bijv. INP1120573")
            snelheid_per_min = st.number_input("Norm Snelheid (stuks/minuut) *", min_value=1, value=30)

    st.divider()

    # --- STAP 2: TIJDREGEL TOEVOEGEN AAN KLADBLOK ---
    st.subheader("2. Activiteit Toevoegen aan Tijdlijn")

    with st.form("logboek_regel", clear_on_submit=False):
        col_tijd1, col_tijd2, col_cat, col_opm = st.columns([1, 1, 2, 3])
        
        with col_tijd1:
            start_tijd = st.time_input("Van (Starttijd)", value=st.session_state.volgende_starttijd)
        with col_tijd2:
            eind_tijd = st.time_input("Tot (Eindtijd)", value=st.session_state.vorige_eindtijd)
        with col_cat:
            activiteit = st.selectbox("Wat gebeurde er?", alle_categorieen)
        with col_opm:
            opmerking = st.text_input("Opmerking")

        submitted = st.form_submit_button("➕ Voeg tijdblok toe aan lijst")

        if submitted:
            start_min = start_tijd.hour * 60 + start_tijd.minute
            eind_min = eind_tijd.hour * 60 + eind_tijd.minute
            duur = eind_min - start_min
            
            if duur < 0:
                st.error("⚠️ Eindtijd moet na de starttijd liggen!")
            elif duur == 0:
                st.error("⚠️ Tijdsblok kan niet 0 minuten zijn.")
            else:
                if activiteit in cat_productie: type_activiteit = "Productie"
                elif activiteit in cat_gepland: type_activiteit = "Gepland"
                else: type_activiteit = "Ongepland"

                st.session_state.huidig_logboek.append({
                    "Starttijd": start_tijd.strftime("%H:%M"),
                    "Eindtijd": eind_tijd.strftime("%H:%M"),
                    "Minuten": duur,
                    "Activiteit": activiteit,
                    "Type": type_activiteit,
                    "Opmerking": opmerking
                })
                
                st.session_state.volgende_starttijd = eind_tijd
                st.session_state.vorige_eindtijd = eind_tijd
                st.success("Tijdblok toegevoegd!")
                st.rerun()

    # --- STAP 3: ZICHTBARE DAGSTAAT ---
    st.divider()
    st.subheader("3. Jouw Tijdlijn van Vandaag")

    df_vandaag = pd.DataFrame(st.session_state.huidig_logboek)

    if not df_vandaag.empty:
        st.dataframe(df_vandaag, use_container_width=True)
        if st.button("🗑️ Wis laatste regel (Foutje herstellen)"):
            st.session_state.huidig_logboek.pop()
            st.rerun()
    else:
        st.info("Je hebt vandaag nog geen tijdblokken toegevoegd.")

    # --- STAP 4: EINDTOTALEN & EXCEL OPSLAAN ---
    st.divider()
    st.subheader("4. Dag Afsluiten & OEE Berekenen")

    if not df_vandaag.empty:
        # Totale uren berekenen
        min_productie = df_vandaag[df_vandaag['Type'] == 'Productie']['Minuten'].sum()
        min_gepland = df_vandaag[df_vandaag['Type'] == 'Gepland']['Minuten'].sum()
        min_ongepland = df_vandaag[df_vandaag['Type'] == 'Ongepland']['Minuten'].sum()
        
        totale_dienst_tijd = min_productie + min_gepland + min_ongepland
        geplande_productietijd = totale_dienst_tijd - min_gepland
        werkelijke_draaitijd = geplande_productietijd - min_ongepland 

        col_totaal1, col_totaal2, col_totaal3 = st.columns(3)
        col_totaal1.metric("Totale Ingevulde Tijd", f"{totale_dienst_tijd} min")
        col_totaal2.metric("Geplande Stilstand", f"{min_gepland} min")
        col_totaal3.metric("Ongeplande Storingen", f"{min_ongepland} min")

        st.markdown("---")
        st.markdown("**Vul het geproduceerde aantal in om de dag af te sluiten:**")
        
        col_prod1, col_prod2 = st.columns(2)
        with col_prod1:
            totaal_gemaakt = st.number_input("Totaal Aantal Stuks Geproduceerd (incl. afkeur)", min_value=0)
        with col_prod2:
            fout_gemaakt = st.number_input("Aantal Foute Stuks (Afkeur)", min_value=0)

        # OEE Berekeningen
        beschikbaarheid_pct = (werkelijke_draaitijd / geplande_productietijd * 100) if geplande_productietijd > 0 else 0
        theoretische_max = werkelijke_draaitijd * snelheid_per_min
        prestatie_pct = (totaal_gemaakt / theoretische_max * 100) if theoretische_max > 0 else 0
        goede_stuks = totaal_gemaakt - fout_gemaakt
        kwaliteit_pct = (goede_stuks / totaal_gemaakt * 100) if totaal_gemaakt > 0 else 0
        oee_pct = (beschikbaarheid_pct/100) * (prestatie_pct/100) * (kwaliteit_pct/100) * 100

        col_oee1, col_oee2, col_oee3, col_oee4 = st.columns(4)
        col_oee1.metric("Beschikbaarheid", f"{beschikbaarheid_pct:.1f}%")
        col_oee2.metric("Prestatie", f"{prestatie_pct:.1f}%")
        col_oee3.metric("Kwaliteit", f"{kwaliteit_pct:.1f}%")
        col_oee4.metric("OEE Totaal", f"{oee_pct:.1f}%")

        st.markdown("---")
        if st.button("💾 Sla Dag-totaal op in Excel", type="primary"):
            
            # --- SPECIFIEKE STORINGEN FILTEREN UIT DE TIJDLIJN ---
            def haal_minuten_op(activiteit_naam):
                return df_vandaag[df_vandaag['Activiteit'] == activiteit_naam]['Minuten'].sum()

            stilstand_monteur = haal_minuten_op("storing (technisch)")
            stilstand_qc = haal_minuten_op("QC")
            stilstand_product = haal_minuten_op("wachten op product")
            # Divers is alles wat ongepland is min deze drie hoofdcategorieën
            stilstand_divers = min_ongepland - (stilstand_monteur + stilstand_qc + stilstand_product)

            # --- PRECIES DE LIJST DIE JIJ VROEG ---
            dag_samenvatting = {
                "Datum": [datum.strftime("%Y-%m-%d")],
                "Machine Nummer": [machine],
                "Machine Soort": [machine_soort],
                "Bandleider": [bandleider],
                "Aantal Mensen": [aantal_mensen],
                "Product Nummer": [artikel_nr],
                "Norm Snelheid": [snelheid_per_min],
                "Beschikbaarheid %": [round(beschikbaarheid_pct, 1)],
                "Prestatie %": [round(prestatie_pct, 1)],
                "Kwaliteit %": [round(kwaliteit_pct, 1)],
                "OEE %": [round(oee_pct, 1)],
                "Geplande Tijd": [geplande_productietijd],
                "Werkelijke Draaitijd": [werkelijke_draaitijd],
                "Theoretische Max Output": [theoretische_max],
                "Totaal Geproduceerd": [totaal_gemaakt],
                "Goede Producten": [goede_stuks],
                "Foute Producten": [fout_gemaakt],
                "Stilstand Monteur": [stilstand_monteur],
                "Stilstand QC": [stilstand_qc],
                "Stilstand Product": [stilstand_product],
                "Stilstand Divers": [stilstand_divers],
                "Opmerking": ["Samenvatting vanuit Tijdlijn"]
            }
            
            df_save = pd.DataFrame(dag_samenvatting)
            if not os.path.isfile(EIND_DATA_FILE):
                df_save.to_csv(EIND_DATA_FILE, index=False, sep=";")
            else:
                df_save.to_csv(EIND_DATA_FILE, mode='a', header=False, index=False, sep=";")
            
            st.success("✅ Opgeslagen in Excel!")
            st.session_state.huidig_logboek = [] # Maakt kladblok leeg
            st.rerun()
    else:
        st.info("Vul eerst tijdblokken in bij stap 2 om de dag af te kunnen sluiten.")

# ==========================================
# PAGINA 2: DATA BEHEREN (DE MINI-EXCEL)
# ==========================================
elif pagina == "Data Beheren":
    st.title("Opgeslagen Data Beheren")
    
    if os.path.isfile(EIND_DATA_FILE):
        df_beheer = pd.read_csv(EIND_DATA_FILE, sep=";")
        aangepaste_df = st.data_editor(df_beheer, num_rows="dynamic", use_container_width=True, height=500)
        
        if st.button("💾 Wijzigingen opslaan", type="primary"):
            aangepaste_df.to_csv(EIND_DATA_FILE, sep=";", index=False)
            st.success("✅ Je aanpassingen zijn veilig opgeslagen!")
    else:
        st.warning("Er is nog geen data opgeslagen. Vul eerst een dagstaat in.")