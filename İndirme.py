import pandas as pd
import os

def load_all_excels():
    EXCEL_FOLDER = "excel_data/"  # Dosyaların olduğu klasör
    dfs = []
    for file in os.listdir(EXCEL_FOLDER):
        if file.endswith(".xlsx"):
            df = pd.read_excel(os.path.join(EXCEL_FOLDER, file))
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

# Bu fonksiyon artık çağrılabilir:
df = load_all_excels()
print(df.head())
