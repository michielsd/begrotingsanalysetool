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
    filepath = f"https://raw.githubusercontent.com/michielsd/begrotingsanalysetool/refs/heads/main/Analysedata/Iv3/{jaar}_{doc.lower()}.csv"
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
def get_class_data(jaar, gemeente):
    filepath = f"https://raw.githubusercontent.com/michielsd/begrotingsanalysetool/refs/heads/main/Brondata/Gemeenteklassen/{jaar}.csv"
    
    gemeente = gemeente.replace(" (gemeente)", "")
    
    data = pd.read_csv(filepath, sep="\t")
    data = data.set_index("Gemeenten")    
    data = data.loc[gemeente]
    
    return data

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
    
    return cluster_to_iv3
    

def iv3_to_cluster(df, overhead, custom_df=None):
    
    cluster_dict = get_cluster_dict()
    
    if custom_df is not None:
        cdf = custom_df.copy()
    else:
        cdf = df.copy()
    
    for cluster, iv3_codes in cluster_dict.items():
        df.loc[cluster] = df.loc[df.index.str.startswith(iv3_codes)].sum()
        cdf.loc[cluster] = cdf.loc[cdf.index.str.startswith(iv3_codes)].sum()
    
    df = df.loc[df.index.isin(cluster_dict.keys())]
    cdf = cdf.loc[cdf.index.isin(cluster_dict.keys())]
    
    if overhead:
        overhead_row = df.loc["Overhead"]
        total_l1_1 = df["L1.1 Salarissen en sociale lasten"].sum()
        
        for index, row in df.iterrows():
            fraction = row["L1.1 Salarissen en sociale lasten"] / total_l1_1
            if index != "Overhead":
                cdf.at[index, "Lasten"] += int(overhead_row["Lasten"] * fraction)
            else:
                cdf.at[index, "Baten"] = 0
                cdf.at[index, "Lasten"] = 0
                cdf.at["Bestuur en ondersteuning", "Lasten"] += int(overhead_row["Saldo"] * fraction)
        
        cdf = cdf.assign(Saldo=cdf['Lasten'] - cdf['Baten'])
    
    cdf = cdf[['Saldo']]
    
    return cdf

def combine_into_chart(iv3_data, gf_data, gemeente):
    # Prep for concat
    iv3 = iv3_data.copy()
    gf = gf_data.copy()
    
    iv3.loc["Overige eigen middelen", "Saldo"] *= -1
    iv3.loc["Onroerendezaakbelasting", "Saldo"] *= -1
    iv3 = iv3_data.rename(columns={"Saldo": "Waarde"})
    iv3["Categorie"] = gemeente
    
    gf.loc["Overige eigen middelen", "Gemeentefonds"] *= -1
    gf.loc["Onroerendezaakbelasting", "Gemeentefonds"] *= -1
    gf = gf_data.rename(columns={"Gemeentefonds": "Waarde"})
    gf["Categorie"] = "Gemeentefonds"
    
    md = pd.concat([iv3, gf])
        
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
    md = md.sort_values(by='Categorie', key=lambda x: x == 'Gemeentefonds')
    
    chart_help = '_' + ', '.join(f'{v}: {k}' for k, v in brev_dict.items()) + '_'
    
    return md, chart_help, custom_order

def create_table(iv3_data, gf_data, jaar, gemeente):
    i = iv3_data.copy()
    g = gf_data.copy()
    
    i = i.rename(columns={"Saldo": "Netto lasten"})
    
    g.loc["Gemeentefonds"] = gf_data.sum()
    g.loc["Onroerendezaakbelasting", "Gemeentefonds"] *= -1
    g.loc["Overige eigen middelen", "Gemeentefonds"] *= -1
    
    md = pd.merge(i, g, on='Taakveld', how='outer')
    
    inkomsten = md.loc[['Onroerendezaakbelasting', 'Overige eigen middelen', 'Mutatie reserves', 'Gemeentefonds']]
    inkomsten['Netto lasten'] *= -1000
    inkomsten['Gemeentefonds'] *= -1000
    
    inkomsten['Verschil'] = inkomsten['Netto lasten'] + inkomsten['Gemeentefonds']
    
    inwoners = get_class_data(jaar, gemeente)['Inwonertal']
    inkomsten['Verschil per inwoner'] = 1000 * inkomsten['Verschil'] / inwoners 
    
    st.write(inkomsten)
    
    
    

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
    
    if "jaar" in st.session_state and "gemeente" in st.session_state and "tabel" in st.session_state:
        if selected_jaar != st.session_state["jaar"] or \
            selected_gemeente != st.session_state["gemeente"]:
            del st.session_state["tabel"]
    
    st.session_state["jaar"] = selected_jaar
    st.session_state["gemeente"] = selected_gemeente
    
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
        gemeente_iv3data = filter_iv3data(get_iv3data(selected_jaar, selected_doc), selected_gemeente) 
        
        if "tabel" in st.session_state:
            iv3_cluster_data = iv3_to_cluster(filter_iv3data(get_iv3data(
                selected_jaar, selected_doc), 
                selected_gemeente), overhead_select, st.session_state["tabel"])
        else:
            iv3_cluster_data = iv3_to_cluster(filter_iv3data(get_iv3data(
                selected_jaar, selected_doc), 
                selected_gemeente), overhead_select)
        
        # Chart
        chart_data, chart_help, cluster_order = combine_into_chart(iv3_cluster_data, gf_cluster_data, selected_gemeente)
        categorie_order = [selected_gemeente, "Gemeentefonds"]
        
        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('Taakveld:N', title='Cluster', sort=cluster_order),
            y=alt.Y('Waarde:Q', title='€ 1 mln.'),
            color=alt.Color('Categorie:N', sort=categorie_order),
            xOffset=alt.XOffset('Categorie:N', sort=categorie_order)
        )
        
        st.altair_chart(chart, use_container_width=True)
        
        st.markdown(chart_help)
        
        # Table
        table = create_table(iv3_cluster_data, gf_cluster_data, selected_jaar, selected_gemeente)
        
        
        
        

with iv3_table_container:
    h1, h2, h3 = st.columns([2, 11, 3])
    
    with h2:
        st.header("Data editor", divider="gray")
        
        gemeente_iv3data = filter_iv3data(get_iv3data(selected_jaar, selected_doc), selected_gemeente)
        tabel_data = gemeente_iv3data[["Baten", "Lasten", "Saldo"]]

        if "tabel" not in st.session_state:
            st.session_state["tabel"] = tabel_data
        
        data_editor = st.data_editor(st.session_state["tabel"], 
                                     disabled="Saldo", 
                                     height=2525, # Adjust for different Iv3-indeling
                                     use_container_width=True
                                     )
        
        if not st.session_state["tabel"].equals(data_editor):
            st.session_state["tabel"] = data_editor
            st.session_state["tabel"]['Saldo'] = st.session_state["tabel"]["Lasten"] - \
                st.session_state["tabel"]["Baten"]
            st.rerun()
                   
        # upload portal
    
# https://discuss.streamlit.io/t/update-data-in-data-editor-automatically/49839/6
