import gc
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Panel Główny – Neuca", layout="wide")

# --------------- MENU BOCZNE ------------------
st.sidebar.title("📂 Projekt zespołowy Grupa II")
wybor_sekcji = st.sidebar.radio("Wybierz moduł analityczny:", ["Filtrowanie po ID leku", "Podstawowe analizy unikalności i sprzedaży", "Tabela udziałowa"])

# --------------- FUNKCJE ----------------------
@st.cache_data
def wczytaj_dane():
    chunksize = 100000
    df_list = []
    for chunk in pd.read_csv("pełne_dane.csv", chunksize=chunksize, index_col=0, low_memory=False):
        df_list.append(chunk)
    df = pd.concat(df_list, axis=0)
    wnioski = pd.read_csv("nazwy.csv", index_col=0)
    return df, wnioski

# --------------- Filtrowanie po leku -------------------
if wybor_sekcji == "Filtrowanie po ID leku":
    df, wnioski = wczytaj_dane()
    st.title("Filtrowanie po leku")

    unikalne_indeksy = df['Indeks'].dropna().unique()
    wybor = st.selectbox("Wybierz ID leku:", sorted(unikalne_indeksy))
    wynik = df[df['Indeks'] == wybor]

    # Nazwa leku z wnioski
    if 'Nazwa leku' in wnioski.columns and 'Indeks' in wnioski.columns:
        dopasowanie = wnioski[wnioski['Indeks'] == wybor]
        if not dopasowanie.empty:
            nazwa_leku = dopasowanie.iloc[0]['Nazwa leku']
        else:
            nazwa_leku = "Nie znaleziono"
    else:
        nazwa_leku = "Brak danych"

    st.sidebar.subheader(f"Nazwa leku dla indeksu {wybor}:")
    st.sidebar.write(f"**{nazwa_leku}**")

    # Kategorie
    kategorie = wynik['Kategoria nazwa'].dropna().unique()
    if len(kategorie) > 0:
        st.sidebar.subheader("Kategorie leku:")
        for k in kategorie:
            st.sidebar.write(f"- {k}")

    # Rodzaje promocji
    rodzaje_promocji = wynik['Rodzaj promocji poziom 2'].dropna().unique()
    if len(rodzaje_promocji) > 0:
        st.sidebar.subheader("Rodzaje promocji:")
        for r in rodzaje_promocji:
            st.sidebar.write(f"- {r}")

    # Producenci i ich nazwy
    producenci = wynik['Producent sprzedażowy kod'].dropna().unique()
    if len(producenci) > 0:
        st.sidebar.subheader("Producenci:")
        for p in producenci:
            st.sidebar.write(f"- {p}")  
    else:
        st.sidebar.write("Brak producentów.")


    st.write(f"**Liczba rekordów dla {wybor}:** {len(wynik)}")
    st.dataframe(wynik)

    st.subheader("Filtruj dane według zakresu dat")
    min_date = pd.to_datetime("2022-01-01")
    max_date = pd.to_datetime("2024-12-31")
    start_date = st.date_input("Wybierz początek okresu", value=min_date, min_value=min_date, max_value=max_date)
    end_date = st.date_input("Wybierz koniec okresu", value=max_date, min_value=min_date, max_value=max_date)

    start_rok, start_miesiac = start_date.year, start_date.month
    end_rok, end_miesiac = end_date.year, end_date.month

    dane_okres = wynik[(
        wynik['Rok'] >= start_rok) & 
        (wynik['Rok'] <= end_rok) & 
        ((wynik['Rok'] > start_rok) | (wynik['Miesiąc'] >= start_miesiac)) & 
        ((wynik['Rok'] < end_rok) | (wynik['Miesiąc'] <= end_miesiac))]

    ilosc_sprzedana = dane_okres['Sprzedaż ilość'].sum()
    wartosc_sprzedazy = dane_okres['Sprzedaż budżetowa'].sum()

    st.subheader(f"Podsumowanie dla okresu {start_date.strftime('%B %Y')} - {end_date.strftime('%B %Y')}")
    st.markdown(f"- **Suma sprzedanych sztuk:** {ilosc_sprzedana:,.0f}")
    st.markdown(f"- **Wartość sprzedaży:** {wartosc_sprzedazy:,.2f} zł")

    if start_rok in [2023, 2024] or end_rok in [2023, 2024]:
        # Liczymy dane rynkowe, ale tylko raz bierzemy pod uwagę kwotę lub ilość dla danego roku i miesiąca
        dane_rynek = dane_okres.drop_duplicates(subset=['Rok', 'Miesiąc', 'Indeks'])
        dane_rynek = dane_rynek.groupby(['Rok', 'Miesiąc']).agg({
            'Sprzedaż rynek ilość': 'sum',
            'Sprzedaż rynek wartość': 'sum'
        }).reset_index()

        ilosc_rynek = dane_rynek['Sprzedaż rynek ilość'].sum()
        wartosc_rynek = dane_rynek['Sprzedaż rynek wartość'].sum()

        st.markdown("**Dane rynkowe:**")
        st.markdown(f"- **Suma sprzedanych sztuk na rynku:** {ilosc_rynek:,.0f}")
        st.markdown(f"- **Wartość rynku:** {wartosc_rynek:,.2f} zł")

        if wartosc_rynek > 0 and ilosc_rynek > 0:
            # Wyświetlanie wykresów
            st.subheader("📊 Udział Neuca w rynku")

            # Wykres wartościowy
            fig_value = go.Figure()
            fig_value.add_trace(go.Bar(
                x=[wartosc_sprzedazy / wartosc_rynek * 100],
                y=["Wartość"],
                orientation='h',
                text=[f"{wartosc_sprzedazy / wartosc_rynek * 100:.1f}%"],
                textposition='inside',
                marker=dict(color='mediumseagreen'),
                name=f"Udział wartościowy: {wartosc_sprzedazy / wartosc_rynek * 100:.1f}%"
            ))
            fig_value.add_trace(go.Bar(
                x=[100 - wartosc_sprzedazy / wartosc_rynek * 100],
                y=["Wartość"],
                orientation='h',
                marker=dict(color='lightgray'),
                showlegend=False
            ))
            fig_value.update_layout(
                barmode='stack',
                xaxis=dict(range=[0, 100], title="Udział [%]"),
                title="Udział wartościowy Neuca w rynku",
                height=120
            )
            st.plotly_chart(fig_value, use_container_width=True)

            # Wykres ilościowy
            fig_qty = go.Figure()
            fig_qty.add_trace(go.Bar(
                x=[ilosc_sprzedana / ilosc_rynek * 100],
                y=["Ilość"],
                orientation='h',
                text=[f"{ilosc_sprzedana / ilosc_rynek * 100:.1f}%"],
                textposition='inside',
                marker=dict(color='cornflowerblue'),
                name=f"Udział ilościowy: {ilosc_sprzedana / ilosc_rynek * 100:.1f}%"
            ))
            fig_qty.add_trace(go.Bar(
                x=[100 - ilosc_sprzedana / ilosc_rynek * 100],
                y=["Ilość"],
                orientation='h',
                marker=dict(color='lightgray'),
                showlegend=False
            ))
            fig_qty.update_layout(
                barmode='stack',
                xaxis=dict(range=[0, 100], title="Udział [%]"),
                title="Udział ilościowy Neuca w rynku",
                height=120
            )
            st.plotly_chart(fig_qty, use_container_width=True)

            # Wyświetlenie wniosków
            st.sidebar.markdown(f"**Udział ilościowy:** {ilosc_sprzedana / ilosc_rynek * 100:.1f}%")
            st.sidebar.markdown(f"**Udział wartościowy:** {wartosc_sprzedazy / wartosc_rynek * 100:.1f}%")
            # Wykres sprzedaży z promocji (z podziałem na kategorie)
            sprzedaz_promocja_centralne = dane_okres[dane_okres['Rodzaj promocji poziom 2'] == 'Centralne']['Sprzedaż ilość'].sum()
            sprzedaz_promocja_partner = dane_okres[dane_okres['Rodzaj promocji poziom 2'] == 'Partner']['Sprzedaż ilość'].sum()
            sprzedaz_promocja_ipra_rpm = dane_okres[dane_okres['Rodzaj promocji poziom 2'].str.contains('regionalne pozostałe|IPRA|RPM', case=False, na=False)]['Sprzedaż ilość'].sum()
            sprzedaz_promocja_sieciowe = dane_okres[dane_okres['Rodzaj promocji poziom 2'].str.contains('sieciowe', case=False, na=False)]['Sprzedaż ilość'].sum()
            sprzedaz_promocja_zgz = dane_okres[dane_okres['Rodzaj promocji poziom 2'].str.contains('ZGZ', case=False, na=False)]['Sprzedaż ilość'].sum()
            sprzedaz_promocja_synoptis = dane_okres[dane_okres['Rodzaj promocji poziom 2'].str.contains('Synoptis - akcje własne', case=False, na=False)]['Sprzedaż ilość'].sum()

    # Całkowita sprzedaż promocyjna
            total_promocja = sprzedaz_promocja_centralne + sprzedaz_promocja_partner + sprzedaz_promocja_ipra_rpm + sprzedaz_promocja_sieciowe + sprzedaz_promocja_zgz + sprzedaz_promocja_synoptis

