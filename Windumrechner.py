import streamlit as st
import pandas as pd
from io import StringIO
from datetime import timedelta

st.title("Umrechnung 10-min → 15-min (gewichtet, rechtsbündig)")

uploaded_file = st.file_uploader("CSV-Datei hochladen", type="csv")

if uploaded_file is not None:
    try:
        # Datei einlesen
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        df = pd.read_csv(stringio, sep=";", decimal=",")
        
        # Spaltenprüfung
        required_cols = ["Datum (Anlage)", "Zeit (Anlage)", "Wind Speed (avg)"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"Fehlende Spalten. Erwartet: {', '.join(required_cols)}")
        else:
            # Zeitstempel erstellen
            df["timestamp"] = pd.to_datetime(
                df["Datum (Anlage)"] + " " + df["Zeit (Anlage)"],
                dayfirst=True,  # Wichtig für deutsches Datumsformat (01.07.2025)
                errors="raise"  # oder "coerce" für stilles Überspringen fehlerhafter Zeilen
            )

            # Messwert vorbereiten
            df["Wind Speed (avg)"] = pd.to_numeric(df["Wind Speed (avg)"], errors="coerce")

            # Beginn- und End-Zeit für jeden 10-min-Wert berechnen
            df["end"] = df["timestamp"]
            df["start"] = df["end"] - timedelta(minutes=10)

            # Nur gültige Zeilen
            df = df.dropna(subset=["Wind Speed (avg)", "start", "end"])

            # 15-min Raster generieren
            start_time = df["start"].min().floor("15T")
            end_time = df["end"].max().ceil("15T")
            bins = pd.date_range(start=start_time, end=end_time, freq="15T")

            results = []

            for i in range(len(bins) - 1):
                interval_start = bins[i]
                interval_end = bins[i + 1]

                # Finde alle Messungen, die mit dem Intervall überlappen
                overlap = df[
                    (df["start"] < interval_end) &
                    (df["end"] > interval_start)
                ].copy()

                if not overlap.empty:
                    # Überlappungsdauer je Messung berechnen
                    overlap["overlap_minutes"] = overlap.apply(
                        lambda row: (
                            min(row["end"], interval_end) - max(row["start"], interval_start)
                        ).total_seconds() / 60,
                        axis=1
                    )

                    # Gewichteter Mittelwert berechnen
                    weighted_sum = (overlap["Wind Speed (avg)"] * overlap["overlap_minutes"]).sum()
                    total_minutes = overlap["overlap_minutes"].sum()

                    weighted_avg = weighted_sum / total_minutes if total_minutes > 0 else None
                else:
                    weighted_avg = None

                results.append({"Time": interval_end, "Wind Speed (avg)": weighted_avg})

            df_result = pd.DataFrame(results)
            df_result = df_result.dropna()

            df_result["Wind Speed (avg)"] = df_result["Wind Speed (avg)"].round(2)

            st.success("Aggregation abgeschlossen.")
            st.dataframe(df_result)

            # Download-Button
            csv = df_result.to_csv(index=False, sep=";", decimal=",").encode("utf-8")
            st.download_button(
                "Download 15-min CSV",
                data=csv,
                file_name="15min_wind_gewichtet.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Datei: {e}")
