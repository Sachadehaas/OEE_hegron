import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURATIE ---
# --- CONFIGURATIE ---
DATA_FILE = 'hegron_oee_logboek_v6.csv'  # Verander v5 naar v6
st.set_page_config(page_title="Hegron OEE Tool", layout="wide")

# --- ZIJBALK NAVIGATIE ---
st.sidebar.title("Navigatie")
pagina = st.sidebar.radio("Kies een optie:", ["OEE data invoeren", "Beheer"])

# PAGINA 1: OEE DATA INVOEREN
if pagina == "OEE data invoeren":
    st.title("OEE Data Invoeren")
    
    # Lijsten definieren
    machine_types = {
        "2": "Pot", "11": "Pot",
        "24": "Parfum", "25": "Parfum", "29": "Parfum", "31": "Parfum",
        "13": "Tube", "14": "Tube", "15": "Tube", "16": "Tube", 
        "17": "Tube", "18": "Tube", "19": "Tube"
    }
    machine_lijst = list(machine_types.keys())
    bandleiders = ["Marla", "Shirley", "Abdel", "Sasi", "Jennifer", "Anders"]

    # --- SECTIE 1: BASIS GEGEVENS ---
    st.subheader("1. Basisgegevens")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        datum = st.date_input("Datum", datetime.now())
    with col2:
        mach_nr = st.selectbox("Machine Nummer", machine_lijst)
        mach_type = machine_types[mach_nr]
    with col3:
        gekozen_leider = st.selectbox("Bandleidster", bandleiders)
        if gekozen_leider == "Anders":
            naam_leider = st.text_input("Naam Bandleidster")
        else:
            naam_leider = gekozen_leider
    with col4:
        aantal_mensen = st.number_input("Aantal Mensen", min_value=1, value=5)

    st.divider()

    # --- HET VASTE FORMULIER ---
    with st.form("oee_formulier", clear_on_submit=True):

        # --- SECTIE 2: PRODUCTIE & TIJD ---
        st.subheader("2. Productie & Tijd")
        c1, c2, c3 = st.columns(3)
        with c1:
            # Product nummer is optioneel (mag leeg zijn)
            prod_nummer = st.text_input("Product Nummer (Optioneel)")
            # Norm Snelheid is verplicht (> 0)
            norm_snelheid = st.number_input("Norm Snelheid (stuks/minuut) *", min_value=0)
        with c2:
            dienst_tijd = st.number_input("Totale Diensttijd (minuten) *", value=525)
            pauze = st.number_input("Geplande Pauze (minuten) *", value=45)
        with c3:
            totaal_geproduceerd = st.number_input("Totaal Aantal Stuks Geproduceerd *", min_value=0)
            # Aantal Fout is optioneel (mag 0 zijn)
            foute_producten = st.number_input("Aantal Foute Stuks (Afkeur)", min_value=0)
            
        st.divider()

        # --- SECTIE 3: STILSTANDEN ---
        st.subheader("3. Stilstanden (Minuten)")
        
        sc1, sc2 = st.columns(2)
        
        with sc1:
            st.markdown("**🔹 Geplande Stilstand**")
            # Opstarten is verplicht met standaardwaarde 5
            stop_opstart = st.number_input("Opstarten/Afsluiten *", min_value=0, value=5)
            stop_ombouw = st.number_input("Ombouw", min_value=0)
            stop_schoonmaak = st.number_input("Schoonmaken productwisseling", min_value=0)
            
        with sc2:
            st.markdown("**🔸 Ongeplande Stilstand (Verliezen)**")
            stop_monteur = st.number_input("Wachten op Monteur", min_value=0)
            stop_qc = st.number_input("Wachten op QC", min_value=0)
            stop_product = st.number_input("Wachten op Product", min_value=0)
            stop_divers = st.number_input("Diversen", min_value=0)

        st.divider()

        # --- SECTIE 4: OPMERKINGEN ---
        st.subheader("4. Opmerkingen")
        opmerking_dag = st.text_area("Bijzonderheden over deze order/dag:", height=100)

        # --- BEREKENINGEN ---
        geplande_stilstand_totaal = stop_opstart + stop_ombouw + stop_schoonmaak
        geplande_productietijd = dienst_tijd - pauze - geplande_stilstand_totaal
        
        ongeplande_stilstand_totaal = stop_monteur + stop_qc + stop_product + stop_divers
        werkelijke_draaitijd = geplande_productietijd - ongeplande_stilstand_totaal
        
        # Voorkom delen door 0
        if geplande_productietijd > 0:
            beschikbaarheid_pct = (werkelijke_draaitijd / geplande_productietijd) * 100
        else:
            beschikbaarheid_pct = 0

        # Prestatie berekening (alleen als norm snelheid is ingevuld)
        if norm_snelheid > 0:
            theoretische_max_output = werkelijke_draaitijd * norm_snelheid
            if theoretische_max_output > 0:
                prestatie_pct = (totaal_geproduceerd / theoretische_max_output) * 100
            else:
                prestatie_pct = 0
        else:
            prestatie_pct = 0
            
        goede_producten = totaal_geproduceerd - foute_producten
        if totaal_geproduceerd > 0:
            kwaliteit_pct = (goede_producten / totaal_geproduceerd) * 100
        else:
            kwaliteit_pct = 0
            
        oee_pct = (beschikbaarheid_pct/100) * (prestatie_pct/100) * (kwaliteit_pct/100) * 100

        # Live Feedback
        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Beschikbaarheid", f"{beschikbaarheid_pct:.1f}%")
        m2.metric("Prestatie", f"{prestatie_pct:.1f}%")
        m3.metric("Kwaliteit", f"{kwaliteit_pct:.1f}%")
        m4.metric("OEE Totaal", f"{oee_pct:.1f}%")

        # Opslaan knop
        submitted = st.form_submit_button("💾 Opslaan in Logboek")

        if submitted:
            # --- VALIDATIE (VERPLICHTE VELDEN CHECK) ---
            fouten = []
            
            if not naam_leider:
                fouten.append("Naam Bandleidster is verplicht.")
            if norm_snelheid <= 0:
                fouten.append("Norm Snelheid moet groter zijn dan 0.")
            if dienst_tijd <= 0:
                fouten.append("Totale Diensttijd moet ingevuld zijn.")
            # Let op: Totaal geproduceerd mag 0 zijn (als de machine hele dag stuk was), 
            # maar Aantal Mensen moet > 0 zijn.
            if aantal_mensen <= 0:
                fouten.append("Aantal mensen moet ingevuld zijn.")

            if fouten:
                for fout in fouten:
                    st.error(f"⚠️ {fout}")
                st.warning("De gegevens zijn NIET opgeslagen. Corrigeer de fouten hierboven.")
            else:
                # Alles is goed, we gaan opslaan!
               # Alles goed -> Opslaan
                # Alles goed -> Opslaan
                # Alles goed -> Opslaan
                nieuwe_regel = {
                    "Datum": [datum],
                    "Machine Nummer": [mach_nr],
                    "Machine Soort": [mach_type],
                    "Bandleider": [naam_leider],
                    "Aantal Mensen": [aantal_mensen],
                    "Product Nummer": [prod_nummer],
                    "Norm Snelheid": [norm_snelheid],
                    "Totaal Diensttijd": [dienst_tijd],
                    "Pauze": [pauze],
                    "Beschikbaarheid %": [round(beschikbaarheid_pct, 1)],
                    "Prestatie %": [round(prestatie_pct, 1)],
                    "Kwaliteit %": [round(kwaliteit_pct, 1)],
                    "OEE %": [round(oee_pct, 1)],
                    "Geplande Tijd": [geplande_productietijd],
                    "Werkelijke Draaitijd": [werkelijke_draaitijd],
                    "Theoretische Max Output": [theoretische_max_output],
                    "Totaal Geproduceerd": [totaal_geproduceerd],
                    "Goede Producten": [goede_producten],
                    "Foute Producten": [foute_producten],
                    "Stilstand Opstart": [stop_opstart],
                    "Stilstand Ombouw": [stop_ombouw],
                    "Stilstand Schoonmaak": [stop_schoonmaak],
                    "Stilstand Monteur": [stop_monteur],
                    "Stilstand QC": [stop_qc],
                    "Stilstand Product": [stop_product],
                    "Stilstand Divers": [stop_divers],
                    "Opmerking": [opmerking_dag]
                }
                
                df_save = pd.DataFrame(nieuwe_regel)
                
                if not os.path.isfile(DATA_FILE):
                    df_save.to_csv(DATA_FILE, index=False, sep=";")
                else:
                    df_save.to_csv(DATA_FILE, mode='a', header=False, index=False, sep=";")
                    
                st.success(f"✅ Gegevens voor {mach_type} lijn {mach_nr} succesvol opgeslagen!")

    # --- SCROLLBARE TABEL MET HISTORIE ---
    st.divider()
    st.subheader("Recente Invoer")

    if os.path.isfile(DATA_FILE):
        df_view = pd.read_csv(DATA_FILE, sep=";")
        df_view_sorted = df_view.iloc[::-1]
        st.dataframe(df_view_sorted, use_container_width=True, height=300)
    else:
        st.info("Nog geen data in het logboek.")