# Obliczanie procentów dla poszczególnych kategorii promocji
            sprzedaz_promocja_centralne_pct = (sprzedaz_promocja_centralne / total_promocja) * 100 if total_promocja else 0
            sprzedaz_promocja_partner_pct = (sprzedaz_promocja_partner / total_promocja) * 100 if total_promocja else 0
            sprzedaz_promocja_ipra_rpm_pct = (sprzedaz_promocja_ipra_rpm / total_promocja) * 100 if total_promocja else 0
            sprzedaz_promocja_sieciowe_pct = (sprzedaz_promocja_sieciowe / total_promocja) * 100 if total_promocja else 0
            sprzedaz_promocja_zgz_pct = (sprzedaz_promocja_zgz / total_promocja) * 100 if total_promocja else 0
            sprzedaz_promocja_synoptis_pct = (sprzedaz_promocja_synoptis / total_promocja) * 100 if total_promocja else 0

# Tworzenie wykresu
            fig_sprzedaz = go.Figure()

# Dodanie słupków dla każdej kategorii promocji
            fig_sprzedaz.add_trace(go.Bar(
                x=["Centralne", "Partner", "Regionalne", "Sieciowe", "ZGZ", "Synoptis"],
                y=[sprzedaz_promocja_centralne_pct, sprzedaz_promocja_partner_pct, sprzedaz_promocja_ipra_rpm_pct, 
                   sprzedaz_promocja_sieciowe_pct, sprzedaz_promocja_zgz_pct, sprzedaz_promocja_synoptis_pct],
                text=[f"{sprzedaz_promocja_centralne_pct:.1f}%", f"{sprzedaz_promocja_partner_pct:.1f}%", 
                      f"{sprzedaz_promocja_ipra_rpm_pct:.1f}%", f"{sprzedaz_promocja_sieciowe_pct:.1f}%", 
                      f"{sprzedaz_promocja_zgz_pct:.1f}%", f"{sprzedaz_promocja_synoptis_pct:.1f}%"],
                textposition='inside',
                marker=dict(color=['skyblue', 'orange', 'yellow', 'red', 'purple', 'pink']),
                name="Udziały w promocji"
                ))

