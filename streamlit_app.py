import csv

import altair as alt
import pandas as pd
import streamlit as st
import matplotlib

# Globals
JAAR_MINIMUM = 2024
JAAR_MAXIMUM = 2024
LAATSTE_JR = 2023
LAATSTE_CRE = "S2024"

############################################################################

############################################################################

def safe_to_numeric(x):
    try:
        return pd.to_numeric(x)
    except ValueError:
        return x

# Data import
@st.cache_resource
def get_iv3data(jaar, doc):
    filepath = f"https://raw.githubusercontent.com/michielsd/begrotingsanalysetool/refs/heads/main/Analysedata/Iv3/{jaar}_{doc}.csv"
    data = pd.read_csv(filepath, sep=";")

    return data

@st.cache_data
def filter_iv3data(data, gemeente):
    
    # Filter out gemeente
    filtered_data = data[data['Gemeenten'] == gemeente]
    
    # Calculate saldo
    filtered_data = filtered_data.assign(Saldo=filtered_data['Lasten'] - filtered_data['Baten'])
        
    # Drop superfluous columns
    filtered_data = filtered_data.drop(columns=["Gemeenten", "Provincie", "Gemeentegrootte", "Stedelijkheid", "Inwonertal"])
    filtered_data = filtered_data.set_index("Taakveld")
    
    filtered_data = filtered_data.apply(safe_to_numeric)
    filtered_data = filtered_data.map(lambda x: x / 1000 if pd.api.types.is_numeric_dtype(type(x)) else x)
    
    return filtered_data

@st.cache_resource
def get_gfdata(gf_path):
    filepath = f"https://raw.githubusercontent.com/michielsd/begrotingsanalysetool/refs/heads/main/Analysedata/GF/GF_{gf_path}.csv"
    data = pd.read_csv(filepath, sep=";")
    
    return data

@st.cache_data
def filter_gfdata(data, gemeente):
    
    # Filter out gemeente
    filtered_data = data[data['Gemeenten'] == gemeente].T
    filtered_data = filtered_data.reset_index()
    filtered_data = filtered_data.rename(columns={"index": "Taakveld"})
    filtered_data = filtered_data.set_index("Taakveld")
    filtered_data = filtered_data.rename(columns={filtered_data.columns[0]: "Gemeentefonds"})
    
    # Drop first two rows plus last one (name, total)
    filtered_data = filtered_data.iloc[2:-1]
    
    # Convert all numerical values to numeric and divide by 1,000,000
    filtered_data = filtered_data.apply(safe_to_numeric)
    filtered_data = filtered_data.map(lambda x: x / 1000000 if pd.api.types.is_numeric_dtype(type(x)) else x)
    
    filtered_data.loc["Overige eigen middelen", "Gemeentefonds"] *= -1
    filtered_data.loc["Onroerendezaakbelasting", "Gemeentefonds"] *= -1
    
    return filtered_data

def get_circulaires(jaar):
    circulaire_dict = {}
    
    laatste_jaar = int(LAATSTE_CRE[1:])
    vorig_jaar = int(jaar) - 1
    laatste_maand = "Mei" if LAATSTE_CRE[0] == "M" else "September"
    
    # If no circulaires for jaar: september circulaire last year
    if int(jaar) > laatste_jaar:
        circulaire_dict[f"September {laatste_jaar}"] = f"S{laatste_jaar}_{jaar}"
    # If circulaire in jaar and laatste circulaire is Mei
    elif int(jaar) == laatste_jaar and laatste_maand == "Mei":
        circulaire_dict[f"Mei {jaar}"] = f"M{laatste_jaar}_{jaar}"
        circulaire_dict[f"September {vorig_jaar}"] = f"S{vorig_jaar}_{jaar}"
    elif int(jaar) == laatste_jaar and laatste_maand == "September":
        circulaire_dict[f"September {jaar}"] = f"S{jaar}_{jaar}"
        #circulaire_dict[f"Mei {jaar}"] = f"M{laatste_jaar}_{jaar}"
        #circulaire_dict[f"September {vorig_jaar}"] = f"S{vorig_jaar}_{jaar}"
    
    circulaire_list = circulaire_dict.keys()
    
    return circulaire_list, circulaire_dict


