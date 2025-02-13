"""Preprocessing for news features."""

import re

import pandas as pd
from constants import (
    cols_to_clean,
    cols_to_drop,
    news_num_csv_files,
    news_template_path,
)
from utils import concatenate_csv_to_df


def preprocess_news() -> pd.DataFrame:
    """
    Realiza o pré-processamento dos dados de notícias:
    - Concatena CSVs.
    - Extrai informações da URL (localidade, tema da notícia).
    - Limpa colunas de texto.
    - Remove colunas desnecessárias.
    """
    # Concatena CSVs
    df_news = concatenate_csv_to_df(news_template_path, news_num_csv_files)

    # Renomeia coluna de chave primária
    df_news = df_news.rename(columns={"page": "pageId"})

    # Converte colunas de data de publicação e modificação
    for col in ["issued", "modified"]:
        df_news[col] = pd.to_datetime(df_news[col])
        df_news[f"{col}Date"] = df_news[col].dt.date
        df_news[f"{col}Time"] = df_news[col].dt.time

    # Extrai informações do miolo da URL
    df_news["urlExtracted"] = df_news["url"].apply(_extract_url_midsection)

    # Extrai localidade da URL
    df_news["local"] = df_news["urlExtracted"].apply(_extract_location)
    df_news["localState"] = df_news["local"].str.split("/").str[0]
    df_news["localRegion"] = df_news["local"].str.split("/").str[1]

    print("Esse aí passou!")

    # Extrai tema da notícia da URL
    df_news["theme"] = df_news["urlExtracted"].apply(_extract_theme)
    df_news["themeMain"] = df_news["theme"].str.split("/").str[0]
    df_news["themeSub"] = df_news["theme"].str.split("/").str[1]

    print("Esse aí passou!")

    # Limpa colunas de texto
    for col in cols_to_clean:
        df_news[f"{col}Cleaned"] = df_news[col].apply(_preprocess_text)

    print("Esse aí passou!")

    # Remove colunas desnecessárias
    df_news = df_news.drop(columns=cols_to_drop)

    return df_news


def _extract_url_midsection(url):
    """Extrai o miolo relevante da URL."""
    regex = r"(?<=g1\.globo\.com\/)(.*?)(?=\/noticia)"
    match = re.search(regex, url)
    return match.group() if match else None


def _extract_location(url_part):
    """Extrai a localidade a partir do miolo da URL."""
    if not url_part:
        return None
    regex = re.compile(r"^[a-z]{2}/[a-z-]+")
    match = regex.match(url_part)
    return match.group() if match else None


def _extract_theme(url_part):
    """Extrai o tema da notícia a partir do miolo da URL."""
    location = _extract_location(url_part)
    if pd.notna(url_part):
        if location:
            theme = url_part.replace(location, "").lstrip("/")
            return theme if theme else None
        else:
            return url_part
    return None


def _preprocess_text(text):
    """Padroniza e limpa o texto de notícias."""
    if not isinstance(text, str):
        text = ""
    text = re.sub(r"\W+", " ", text)
    text = re.sub(r"\d+", "", text)
    return text.lower()
