import streamlit as st
import pandas as pd
from lib import (
    calc_hourwages, init_db, save_scenario, 
    get_all_scenarios, delete_scenario,
    format_number
)

# Initialize the database
init_db()

# Set page title and configuration
st.set_page_config(
    page_title="Stundenlohn Kalkulator",
    page_icon="💰",
    layout="wide"
)

# Title and description
st.title("Stundenlohn Kalkulator")
st.markdown("""
Diese Anwendung berechnet Stundensätze basierend auf verschiedenen Eingabeparametern.
Sie können mehrere Szenarien speichern und vergleichen.
""")

# Create tabs for different functionalities
tab1, tab2, tab3 = st.tabs(["Kalkulation", "Gespeicherte Szenarien", "Vergleich"])

with tab1:
    st.header("Stundensatz Kalkulation")

    # Input fields with automatic calculation
    col1, col2 = st.columns(2)

    with col1:
        worker_amount = st.number_input(
            "Anzahl Mitarbeitende", 
            min_value=1, 
            value=8,
            help="Anzahl der Mitarbeitenden im Unternehmen"
        )

        individual_costs = st.number_input(
            "Einzelkosten pro MA (€)", 
            min_value=0.0, 
            value=60000.0,
            help="Jährliche Kosten pro Mitarbeiter:in (z.B. Gehalt, Sozialabgaben)"
        )

        overhead_costs = st.number_input(
            "Gemeinkosten (€)", 
            min_value=0.0, 
            value=230000.0,
            help="Jährliche Gemeinkosten des Unternehmens (z.B. Miete, Verwaltung)"
        )

    with col2:
        hours = st.number_input(
            "Fakturierbare Stunden pro MA", 
            min_value=0.1, 
            value=1512.0,
            help="Jährliche fakturierbare Stunden pro Mitarbeiter:in"
        )

        earning_percentage = st.number_input(
            "Gewinnaufschlag (%)", 
            min_value=0.0, 
            max_value=100.0, 
            value=15.0,
            help="Gewinnaufschlag in Prozent"
        ) / 100.0

        vat_percentage = st.number_input(
            "Mehrwertsteuersatz (%)", 
            min_value=0.0, 
            max_value=100.0, 
            value=19.0,
            help="Mehrwertsteuersatz in Prozent"
        ) / 100.0

        geld_f_chefchen = st.checkbox(
            "Verdampfung",
            value=False,
            help="Hiermit können Sie aktivieren das Geld verdampft und sich beim Chef Kondensiert."
        )

    # Calculate and display results automatically
    try:
        selbstkostensatz, netto, brutto, netto_selbst_diff, chef_kondensat = calc_hourwages(
            worker_amount, individual_costs, overhead_costs, 
            hours, earning_percentage, vat_percentage, geld_f_chefchen
        )

        # Display results in a nice format
        st.markdown("### Ergebnisse")
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Selbstkostensatz", f"{format_number(selbstkostensatz)} €/h")

        with col2:
            st.metric("Netto-Stundensatz", f"{format_number(netto)} €/h")

        with col3:
            st.metric("Netto-Selbstkosten Diff.", f"{format_number(netto_selbst_diff)} €/h")

        with col4:
            st.metric("Brutto-Stundensatz", f"{format_number(brutto)} €/h")


            with col5:
                if geld_f_chefchen:
                    st.metric("Sonstige", f"{format_number(chef_kondensat)} €/h")
                else:
                    st.metric("Sonstige", "0.00 €/h")

        # Save scenario option
        with st.expander("Szenario speichern"):
            with st.form("save_scenario_form"):
                scenario_name = st.text_input("Szenario-Name", "Mein Szenario")
                scenario_description = st.text_area("Beschreibung", "", help="Optionale Beschreibung des Szenarios")
                save_button = st.form_submit_button("Speichern")

                if save_button and scenario_name:
                    try:
                        scenario_id = save_scenario(
                            scenario_name, worker_amount, individual_costs, 
                            overhead_costs, hours, earning_percentage, vat_percentage,
                            description=scenario_description, chef=geld_f_chefchen
                        )
                        if scenario_id > 0:
                            st.success(f"Szenario '{scenario_name}' erfolgreich gespeichert!")
                        else:
                            st.error("Fehler beim Speichern des Szenarios.")
                    except Exception as e:
                        st.error(f"Fehler beim Speichern: {str(e)}")
    except Exception as e:
        st.error(f"Berechnungsfehler: {str(e)}")
        st.info("Bitte überprüfen Sie Ihre Eingaben und stellen Sie sicher, dass keine Division durch Null erfolgt.")