def get_cluster_dict():
    
    # GF names to tuples w/ Iv3-taakvelden
    cluster_to_iv3 = {
        "Sociale basisvoorzieningen" : ("6.1", "6.2", "7.1"),
        "Participatie": ("6.3", "6.4", "6.5"),
        "Individuele voorzieningen Wmo": ("6.6", "6.71", "6.82"),
        "Individuele voorzieningen Jeugd": ("6.72", "6.73", "6.74", "6.82"),
        "Bestuur en ondersteuning": ("0.1 ", "0.2"), # Spatie achter 0.1
        "Orde en veiligheid": ("1."),
        "Onderwijs": ("4."),
        "Sport, cultuur en recreatie": ("5."),
        "Infrastructuur, ruimte en milieu": ("0.63", "0.9", "2.", "3.", "7.2", "7.3", "7.4", "8.1", "8.3"),
        "Overig": ("Dummy"), # Dummy variable
        "Overige eigen middelen": ("0.11", "0.3", "0.5", "0.64", "0.8", "8.2"),
        "Onroerendezaakbelasting": ("0.61", "0.62"),
        "Overhead" : ("0.4"),
        "Gemeentefonds" : ("0.7"),
        "Mutatie reserves": ("0.10"), # Waarom hier niet 0.11 bij?
    }
    
    cluster_to_afk = {
        "Individuele voorzieningen Wmo": "Wmo",
        "Individuele voorzieningen Jeugd": "Jeugd",
        "Overige eigen middelen": "OEM",
        "Onroerendezaakbelasting": "OZB",
    }
    
    return cluster_to_iv3, cluster_to_afk
    

def iv3_to_cluster(df, overhead):
    
    cluster_dict, cluster_afk = get_cluster_dict()
    
    for cluster, iv3_codes in cluster_dict.items():
        df.loc[cluster] = df.loc[df.index.str.startswith(iv3_codes)].sum()
    
    df = df.loc[df.index.isin(cluster_dict.keys())]
    
    if overhead:
        overhead_row = df.loc["Overhead"]
        total_l1_1 = df["L1.1 Salarissen en sociale lasten"].sum()
        
        for index, row in df.iterrows():
            fraction = row["L1.1 Salarissen en sociale lasten"] / total_l1_1
            if index != "Overhead":
                df.at[index, "Lasten"] += int(overhead_row["Lasten"] * fraction)
            else:
                df.at[index, "Baten"] = 0
                df.at[index, "Lasten"] = 0
                df.at["Bestuur en ondersteuning", "Lasten"] += int(overhead_row["Saldo"] * fraction)
        
        df = df.assign(Saldo=df['Lasten'] - df['Baten'])
    
    df.loc["Overige eigen middelen", "Saldo"] *= -1
    df.loc["Onroerendezaakbelasting", "Saldo"] *= -1
    
    df = df[['Saldo']]
    
    return df

