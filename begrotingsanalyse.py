import csv

import altair as alt
import pandas as pd
import streamlit as st
import matplotlib

# Globals
JAAR_MINIMUM = 2024
JAAR_MAXIMUM = 2024


# Data import
@st.cache_resource
def get_data(filepath):
    
    data = pd.read_pickle(filepath)

    return data


# Provincie and Grootteklasse data
def get_classes():
    filepath = "gemeenteklassen.csv"

    with open(filepath, mode='r') as infile:
        reader = csv.reader(infile)
        rows = list(reader)

    provincie_dict = {row[0]: row[1] for row in rows}
    grootteklasse_dict = {row[0]: row[2] for row in rows}

    return provincie_dict, grootteklasse_dict


# Filter
@st.cache_data
def filter_data(data,
                gemeente,
                stand,
                jaarmin=JAAR_MINIMUM,
                jaarmax=JAAR_MAXIMUM,
                vergelijking=None):

    # Tuple of jaren (saved as category)
    jaar_range = tuple([str(i) for i in range(jaarmin, jaarmax + 1)])

    # Select by gemeente and Totaal/Per inwoner, no Provincie or Grootteklasse
    if not vergelijking:
        filtered_data = data[(data['Stand'] == stand)
                             & (data['Gemeenten'] == gemeente)
                             & (data['Jaar'].str.startswith(jaar_range))]

    # Select by gemeente and stand and vergelijking (Gemeente, Provincie, Grootteklasse)
    else:
        filtered_data = data[(data['Stand'] == stand)
                             & (data['Jaar'].str.startswith(jaar_range)
                                & ((data['Gemeenten'] == gemeente)
                                   | (data['Gemeenten'] == vergelijking)))]


    return filtered_data


# Wide screen
st.set_page_config(layout="wide")

# Body
header_container = st.container()

# Sidebar
with st.sidebar:
    st.header("Selecteer hier de analyse")
    
    selected_jaar = st.selectbox("Selecteer hier het begrotingsjaar",
                                 range(JAAR_MINIMUM, JAAR_MAXIMUM),
                                 key=0)


with header_container:
    ch1, ch2, ch3 = st.columns([2, 4, 2])

    with ch2:
        st.title("📊 Begrotingsanalyse")
        st.markdown(
            "Begrotingsanalyse"
        )
        )
        st.markdown(
            "Dit is een voorlopige versie, fouten voorbehouden. Vragen of opmerkingen? Stuur een mail naar <postbusiv3@minbzk.nl>."
        )


# KIES GEMEENTE
# KIES OVERHEAD
# KIES VERGELIJKING

# MIDDEN
# DATAFRAME VOOR BEPALEN BATEN / LASTEN
# GRAFIEK 

# FUNCTIE VOOR GEMEENTEFONDS
# FUNCTIE VOOR LADEN IN IV3 TOTALE BATEN LASTEN
# FUNCTIE MAKEN TOTALEN BATEN / LASTEN PER IV3

# TD: GENEREREN TOTALE BATEN/LASTEN/SALDO PER IV3 VOOR 1 JAAR