with tab2:
    st.header("Gespeicherte Szenarien")

    # Refresh button
    if st.button("Aktualisieren"):
        st.rerun()

    try:
        # Get all scenarios
        scenarios = get_all_scenarios()

        if not scenarios:
            st.info("Keine Szenarien gespeichert. Berechnen und speichern Sie ein Szenario im Tab 'Kalkulation'.")
        else:
            try:
                # Convert to DataFrame for better display
                df = pd.DataFrame(scenarios)

                # Rename columns for better display
                df = df.rename(columns={
                    'id': 'ID',
                    'name': 'Name',
                    'description': 'Beschreibung',
                    'worker_amount': 'Anzahl MA',
                    'individual_costs': 'Kosten pro MA (€)',
                    'overhead_costs': 'Gemeinkosten (€)',
                    'hours': 'Stunden pro MA',
                    'earning_percentage': 'Gewinn (%)',
                    'vat_percentage': 'MwSt (%)',
                    'selbstkostensatz': 'Selbstkostensatz (€/h)',
                    'netto': 'Netto (€/h)',
                    'brutto': 'Brutto (€/h)',
                    'netto_selbstkosten_diff': 'Netto-Selbstkosten Diff. (€/h)',
                    'geld_fuer_chefchen': 'Geld für Chefchen (€/h)',
                    'created_at': 'Erstellt am'
                })

                # Format percentages
                df['Gewinn (%)'] = df['Gewinn (%)'] * 100
                df['MwSt (%)'] = df['MwSt (%)'] * 100

                # Format numeric columns with thousand separators
                for col in ['Kosten pro MA (€)', 'Gemeinkosten (€)', 'Selbstkostensatz (€/h)', 'Netto (€/h)', 'Brutto (€/h)', 'Netto-Selbstkosten Diff. (€/h)']:
                    if col in df.columns:
                        df[col] = df[col].apply(lambda x: format_number(x, decimal_places=2))

                # Display the DataFrame
                st.dataframe(df)

                # Delete scenario option
                with st.expander("Szenario löschen"):
                    with st.form("delete_scenario_form"):
                        scenario_id_to_delete = st.selectbox(
                            "Szenario auswählen", 
                            options=[(s['id'], s['name']) for s in scenarios],
                            format_func=lambda x: f"{x[0]} - {x[1]}"
                        )

                        delete_button = st.form_submit_button("Löschen")

                        if delete_button and scenario_id_to_delete:
                            try:
                                if delete_scenario(scenario_id_to_delete[0]):
                                    st.success(f"Szenario '{scenario_id_to_delete[1]}' erfolgreich gelöscht!")
                                    st.rerun()
                                else:
                                    st.error("Fehler beim Löschen des Szenarios.")
                            except Exception as e:
                                st.error(f"Fehler beim Löschen: {str(e)}")
            except Exception as e:
                st.error(f"Fehler bei der Darstellung der Szenarien: {str(e)}")
    except Exception as e:
        st.error(f"Fehler beim Laden der Szenarien: {str(e)}")
        st.info("Bitte versuchen Sie es später erneut oder prüfen Sie die Datenbankverbindung.")

