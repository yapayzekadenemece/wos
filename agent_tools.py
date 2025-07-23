import os
import pandas as pd

EXCEL_FOLDER = "excel_data/"

def load_all_excels():
    dfs = []
    for file in os.listdir(EXCEL_FOLDER):
        if file.endswith(".xlsx"):
            df = pd.read_excel(os.path.join(EXCEL_FOLDER, file))
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

df = load_all_excels()

def most_published_universities_by_field(field_keyword):
    filtered = df[df['keywords.authorKeywords'].astype(str).str.contains(field_keyword, case=False, na=False)]
    grouped = filtered.groupby("Üniversite Adı").size().sort_values(ascending=False).reset_index()
    grouped.columns = ["Üniversite", "Makale Sayısı"]
    return grouped.head(10)

def article_distribution_by_journal(journal_keyword):
    filtered = df[df['source.sourceTitle'].astype(str).str.contains(journal_keyword, case=False, na=False)]
    grouped = filtered.groupby("Üniversite Adı").size().sort_values(ascending=False).reset_index()
    grouped.columns = ["Üniversite", "Makale Sayısı"]
    return grouped