def combine_into_chart(iv3_data, gf_data, gemeente):
    # Prep for concat
    iv3_data = iv3_data.rename(columns={"Saldo": "Waarde"})
    iv3_data["Categorie"] = gemeente
    gf_data = gf_data.rename(columns={"Gemeentefonds": "Waarde"})
    gf_data["Categorie"] = "Gemeentefonds"
    
    md = pd.concat([iv3_data, gf_data])
        
    brev_dict = {
        "Onroerendezaakbelasting": "OZB",
        "Overige eigen middelen": "OEM",
        "Bestuur en ondersteuning": "Bestuur",
        "Sociale basisvoorzieningen": "SB",
        "Participatie": "Participatie",
        "Individuele voorzieningen Wmo": "Wmo",
        "Individuele voorzieningen Jeugd": "Jeugd", 
        "Orde en veiligheid": "Orde",
        "Onderwijs": "Onderwijs",
        "Sport, cultuur en recreatie": "SCR",
        "Infrastructuur, ruimte en milieu": "IRM",
        "Overhead": "Overhead",
    }
    
    select_list = tuple(brev_dict.keys())
    custom_order = tuple(brev_dict.values())
    
    md = md[md.index.isin(select_list)]
    md.index = md.index.map(brev_dict)
    md = md.reset_index()
    
    chart_help = ', '.join(f'{v}: {k}' for k, v in brev_dict.items())
    
    return md, chart_help, custom_order


############################################################################

############################################################################

# Wide screen
st.set_page_config(layout="wide")

# Body
header_container = st.container()
chart_container = st.container()
iv3_table_container = st.container()

# Sidebar
with st.sidebar:
    st.header("Analyse")
    
    sidebar_jaren = [str(i) for i in range(JAAR_MINIMUM, JAAR_MAXIMUM+1)]
    selected_jaar = st.selectbox("Selecteer het begrotingsjaar",
                                 sidebar_jaren,
                                 index=0,
                                 key=0)
    
    sidebar_gemeenten = get_iv3data(selected_jaar, "begroting").Gemeenten.unique()
    selected_gemeente = st.selectbox("Selecteer de gemeente",
                                 sidebar_gemeenten,
                                 key=1)
    
    documenten = ["Begroting", "Jaarrekening"] if int(selected_jaar) <= LAATSTE_JR else ["Begroting"]
    selected_doc = st.selectbox("Begroting- of jaarrekeningdata?",
                            documenten,
                            key=2)


with header_container:
    h1, h2, h3 = st.columns([2, 4, 2])

    with h2:
        st.title("📊 Begrotingsanalyse")
        st.markdown(
            "Begrotingsanalyse"
        )
        st.markdown(
            "Dit is een voorlopige versie, fouten voorbehouden. Vragen of opmerkingen? Stuur een mail naar <postbusiv3@minbzk.nl>."
        )


with chart_container:
    h1, h2, h3 = st.columns([1, 4, 1])
    
    with h2:
        circulaires, circulaire_dict = get_circulaires(selected_jaar)
        selected_circulaire = st.selectbox("Selecteer de circulaire",
                                 circulaires,
                                 index=0,
                                 key=3)
        overhead_select = st.toggle("Overhead toegedeeld?")
    
        gf_cluster_data = filter_gfdata(get_gfdata(circulaire_dict[selected_circulaire]), selected_gemeente)
        iv3_cluster_data = iv3_to_cluster(filter_iv3data(get_iv3data(selected_jaar, selected_doc), selected_gemeente), overhead_select)
        chart_data, chart_help, custom_order = combine_into_chart(iv3_cluster_data, gf_cluster_data, selected_gemeente)
        
        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('Taakveld:N', title='Cluster', sort=custom_order),
            y=alt.Y('Waarde:Q', title='€ 1 mln.'),
            color='Categorie:N',
            xOffset='Categorie:N',
        )
        
        st.altair_chart(chart, use_container_width=True)
        
        st.markdown(chart_help)
        

with iv3_table_container:
    h1, h2, h3 = st.columns([2, 4, 2])
    
    with h2:
        
        with st.form("data_editor_form"):
            submit_button = st.form_submit_button("Update de grafiek")
            gemeente_iv3data = filter_iv3data(get_iv3data(selected_jaar, selected_doc), selected_gemeente)
            tabel_data = gemeente_iv3data[["Baten", "Lasten", "Saldo"]]
            
            st.data_editor(tabel_data, disabled=["Saldo"], use_container_width=True,)
            
            if submit_button:
                pass
    
# https://discuss.streamlit.io/t/update-data-in-data-editor-automatically/49839/6
