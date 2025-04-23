import os
import csv
from pathlib import Path

import pandas as pd

# Globals
IV3_MAP = "Brondata/Iv3/"
CLASSES = "Brondata/Gemeenteklassen/"
SOC_CTR = "Brondata/sociale_structuur_centrumfunctie.csv"
NAMES = "Brondata/gemeentenamen.csv"
ANALYSEMAP = "Analysedata/Iv3/"

def main():
    
    for file in os.listdir(IV3_MAP):
        jaar = file[:4]
        
        # Create output file name
        if file.endswith("000.csv"):
            output_name = f'{jaar}_begroting.csv'
        elif file.endswith("005.csv"):
            output_name =  f'{jaar}_jaarrekening.csv'
    
        # Create output df
        df = pd.read_csv(str(IV3_MAP) + file)
        
        totals = get_taakveld_totals(df)
        totals_w_classes = add_class_data(totals, jaar)
        totals_right_names = replace_gemeente_names(totals_w_classes)
        
        output_df = add_total_general(totals_right_names)
        
        output_df.to_csv(str(ANALYSEMAP) + output_name, sep=";", index=False) # ; For Nuenen Gerwen
        print(output_name)
                
def get_taakveld_totals(df):
    k = "k_2ePlaatsing_2"

    # Pivot on Gemeenten and TaakveldBalanspost
    pv = df.pivot(index = ["Gemeenten", "TaakveldBalanspost"], columns="Categorie", values =[k])
    
    # Sum baten and lasten
    pv.columns = [col[-1] for col in pv.columns]
    batencolumns = [col for col in pv.columns if col.startswith("B")]
    lastencolumns = [col for col in pv.columns if col.startswith("L")]

    pv['Baten'] = pv[batencolumns].sum(axis=1)
    pv['Lasten'] = pv[lastencolumns].sum(axis=1)
    
    # Remove Balanspost and columns with Categorie excl. Salarislasten
    pv = pv[pv.index.get_level_values("TaakveldBalanspost").str.startswith(("A", "P")) == False]
    lastencolumns = [col for col in lastencolumns if not col.startswith("L1.1")]
    pv = pv.drop(columns=batencolumns + lastencolumns + ['Primo', 'Ultimo'])
    
    df2 = pv.reset_index()
    df2 = df2.rename(columns={"TaakveldBalanspost": "Taakveld"})
    
    return df2

def add_class_data(df, jaar):
    
    class_data = pd.read_csv(CLASSES + jaar + ".csv", sep="\t")
    soc_data = pd.read_csv(SOC_CTR, sep="\t")
    
    class_df = pd.merge(df, class_data, on="Gemeenten")
    output_df = pd.merge(class_df, soc_data, on="Gemeenten")
    
    return output_df

def replace_gemeente_names(df):
    
    # Create dict with gemeentenamen
    gemeentenamen = {}
    with open(NAMES, mode='r', encoding='utf-8') as file:
        csv_reader = csv.reader(file, delimiter='\t')
        next(csv_reader)  # Skip header row
        for row in csv_reader:
            gemeentenamen[row[0]] = row[1]
    output_df = df.replace(gemeentenamen)
    
    return output_df

def add_total_general(df):
    
    # Calculate total for each unique Taakveld
    total_df = df.groupby("Taakveld").agg({
        "L1.1 Salarissen en sociale lasten": "sum",
        "Baten": "sum",
        "Lasten": "sum",
        "Inwonertal": "sum"
    }).reset_index()
    
    # Set the 'Gemeenten' column to 'Nederland' for the total rows
    total_df['Gemeenten'] = 'Nederland'
    
    # Add the total row to the original dataframe
    df = pd.concat([df, total_df], ignore_index=True)
    
    return df

if __name__ == "__main__":
    main()