# PAGINA: BEHEER (Aanpassen & Verwijderen)
elif pagina == "Beheer":
    st.title("🛠️ Data Beheren")
    st.markdown("Pas regels aan of verwijder ze definitief na invoer van het wachtwoord.")
    st.divider()

    if os.path.isfile(DATA_FILE):
        try:
            df_beheer = pd.read_csv(DATA_FILE, sep=";")
            
            # 1. Selectie van de rij
            col_sel_1, col_sel_2 = st.columns(2)
            with col_sel_1:
                unieke_datums = sorted(df_beheer['Datum'].unique(), reverse=True)
                gekozen_datum = st.selectbox("1. Kies de datum:", unieke_datums)

            dag_data = df_beheer[df_beheer['Datum'] == gekozen_datum]
            
            if not dag_data.empty:
                with col_sel_2:
                    opties = {f"{r['Machine Soort']} {r['Machine Nummer']} ({r['Bandleider']})": i 
                              for i, r in dag_data.iterrows()}
                    gekozen_label = st.selectbox("2. Kies de specifieke regel:", list(opties.keys()))
                    index_to_edit = opties[gekozen_label]

                # 2. Wachtwoord controle
                wachtwoord = st.text_input("Voer het wachtwoord in om wijzigingen te maken:", type="password")

                if wachtwoord == "D0nderd@g18!":
                    st.success("Toegang verleend.")
                    
                    st.write("### Bewerk de gegevens in de tabel:")
                    # We maken een tijdelijke DF van 1 rij voor de editor
                    # Let op: we zorgen dat alle kolommen zichtbaar zijn
                    edited_df = st.data_editor(df_beheer.loc[[index_to_edit]], hide_index=True)

                    col_actie_1, col_actie_2 = st.columns(2)
                    
                    with col_actie_1:
                        if st.button("💾 Wijzigingen opslaan", use_container_width=True):
                            r = edited_df.iloc[0]
                            
                            # --- HERBEREKENING BIJ OPSLAAN ---
                            # Tijden
                            gepl_stilstand = r['Stilstand Opstart'] + r['Stilstand Ombouw'] + r['Stilstand Schoonmaak']
                            gepl_tijd = r['Totaal Diensttijd'] - r['Pauze'] - gepl_stilstand
                            ong_stilstand = r['Stilstand Monteur'] + r['Stilstand QC'] + r['Stilstand Product'] + r['Stilstand Divers']
                            werk_tijd = gepl_tijd - ong_stilstand
                            
                            # OEE Componenten
                            bes_pct = (werk_tijd / gepl_tijd * 100) if gepl_tijd > 0 else 0
                            max_out = werk_tijd * r['Norm Snelheid']
                            pre_pct = (r['Totaal Geproduceerd'] / max_out * 100) if max_out > 0 else 0
                            goede_p = r['Totaal Geproduceerd'] - r['Foute Producten']
                            kwa_pct = (goede_p / r['Totaal Geproduceerd'] * 100) if r['Totaal Geproduceerd'] > 0 else 0
                            
                            tot_oee = (bes_pct/100) * (pre_pct/100) * (kwa_pct/100) * 100

                            # Update originele dataframe met handmatige EN berekende data
                            df_beheer.loc[index_to_edit] = r
                            df_beheer.at[index_to_edit, 'Geplande Tijd'] = gepl_tijd
                            df_beheer.at[index_to_edit, 'Werkelijke Draaitijd'] = werk_tijd
                            df_beheer.at[index_to_edit, 'Theoretische Max Output'] = max_out
                            df_beheer.at[index_to_edit, 'Goede Producten'] = goede_p
                            df_beheer.at[index_to_edit, 'Beschikbaarheid %'] = round(bes_pct, 1)
                            df_beheer.at[index_to_edit, 'Prestatie %'] = round(pre_pct, 1)
                            df_beheer.at[index_to_edit, 'Kwaliteit %'] = round(kwa_pct, 1)
                            df_beheer.at[index_to_edit, 'OEE %'] = round(tot_oee, 1)
                            
                            df_beheer.to_csv(DATA_FILE, sep=";", index=False)
                            st.success("Gegevens bijgewerkt en herberekend!")
                            st.rerun()

                    with col_actie_2:
                        if st.button("🗑️ Regel definitief verwijderen", type="primary", use_container_width=True):
                            df_beheer = df_beheer.drop(index_to_edit)
                            df_beheer.to_csv(DATA_FILE, sep=";", index=False)
                            st.warning("Regel verwijderd.")
                            st.rerun()
                
                elif wachtwoord != "":
                    st.error("Onjuist wachtwoord.")
            else:
                st.warning("Geen data gevonden op deze datum.")

        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het lezen van het bestand: {e}")
            st.info("Tip: Verwijder het oude CSV-bestand en begin opnieuw met de nieuwe kolommen.")
    else:
        st.info("Nog geen data beschikbaar om te beheren.")
