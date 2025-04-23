import os
import csv

import pandas as pd

# Input
GF_MAP = "Brondata/GF/clusterdata/"
UF_CSV = "Brondata/GF/uitkeringsfactor.csv"
OUTPUT_MAP = "Analysedata/GF/"

def main():
    circulaires = get_gf_data(GF_MAP, UF_CSV)
    
    if circulaires:
        clusters = calculate_clusters(circulaires, UF_CSV)
        
    if clusters:
        for key, value in clusters.items():
            print(key)
            value.to_csv(OUTPUT_MAP + key + ".csv", sep=";") # ; For Nuenen Gerwen


def get_gf_data(gf_map, uf_csv):
    uf_checklist, uf_list = get_uf(uf_csv)
    
    gf_data = []
    
    gf_files = os.listdir(gf_map)
    gewichten_files = [file for file in gf_files if "gewichten" in file.lower()]
    volumina_files = [file for file in gf_files if "volumina" in file.lower()]
    siudu_files = [file for file in gf_files if "siudu" in file.lower()]
    
    for g in gewichten_files:
        volumina = any(file.startswith(g[:13]) for file in volumina_files)
        siudu = any(file.startswith(g[:13]) for file in siudu_files)
        
        if volumina and siudu and g[3:13] in uf_checklist:
            gf_data.append(g[:13])
            
    return gf_data


def calculate_clusters(circulaires, uf_csv):
    
    # Define closure to convert values to numeric, with error handling
    def safe_to_numeric(x):
        try:
            return pd.to_numeric(x)
        except ValueError:
            return x
    
    cluster_data_dict = {}
    
    for circulaire in circulaires:
        uf_checklist, uf_list = get_uf(uf_csv)
        
        df_gewichten = pd.read_csv(GF_MAP + circulaire + "_Gewichten.csv", sep='\t', decimal=',', thousands='.') 
        df_volumina = pd.read_csv(GF_MAP + circulaire + "_Volumina.csv", sep='\t', decimal=',', thousands='.')
        df_siudu = pd.read_csv(GF_MAP + circulaire + "_SIUDU.csv", sep='\t', decimal=',', thousands='.')
        
        # Define indices, set to numeric
        df_gewichten = df_gewichten.set_index("Codering maatstaf")
        df_volumina = df_volumina.set_index("Naam")
        df_siudu = df_siudu.set_index("Naam")
        
        df_gewichten = df_gewichten.apply(safe_to_numeric)
        df_volumina = df_volumina.apply(safe_to_numeric)
        df_siudu = df_siudu.apply(safe_to_numeric)
        
        # Take clusters from gewichten
        clusters = list(df_gewichten.columns[1:])
        
        # Take uitkeringsfactor from circulaire
        uf = float([row for row in uf_list if row.startswith(circulaire[3:])][0][11:])
        
        # Calculate cluster totals per gemeente
        outputdict = {}
        for i, r in df_volumina.iterrows():
            linedict = {}
    
            gemeente = r.name
            
            # Create dicts for volumina/siudu column names and values per gemeente
            volumina_columns = df_volumina.columns[2:]
            volumina_values = r[2:].values
            volumina_dict = {v: w for v, w in zip(volumina_columns, volumina_values)}
            
            siudu_columns = df_siudu.columns[2:]
            siudu_values = df_siudu.loc[gemeente].values[2:]
            siudu_dict = {v: w for v, w in zip(siudu_columns, siudu_values)}
            
            for c in clusters:
        
                # Create dicts for gewichten column names and values per gemeente where index != nan (excludes IUDU)
                gewichten_rows = df_gewichten.index[df_gewichten.index.notna()]
                gewichten_per_cluster = df_gewichten[c][df_gewichten.index.notna()].values
                gewichten_dict = {v: w for v, w in zip(gewichten_rows, gewichten_per_cluster)}
                
                # SIUDU gewichten: ART 12 added manually to cluster Overig
                siudu_gewichten_namen = list(df_gewichten[df_gewichten.index.isna()]['Naam maatstaf'])
                siudu_gewichten = list(df_gewichten[df_gewichten.index.isna()][c])
                siudu_gewichten_dict = {v: w for v, w in zip(siudu_gewichten_namen, siudu_gewichten)}
                
                cluster_total = 0

                # Match dict keys of gewichten and volumina for AU clusters
                if len(gewichten_dict) == len(volumina_dict):
                    for key in gewichten_dict.keys():
                        if key in volumina_dict:
                            ufactor = 1 if "woz" in key.lower() else uf
                            cluster_total += ufactor * gewichten_dict[key] * volumina_dict[key]
                
                # Match dict keys of gewichten and volumina for SIUDU
                if len(siudu_gewichten_dict) == len(siudu_dict):
                    for key in siudu_gewichten_dict.keys():
                        if key in siudu_dict:
                            cluster_total += siudu_gewichten_dict[key] * siudu_dict[key]
                
                linedict[c] = cluster_total
                    
            outputdict[gemeente] = linedict
            
        df = pd.DataFrame(outputdict).T
        df = df.reset_index()
        df = df.rename(columns={"index": "Gemeenten"})
        
        # Calculate total row correctly by summing each column
        total_row = pd.DataFrame({
            'Gemeenten': ['Nederland'],
            **{col: [df[col].sum()] for col in df.columns if col != 'Gemeenten'}
        })
        
        # Concatenate the total row to the dataframe
        df = pd.concat([df, total_row], ignore_index=True)

        cluster_data_dict[circulaire] = df
    return cluster_data_dict
        

def get_uf(uf_csv):
    with open(uf_csv, mode='r', encoding='utf-8', ) as file:
        csv_reader = csv.reader(file)
        uf_list = list(csv_reader)[1:]
    
    uf_checklist = ["_".join(row[:-1]) for row in uf_list]
    uf_list = ["_".join(row) for row in uf_list]
    
    return uf_checklist, uf_list


        
     
if __name__ == "__main__":
    main()
