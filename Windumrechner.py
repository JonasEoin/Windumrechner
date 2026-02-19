import streamlit as st
import pandas as pd
from datetime import timedelta

st.title("10-min → 15-min Winddaten-Umrechner (gewichtet)")

# Datei-Upload
uploaded_file = st.file_uploader("CSV-Datei hochladen", type=["csv"])

# Ausrichtung-Auswahl
input_alignment = st.selectbox(
    "Ausrichtung der Eingangsdaten (10-min-Werte)",
    ["rechtsbündig (Senvion, Enercon, Vestas)", "linksbündig (Nordex)"]
)

output_alignment = st.selectbox(
    "Ausrichtung der Ausgangsdaten (15-min-Werte)",
    ["rechtsbündig (Standard)", "linksbündig"]
)

if uploaded_file:
    # Rohdaten einlesen (immer unverändert)
    df_raw = pd.read_csv(
        uploaded_file,
        sep=";",
        decimal=","
    )

    # Spalten prüfen
    required_cols = ["Datum (UTC, Anlage)", "Zeit (UTC, Anlage)", "Wind Speed (avg)"]
    if not all(col in df_raw.columns for col in required_cols):
        st.error(f"Fehlende Spalten. Erwartet werden: {', '.join(required_cols)}")
    else:
        # Leere Messwerte durch 0 ersetzen
        df_raw["Wind Speed (avg)"] = pd.to_numeric(df_raw["Wind Speed (avg)"], errors="coerce").fillna(0)
        
        # Kopie der Rohdaten für Berechnung
        df = df_raw.copy()

        # Timestamp erstellen
        df["timestamp"] = pd.to_datetime(df["Datum (UTC, Anlage)"] + " " + df["Zeit (UTC, Anlage)"],
                                         dayfirst=True,  # Wichtig für deutsches Datumsformat (01.07.2025)
                                         errors="raise"  # oder "coerce" für stilles Überspringen fehlerhafter Zeilen
        )

        # Eingangsausrichtung berücksichtigen
        if input_alignment == "rechtsbündig (Senvion, Enercon, Vestas)":
            df["timestamp"] -= timedelta(minutes=10)

        # Nur benötigte Spalten behalten
        df = df[["timestamp", "Wind Speed (avg)"]].copy()

        # 15-min Aggregation mit Gewichtung
        results = []
        start_time = df["timestamp"].min().floor("15T")
        end_time = df["timestamp"].max().ceil("15T")

        current_time = start_time
        while current_time < end_time:
            interval_end = current_time + timedelta(minutes=15)

            # Alle relevanten 10-min-Daten finden (max. 10 Min Überhang)
            mask = (df["timestamp"] >= current_time) & (df["timestamp"] < interval_end + timedelta(minutes=10))
            subset = df[mask]

            if len(subset) > 0:
                weighted_sum = 0
                total_minutes = 0
                for _, row in subset.iterrows():
                    ts = row["timestamp"]
                    val = row["Wind Speed (avg)"]
                    # Intervalllänge bestimmen
                    start_10min = ts
                    end_10min = ts + timedelta(minutes=10)
                    overlap_start = max(start_10min, current_time)
                    overlap_end = min(end_10min, interval_end)
                    minutes = (overlap_end - overlap_start).total_seconds() / 60
                    if minutes > 0:
                        weighted_sum += val * minutes
                        total_minutes += minutes

                avg_value = weighted_sum / total_minutes if total_minutes > 0 else None
                results.append([current_time, round(avg_value, 2)])

            current_time = interval_end

        df_out = pd.DataFrame(results, columns=["timestamp", "Wind Speed (avg)"])

        # Ausgangsausrichtung berücksichtigen
        if output_alignment == "rechtsbündig (Standard)":
            df_out["timestamp"] += timedelta(minutes=15)

        # Zeitstempel formateiren

        df_out["timestamp"] = df_out["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        st.subheader("Ergebnis")
        st.dataframe(df_out)

        # Download-Link
        csv_out = df_out.to_csv(index=False, sep=";", decimal=",")
        st.download_button(
            "Ergebnis herunterladen",
            csv_out,
            file_name="wind_15min.csv",
            mime="text/csv"
        )

        






        