with tab3:
    st.header("Szenarien vergleichen")

    try:
        # Get all scenarios
        scenarios = get_all_scenarios()

        if len(scenarios) < 2:
            st.info("Sie benötigen mindestens zwei gespeicherte Szenarien für einen Vergleich.")
        else:
            # Allow selecting multiple scenarios to compare
            selected_scenario_ids = st.multiselect(
                "Szenarien zum Vergleich auswählen",
                options=[(s['id'], s['name']) for s in scenarios],
                format_func=lambda x: f"{x[0]} - {x[1]}"
            )

            if selected_scenario_ids:
                try:
                    # Get the selected scenarios
                    selected_scenarios = [s for s in scenarios if (s['id'], s['name']) in selected_scenario_ids]

                    if selected_scenarios:
                        try:
                            # Convert to DataFrame for comparison
                            comparison_df = pd.DataFrame(selected_scenarios)

                            # Calculate the difference between Netto and Selbstkostensatz
                            comparison_df['netto_selbstkosten_diff'] = comparison_df['netto'] - comparison_df['selbstkostensatz']

                            # Rename columns for better display
                            comparison_df = comparison_df.rename(columns={
                                'id': 'ID',
                                'name': 'Name',
                                'description': 'Beschreibung',
                                'worker_amount': 'Anzahl MA',
                                'individual_costs': 'Kosten pro MA (€)',
                                'overhead_costs': 'Gemeinkosten (€)',
                                'hours': 'Stunden pro MA',
                                'earning_percentage': 'Gewinn (%)',
                                'vat_percentage': 'MwSt (%)',
                                'selbstkostensatz': 'Selbstkostensatz (€/h)',
                                'netto': 'Netto (€/h)',
                                'brutto': 'Brutto (€/h)',
                                'netto_selbstkosten_diff': 'Netto-Selbstkosten Diff. (€/h)',
                                'created_at': 'Erstellt am'
                            })

                            # Format percentages
                            comparison_df['Gewinn (%)'] = comparison_df['Gewinn (%)'] * 100
                            comparison_df['MwSt (%)'] = comparison_df['MwSt (%)'] * 100

                            # Create a copy of numeric columns for styling before formatting
                            numeric_cols = ['Kosten pro MA (€)', 'Gemeinkosten (€)', 'Selbstkostensatz (€/h)', 
                                           'Netto (€/h)', 'Brutto (€/h)', 'Netto-Selbstkosten Diff. (€/h)']

                            # Round numeric columns to 2 decimal places in the styling dataframe
                            for col in numeric_cols:
                                if col in comparison_df.columns:
                                    comparison_df[col] = comparison_df[col].round(2)

                            # Create a copy for styling after rounding
                            styling_df = comparison_df.copy()

                            # Convert all numeric values in styling_df to strings to avoid styling errors
                            for col in numeric_cols:
                                if col in styling_df.columns:
                                    styling_df[col] = styling_df[col].astype(str)

                            # Format numeric columns with thousand separators
                            for col in numeric_cols:
                                if col in comparison_df.columns:
                                    comparison_df[col] = comparison_df[col].apply(lambda x: format_number(x, decimal_places=2))

                            # Create a styled dataframe to highlight min/max values
                            if len(selected_scenarios) >= 2:
                                # Function to highlight the maximum value in a Series
                                def highlight_max(s):
                                    # Convert back to float for comparison if the series contains strings
                                    if s.dtype == 'object':
                                        try:
                                            numeric_s = s.astype(float)
                                            is_max = numeric_s == numeric_s.max()
                                        except:
                                            is_max = [False] * len(s)
                                    else:
                                        is_max = s == s.max()
                                    return ['background-color: #90EE90' if v else '' for v in is_max]

                                # Function to highlight the minimum value in a Series
                                def highlight_min(s):
                                    # Convert back to float for comparison if the series contains strings
                                    if s.dtype == 'object':
                                        try:
                                            numeric_s = s.astype(float)
                                            is_min = numeric_s == numeric_s.min()
                                        except:
                                            is_min = [False] * len(s)
                                    else:
                                        is_min = s == s.min()
                                    return ['background-color: #CC0000' if v else '' for v in is_min]

                                # Apply styling to numeric columns only
                                styled_df = styling_df.style
                                for col in numeric_cols:
                                    if col in styling_df.columns and len(styling_df[col].unique()) > 1:
                                        styled_df = styled_df.apply(highlight_max, subset=[col])
                                        styled_df = styled_df.apply(highlight_min, subset=[col])

                                # Display the styled comparison dataframe
                                st.write("Vergleich der Szenarien (Höchstwerte in Grün, Tiefstwerte in Rot):")
                                st.dataframe(styled_df)
                            else:
                                # Display the comparison without styling if less than 2 scenarios
                                st.dataframe(comparison_df)

                        except Exception as e:
                            st.error(f"Fehler bei der Verarbeitung der Vergleichsdaten: {str(e)}")
                except Exception as e:
                    st.error(f"Fehler bei der Auswahl der Szenarien: {str(e)}")
    except Exception as e:
        st.error(f"Fehler beim Laden der Szenarien: {str(e)}")
        st.info("Bitte versuchen Sie es später erneut oder prüfen Sie die Datenbankverbindung.")

# Footer
st.markdown("---")
st.markdown("◬ 2025 Stundenlohn Kalkulator von DerVogel101.")