# Dostosowanie wykresu
            fig_sprzedaz.update_layout(
                barmode='stack',
                title="Udział sprzedaży w promocjach (podział na kategorie)",
                xaxis_title="Rodzaj promocji",
                yaxis_title="Udział [%]",
                yaxis=dict(range=[0, 100]),
                height=400
                )   

# Wyświetlanie wykresu w Streamlit
            st.plotly_chart(fig_sprzedaz, use_container_width=True)

# Zakładając, że dane_okres i wnioski są już załadowane, wykonajmy odpowiednie obliczenia
            dane_okres['Budget_ZP'] = dane_okres['Sprzedaż budżetowa ZP'].fillna(0)
            dane_okres['Budget_Promocyjna'] = dane_okres['Sprzedaż budżetowa promocyjna'].fillna(0)
            dane_okres['Budget_Normalna'] = (dane_okres['Sprzedaż budżetowa'] - dane_okres['Budget_ZP'] - dane_okres['Budget_Promocyjna']).clip(lower=0)

# Grupowanie po leku
            podsumowanie = dane_okres.groupby('Indeks')[['Budget_ZP', 'Budget_Promocyjna', 'Budget_Normalna']].sum().reset_index()

# Dodanie kolumny 'Suma_budzetowa' (suma wszystkich składowych budżetu)
            podsumowanie['Suma_budzetowa'] = podsumowanie[['Budget_ZP', 'Budget_Promocyjna', 'Budget_Normalna']].sum(axis=1)

# Łączenie z danymi o nazwach leków
            podsumowanie = podsumowanie.merge(wnioski[['Indeks', 'Nazwa leku']], on='Indeks', how='left')

# Obliczenia procentów dla każdej kategorii budżetu
            podsumowanie['Percent_Budget_ZP'] = podsumowanie['Budget_ZP'] / podsumowanie['Suma_budzetowa'] * 100
            podsumowanie['Percent_Budget_Promocyjna'] = podsumowanie['Budget_Promocyjna'] / podsumowanie['Suma_budzetowa'] * 100
            podsumowanie['Percent_Budget_Normalna'] = podsumowanie['Budget_Normalna'] / podsumowanie['Suma_budzetowa'] * 100

# Sortowanie danych po sumie budżetowej
            df_plot = podsumowanie.sort_values(by='Suma_budzetowa', ascending=False)

# Tworzenie wykresu
            fig = go.Figure()

# Dodanie poszczególnych warstw wykresu
            fig.add_bar(
                x=df_plot['Nazwa leku'],
                y=df_plot['Budget_ZP'],
                name='ZP',
                hovertext=df_plot['Percent_Budget_ZP'].apply(lambda x: f'{x:.2f}%'),
                hoverinfo='text'
                )
            fig.add_bar(
                x=df_plot['Nazwa leku'],
                y=df_plot['Budget_Promocyjna'],
                name='Promocyjna',
                hovertext=df_plot['Percent_Budget_Promocyjna'].apply(lambda x: f'{x:.2f}%'),
                hoverinfo='text'
                )
            fig.add_bar(
                x=df_plot['Nazwa leku'],
                y=df_plot['Budget_Normalna'],
                name='Pozostała',
                hovertext=df_plot['Percent_Budget_Normalna'].apply(lambda x: f'{x:.2f}%'),
                hoverinfo='text'
                )

# Aktualizacja wyglądu wykresu (usunięcie osi pionowej)
            fig.update_layout(
                barmode='stack',
                title='Struktura sprzedaży budżetowej wg leku',
                xaxis_title='Lek',
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),  # Ukrycie osi Y
                height=600,
                showlegend=True,
                )


# Wyświetlanie wykresu w Streamlit
            st.plotly_chart(fig)
      
    with st.expander("📈 Trendy miesięczne sprzedaży"):
        dane_trendy = (
            dane_okres
            .groupby(['Rok', 'Miesiąc'])['Sprzedaż ilość']
            .sum()
            .reset_index()
        )
        dane_trendy['Data'] = pd.to_datetime(
            dane_trendy.rename(columns={'Rok': 'year', 'Miesiąc': 'month'})
            .assign(day=1)[['year', 'month', 'day']]
        )

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dane_trendy['Data'],
            y=dane_trendy['Sprzedaż ilość'],
            mode='lines+markers',
            name='Sprzedaż ilość',
            line=dict(color='royalblue')
        ))
        fig.update_layout(
            title="📦 Miesięczna sprzedaż leku",
            xaxis_title="Data",
            yaxis_title="Sprzedaż (sztuki)",
            yaxis=dict(range=[0, dane_trendy['Sprzedaż ilość'].max() * 1.1]),  # Oś Y zaczyna się od 0
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    with st.expander("📊 Średnia cena jednostkowa"):
        dane_okres['Cena jednostkowa'] = dane_okres['Sprzedaż budżetowa'] / dane_okres['Sprzedaż ilość'].replace(0, pd.NA)
        ceny = dane_okres.groupby(['Rok', 'Miesiąc'])['Cena jednostkowa'].mean().reset_index()
        ceny['Data'] = pd.to_datetime(ceny.rename(columns={'Rok': 'year', 'Miesiąc': 'month'}).assign(day=1)[['year', 'month', 'day']])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ceny['Data'], y=ceny['Cena jednostkowa'], mode='lines+markers'))
        fig.update_layout(title="Średnia cena jednostkowa miesięcznie", xaxis_title="Data", yaxis_title="Cena (PLN)",
        yaxis=dict(range=[0, ceny['Cena jednostkowa'].max() * 1.1]),height=400)
        st.plotly_chart(fig, use_container_width=True)
# --------------- Unikalnosc produktów-------------------
if wybor_sekcji == "Podstawowe analizy unikalności i sprzedaży":
        df, wnioski = wczytaj_dane()
        st.title("Analizy")
        # Zamiana NaN w kolumnie "Rodzaj promocji poziom 2" na "Normalna sprzedaż"
        df["Rodzaj promocji poziom 2"] = df["Rodzaj promocji poziom 2"].fillna("Normalna sprzedaż")

        # Tworzenie zakładek
        zakladki = st.tabs(["Unikalne produkty", "Sprzedaż produktów","Typy promocji"])

        # Zakładka 1 – Podsumowanie unikalnych wartości
        with zakladki[0]:
            st.subheader("Unikalne produkty w promocji")

            # GÓRNA SEKCJA: kategorie i rok
            kol1, kol2 = st.columns([2, 1])

            with kol1:
                st.markdown("#### Podział wg kategorii leku")
                produkty_kategoria = (
                    df.groupby("Kategoria nazwa")["Indeks"]
                    .nunique()
                    .reset_index()
                    .rename(columns={"Indeks": "Liczba unikalnych produktów"})
                    .sort_values(by="Liczba unikalnych produktów", ascending=False)
                )
                st.dataframe(produkty_kategoria, use_container_width=True)

            with kol2:
                st.markdown("#### Podział wg roku")
                produkty_rok = (
                    df.groupby("Rok")["Indeks"]
                    .nunique()
                    .reset_index()
                    .rename(columns={"Indeks": "Liczba unikalnych produktów"})
                    .sort_values(by="Rok")
                )
                st.dataframe(produkty_rok, use_container_width=True)

            # DOLNA SEKCJA: tabela + wykres
            dol1, dol2 = st.columns([2, 2])

            with dol1:
                st.markdown("#### Podział wg roku i miesiąca")
                produkty_miesiac = (
                    df.groupby(["Rok", "Miesiąc", "Kategoria nazwa"])["Indeks"]
                    .nunique()
                    .reset_index()
                    .rename(columns={"Indeks": "Liczba unikalnych produktów"})
                    .sort_values(by=["Rok", "Miesiąc"])
                )
                st.dataframe(produkty_miesiac, use_container_width=True)

            with dol2:
                st.markdown("#### Wykres: liczba unikalnych produktów wg roku i miesiąca")

                # Filtrowanie danych do wykresu
                dostepne_lata = sorted(df["Rok"].dropna().unique())
                wybrany_rok = st.selectbox("Wybierz rok", dostepne_lata, index=len(dostepne_lata) - 1)

                dostepne_kategorie = sorted(df["Kategoria nazwa"].dropna().unique())
                wybrane_kategorie = st.multiselect("Wybierz kategorię (opcjonalnie)", dostepne_kategorie, default=dostepne_kategorie)

                # Filtrowanie danych
                df_filtr = produkty_miesiac[
                    (produkty_miesiac["Rok"] == wybrany_rok) &
                    (produkty_miesiac["Kategoria nazwa"].isin(wybrane_kategorie))
                ].copy()

                df_filtr["Rok-Miesiac"] = (
                    df_filtr["Rok"].astype(str) + "-" +
                    df_filtr["Miesiąc"].astype(str).str.zfill(2)
                )

                fig = px.bar(
                    df_filtr,
                    x="Rok-Miesiac",
                    y="Liczba unikalnych produktów",
                    color="Kategoria nazwa",
                    labels={"Rok-Miesiac": "Rok-Miesiąc", "Kategoria nazwa": "Kategoria"},
                    title=f"Unikalne produkty w {wybrany_rok} (wg miesiąca)",
                    height=400
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

            # PODZIAŁ WG RODZAJU PROMOCJI
            st.markdown("#### Podział wg rodzaju promocji poziom 2")
            produkty_rodzaj = (
                df.groupby("Rodzaj promocji poziom 2")["Indeks"]
                .nunique()
                .reset_index()
                .rename(columns={"Indeks": "Liczba unikalnych produktów"})
                .sort_values(by="Liczba unikalnych produktów", ascending=False)
            )
            st.dataframe(produkty_rodzaj, use_container_width=True)

            # Tabela: unikalne promocje wg roku, miesiąca, rodzaju promocji
            st.markdown("#### Liczba unikalnych promocji wg roku, miesiąca i rodzaju promocji")
            promocje_trend = (
                df.groupby(["Rok", "Miesiąc", "Rodzaj promocji poziom 2"])["Id promocji"]
                .nunique()
                .reset_index()
                .rename(columns={"Id promocji": "Liczba unikalnych promocji"})
                .sort_values(by=["Rok", "Miesiąc"])
            )
            st.dataframe(promocje_trend, use_container_width=True)

            # Wykres liniowy dla wybranych rodzajów promocji na jednym wykresie
            st.markdown("#### Trend liczby unikalnych promocji wg rodzaju")
            wybrane_lata = sorted(promocje_trend["Rok"].unique())
            wybrany_rok_trend = st.selectbox("Wybierz rok do analizy trendu", wybrane_lata, index=len(wybrane_lata) - 1)

            df_trend_filtered = promocje_trend[promocje_trend["Rok"] == wybrany_rok_trend].copy()
            df_trend_filtered["Miesiąc"] = df_trend_filtered["Miesiąc"].astype(int)

    # Pomijanie "normalnej sprzedaży"
            df_trend_filtered = df_trend_filtered[
            df_trend_filtered["Rodzaj promocji poziom 2"].str.lower() != "normalna sprzedaż"
            ]

            dostepne_rodzaje = sorted(df_trend_filtered["Rodzaj promocji poziom 2"].unique())
            wybrane_rodzaje = st.multiselect(
                "Wybierz rodzaj(e) promocji do wyświetlenia", 
            options=dostepne_rodzaje, 
            default=dostepne_rodzaje
            )

            df_temp = df_trend_filtered[df_trend_filtered["Rodzaj promocji poziom 2"].isin(wybrane_rodzaje)]

            if not df_temp.empty:
                fig = px.line(
                    df_temp,
                    x="Miesiąc",
                    y="Liczba unikalnych promocji",
                    color="Rodzaj promocji poziom 2",
                    markers=True,
                    title=f"Trend promocji wg rodzaju ({wybrany_rok_trend})"
                )
                fig.update_layout(
                    xaxis=dict(tickmode='linear', dtick=1),
                    yaxis=dict(range=[0, df_temp["Liczba unikalnych promocji"].max() * 1.1])
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Brak danych dla wybranych rodzajów promocji.")



        # Zakładka 2 – Sprzedaż produktów
        with zakladki[1]:
            st.subheader("Sprzedaż produktów")

            # Tabela: liczba sprzedanych sztuk wg roku i miesiąca
            st.markdown("#### Liczba sprzedanych sztuk wg roku i miesiąca")
            sprzedaz_miesiac = (
                df.groupby(["Rok", "Miesiąc"])["Sprzedaż ilość"]
                .sum()
                .reset_index()
                .rename(columns={"Ilość": "Liczba sprzedanych sztuk"})
                .sort_values(by=["Rok", "Miesiąc"])
            )
            st.dataframe(sprzedaz_miesiac, use_container_width=True)

            # Tabela: liczba sprzedanych sztuk wg roku
            st.markdown("#### Liczba sprzedanych sztuk wg roku")
            sprzedaz_rok = (
                df.groupby("Rok")["Sprzedaż ilość"]
                .sum()
                .reset_index()
                .rename(columns={"Sprzedaż ilość": "Liczba sprzedanych sztuk"})
                .sort_values(by="Rok")
            )
            st.dataframe(sprzedaz_rok, use_container_width=True)

            # Wykres: liczba sprzedanych sztuk wg rodzaju promocji, miesiąca i roku
            st.markdown("#### Wykres: liczba sprzedanych sztuk wg rodzaju promocji (miesiące)")
            wybrane_lata_sprz = sorted(df["Rok"].dropna().unique())
            wybrany_rok_sprz = st.selectbox("Wybierz rok do wykresu", wybrane_lata_sprz, index=len(wybrane_lata_sprz) - 1)

            sprzedaz_trend = (
                df.groupby(["Rok", "Miesiąc", "Rodzaj promocji poziom 2"])["Sprzedaż ilość"]
                .sum()
                .reset_index()
                .rename(columns={"Sprzedaż ilość": "Liczba sprzedanych sztuk"})
            )
            df_sprz_filtered = sprzedaz_trend[sprzedaz_trend["Rok"] == wybrany_rok_sprz].copy()
            df_sprz_filtered["Miesiąc"] = df_sprz_filtered["Miesiąc"].astype(int)

            rodzaje_sprz = df_sprz_filtered["Rodzaj promocji poziom 2"].unique()
            for rodzaj in rodzaje_sprz:
                df_temp = df_sprz_filtered[df_sprz_filtered["Rodzaj promocji poziom 2"] == rodzaj]
                fig = px.line(
                    df_temp,
                    x="Miesiąc",
                    y="Liczba sprzedanych sztuk",
                    title=f"Sprzedaż: {rodzaj} ({wybrany_rok_sprz})",
                    markers=True
                )
                fig.update_layout(xaxis=dict(tickmode='linear', dtick=1),yaxis=dict(range=[0, df_temp["Liczba sprzedanych sztuk"].max() * 1.1]))
                st.plotly_chart(fig, use_container_width=True)

        with zakladki[2]:
            st.subheader("Informacje na podstawie typu promocji")

            tabela = df.groupby("Rodzaj promocji poziom 2").agg(
                liczba_obserwacji=("Rodzaj promocji poziom 2", "count"),
                suma_sprzedaz_ilosc=("Sprzedaż ilość", "sum"),
                suma_sprzedaz_promocyjna=("Sprzedaż budżetowa promocyjna", "sum"),
                suma_sprzedaz_zp=("Sprzedaż budżetowa ZP", "sum"),
                suma_sprzedaz_budzetowa=("Sprzedaż budżetowa", "sum")
            ).reset_index()

    # Formatowanie kolumn liczbowych
            tabela_formatted = tabela.copy()
            for col in tabela.columns[1:]:  # pomijamy kolumnę z nazwą promocji
                tabela_formatted[col] = tabela[col].apply(lambda x: f"{x:,.0f}".replace(",", " ").replace(".", ","))

            st.dataframe(tabela_formatted, use_container_width=True)


            # Możliwość wyboru kategorii do analizy
            dostepne_kategorie = sorted(df["Kategoria nazwa"].dropna().unique())
            
            # Użycie unikalnego klucza dla multiselect
            wybrane_kategorie = st.multiselect(
                "Wybierz kategorię (opcjonalnie)", 
                dostepne_kategorie, 
                default=dostepne_kategorie,
                key="kategorie_multiselect"  # Dodanie unikalnego klucza
            )

            # Zbiorcze dane wg rodzaju promocji i kategorii
            zbiorcze_z_kategoria = df.groupby(["Rodzaj promocji poziom 2", "Kategoria nazwa"]).agg(
                Liczba_obserwacji=("Indeks", "count"),
                Suma_sprzedaz_ilosc=("Sprzedaż ilość", "sum"),
                Suma_sprzedaz_promocyjna=("Sprzedaż budżetowa promocyjna", "sum"),
                Suma_sprzedaz_zp=("Sprzedaż budżetowa ZP", "sum"),
                Suma_sprzedaz_budzetowa=("Sprzedaż budżetowa", "sum")
            ).reset_index()

            # Filtrowanie tabeli po wybranych kategoriach
            zbiorcze_z_kategoria_filtr = zbiorcze_z_kategoria[zbiorcze_z_kategoria["Kategoria nazwa"].isin(wybrane_kategorie)]

           # Wykres słupkowy: Procentowy udział kategorii w ramach rodzaju promocji
            st.markdown("#### Udział procentowy kategorii w ramach rodzaju promocji")

            # Oblicz udział procentowy w ramach każdej grupy rodzaju promocji
            df_proc = zbiorcze_z_kategoria_filtr.copy()
            df_proc["Liczba_obserwacji"] = df_proc["Liczba_obserwacji"].astype(float)

            # Obliczenie sumy obserwacji dla każdego rodzaju promocji
            suma_obserwacji = df_proc.groupby("Rodzaj promocji poziom 2")["Liczba_obserwacji"].transform("sum")
            df_proc["Udział (%)"] = (df_proc["Liczba_obserwacji"] / suma_obserwacji) * 100
           
            fig = px.bar(
               df_proc,
               x="Rodzaj promocji poziom 2",
               y="Udział (%)",
               color="Kategoria nazwa",
               title="Udział procentowy kategorii w ramach rodzaju promocji",
               labels={"Rodzaj promocji poziom 2": "Rodzaj promocji"},
               height=400
               )   
            fig.update_layout(
               xaxis_tickangle=-45,
               barmode="stack",
               yaxis=dict(range=[0, 100])
               )
            st.plotly_chart(fig, use_container_width=True)


            # Średnia liczba sztuk na promocję wg rodzaju promocji
            st.markdown("#### Średnia liczba sztuk na promocję wg rodzaju promocji")
            srednia_na_promocje = (
                df.groupby("Rodzaj promocji poziom 2").agg({
                    "Sprzedaż ilość": "sum",
                    "Id promocji": pd.Series.nunique
                }).reset_index()
            )
            srednia_na_promocje["Średnia liczba sztuk na promocję"] = srednia_na_promocje["Sprzedaż ilość"] / srednia_na_promocje["Id promocji"]
            srednia_na_promocje = srednia_na_promocje[["Rodzaj promocji poziom 2", "Średnia liczba sztuk na promocję"]]
            st.dataframe(srednia_na_promocje, use_container_width=True)

if wybor_sekcji == "Tabela udziałowa":
   df,wnioski = wczytaj_dane()

   dane_miesieczne = df.groupby(["Rok", "Miesiąc"]).agg(
        Neuca_sprzedaz=("Sprzedaż budżetowa", "sum"),
        Rynek_sprzedaz=("Sprzedaż rynek wartość", "sum"),
        Sprzedaz_zp=("Sprzedaż budżetowa ZP", "sum"),
        Sprzedaz_promo=("Sprzedaż budżetowa promocyjna", "sum")
    ).reset_index()

    # Udział NEUCA na rynku
   dane_miesieczne["Udział NEUCA [%]"] = round(
        100 * dane_miesieczne["Neuca_sprzedaz"] / dane_miesieczne["Rynek_sprzedaz"], 2
        )

    # Struktura sprzedaży wewnątrz NEUCA
   dane_miesieczne["ZP - %"] = round(
        100 * dane_miesieczne["Sprzedaz_zp"] / dane_miesieczne["Neuca_sprzedaz"], 2
        )
   dane_miesieczne["Promo - %"] = round(
        100 * dane_miesieczne["Sprzedaz_promo"] / dane_miesieczne["Neuca_sprzedaz"], 2
        )
   dane_miesieczne["Pozostałe - %"] = 100 - dane_miesieczne["ZP - %"] - dane_miesieczne["Promo - %"]

# Wyświetlanie osobno dla każdego roku
   for rok in [2023, 2024]:
        st.subheader(f"Udział NEUCA i struktura sprzedaży wg miesięcy – {rok}")
    
        dane_rok = dane_miesieczne[dane_miesieczne["Rok"] == rok]
    
        st.dataframe(
            dane_rok[
                ["Rok", "Miesiąc", "Udział NEUCA [%]", "ZP - %", "Promo - %", "Pozostałe - %"]
                ].sort_values(["Miesiąc"]),
            use_container_width=True
            )

gc.collect()