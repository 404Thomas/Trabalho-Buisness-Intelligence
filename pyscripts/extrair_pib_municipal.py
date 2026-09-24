"""
Extração do PIB e PIB per capita municipal (IBGE - PIB dos Municípios) via API SIDRA
e deflação pelo IPCA, para o período de análise do projeto de BI (2014-2023).

Camadas geradas:
  data/raw/ibge/pib_<tabela>_<ano>.json   -> resposta bruta da API (reprodutibilidade)
  data/raw/ibge/ipca_<ano>.json
  data/processed/pib_municipal.csv        -> tabela tratada, pronta para o DW

Uso:
  pip install requests pandas
  python extrair_pib_municipal.py
  python extrair_pib_municipal.py --inicio 2014 --fim 2023 --ano-base 2023
"""

import argparse
import json
import sys
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests

API_SIDRA = "https://apisidra.ibge.gov.br/values"
API_META = "https://servicodados.ibge.gov.br/api/v3/agregados"

# Tabelas do PIB dos Municípios. A 5938 é a série principal (referência 2010).
# Se o IBGE publicar 2022-2023 em outra tabela, adicione o número aqui:
# o script consulta os períodos de cada uma e usa a primeira que tiver o ano.
TABELAS_PIB = [5938]

TABELA_IPCA = 1737  # IPCA - série histórica mensal (número-índice)

RAIZ = Path(__file__).resolve().parent
DIR_RAW = RAIZ / "data" / "raw" / "ibge"
DIR_PROC = RAIZ / "data" / "processed"


# --------------------------------------------------------------------------- #
# Utilidades de acesso à API
# --------------------------------------------------------------------------- #
def get_json(url: str, tentativas: int = 4, espera: float = 5.0):
    """GET com retentativas: a API do IBGE às vezes responde 500/timeout."""
    for i in range(1, tentativas + 1):
        try:
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as erro:
            print(f"  [tentativa {i}/{tentativas}] falhou: {erro}")
            if i == tentativas:
                raise
            time.sleep(espera * i)


def normalizar(texto: str) -> str:
    """Minúsculas e sem acento, para buscar variáveis pelo nome."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def metadados(tabela: int) -> dict:
    return get_json(f"{API_META}/{tabela}/metadados")


def periodos_disponiveis(tabela: int) -> set[int]:
    return {int(p["id"][:4]) for p in get_json(f"{API_META}/{tabela}/periodos")}


def achar_variavel(meta: dict, *termos: str, excluir: tuple = ()) -> dict | None:
    """Encontra a variável cujo nome contém todos os termos (sem depender do ID fixo)."""
    for var in meta["variaveis"]:
        nome = normalizar(var["nome"])
        if all(t in nome for t in termos) and not any(e in nome for e in excluir):
            return var
    return None


def sidra_para_df(dados: list) -> pd.DataFrame:
    """
    A API SIDRA devolve uma lista em que o 1º elemento é o cabeçalho
    (ex.: {"D1N": "Município", "D2N": "Variável", ...}). Usamos esse
    cabeçalho para renomear as colunas de forma robusta.
    """
    cabecalho, linhas = dados[0], dados[1:]
    df = pd.DataFrame(linhas)
    return df.rename(columns=cabecalho)


# --------------------------------------------------------------------------- #
# Extração
# --------------------------------------------------------------------------- #
def extrair_pib(inicio: int, fim: int) -> pd.DataFrame:
    # Descobre, para cada tabela, quais anos ela tem e quais são as variáveis
    catalogo = []
    for tab in TABELAS_PIB:
        meta = metadados(tab)
        var_pib = achar_variavel(meta, "produto interno bruto", "correntes",
                                 excluir=("per capita", "participacao"))
        var_pc = achar_variavel(meta, "per capita")
        anos = periodos_disponiveis(tab)
        print(f"Tabela {tab}: {meta['nome'][:80]}...")
        print(f"  anos disponíveis: {min(anos)}-{max(anos)}")
        print(f"  PIB: {var_pib and var_pib['id']} | PIB per capita: {var_pc and var_pc['id']}")
        if var_pib is None:
            print("  AVISO: variável de PIB não encontrada; tabela ignorada.")
            continue
        catalogo.append((tab, anos, var_pib, var_pc))

    partes, faltando = [], []
    for ano in range(inicio, fim + 1):
        fonte = next((c for c in catalogo if ano in c[1]), None)
        if fonte is None:
            faltando.append(ano)
            continue
        tab, _, var_pib, var_pc = fonte
        ids = [str(var_pib["id"])] + ([str(var_pc["id"])] if var_pc else [])

        # Um ano por requisição: a API limita o número de valores por consulta
        url = f"{API_SIDRA}/t/{tab}/n6/all/v/{','.join(ids)}/p/{ano}"
        print(f"Baixando PIB {ano} (tabela {tab})...")
        dados = get_json(url)
        (DIR_RAW / f"pib_{tab}_{ano}.json").write_text(
            json.dumps(dados, ensure_ascii=False), encoding="utf-8")

        df = sidra_para_df(dados)
        df["tabela_origem"] = tab
        partes.append(df)

    if faltando:
        print(f"\nAVISO: anos sem dados em nenhuma tabela configurada: {faltando}")
        print("Confira em https://sidra.ibge.gov.br/pesquisa/pib-munic/tabelas "
              "e adicione a tabela em TABELAS_PIB.\n")
    if not partes:
        sys.exit("Nenhum dado de PIB foi baixado.")
    return pd.concat(partes, ignore_index=True)


def extrair_ipca(inicio: int, fim: int) -> pd.Series:
    """Média anual do número-índice do IPCA (base dez/1993 = 100)."""
    meta = metadados(TABELA_IPCA)
    var = achar_variavel(meta, "numero-indice")
    if var is None:
        sys.exit("Variável 'número-índice' do IPCA não encontrada.")

    medias = {}
    for ano in range(inicio, fim + 1):
        meses = ",".join(f"{ano}{m:02d}" for m in range(1, 13))
        dados = get_json(f"{API_SIDRA}/t/{TABELA_IPCA}/n1/all/v/{var['id']}/p/{meses}")
        (DIR_RAW / f"ipca_{ano}.json").write_text(
            json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        valores = pd.to_numeric(sidra_para_df(dados)["Valor"], errors="coerce")
        medias[ano] = valores.mean()
    return pd.Series(medias, name="ipca_indice_medio")


# --------------------------------------------------------------------------- #
# Transformação
# --------------------------------------------------------------------------- #
def transformar(bruto: pd.DataFrame, ipca: pd.Series, ano_base: int) -> pd.DataFrame:
    df = bruto.rename(columns={
        "Município (Código)": "co_municipio",
        "Município": "no_municipio",
        "Ano": "ano",
        "Variável": "variavel",
        "Valor": "valor",
    })

    # SIDRA usa símbolos para ausência: "-" (zero absoluto), "..." / "X" (não disponível / sigilo)
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["ano"] = df["ano"].astype(int)
    df["co_municipio"] = df["co_municipio"].astype(int)

    df["variavel"] = df["variavel"].map(
        lambda v: "pib_per_capita" if "per capita" in normalizar(v) else "pib_mil_reais")

    tabela = (df.pivot_table(index=["co_municipio", "no_municipio", "ano"],
                             columns="variavel", values="valor", aggfunc="first")
                .reset_index())
    tabela.columns.name = None

    # "Alegre - ES" -> nome e UF em colunas separadas
    partes = tabela["no_municipio"].str.rsplit(" - ", n=1, expand=True)
    tabela["no_municipio"], tabela["sg_uf"] = partes[0], partes[1]

    # Deflação: valores a preços constantes do ano-base
    fator = ipca[ano_base] / tabela["ano"].map(ipca)
    tabela["pib_mil_reais_real"] = tabela["pib_mil_reais"] * fator
    if "pib_per_capita" in tabela:
        tabela["pib_per_capita_real"] = tabela["pib_per_capita"] * fator
    else:
        print("AVISO: PIB per capita não veio da API; será preciso calcular "
              "com a população (Estimativas de População, SIDRA).")

    # Marca a mudança de metodologia populacional/série informada pelo IBGE
    tabela["flag_serie_revisavel"] = tabela["ano"] >= 2022

    return tabela.sort_values(["co_municipio", "ano"]).reset_index(drop=True)


def validar(df: pd.DataFrame, inicio: int, fim: int) -> None:
    print("\n=== Validação ===")
    print(f"Linhas: {len(df):,} | Municípios distintos: {df['co_municipio'].nunique():,}")
    print("Municípios por ano:")
    print(df.groupby("ano")["co_municipio"].nunique().to_string())
    nulos = df.isna().sum()
    print("Valores nulos por coluna:")
    print(nulos[nulos > 0].to_string() if nulos.any() else "  nenhum")
    duplicados = df.duplicated(["co_municipio", "ano"]).sum()
    print(f"Duplicidades (município, ano): {duplicados}")
    codigos_invalidos = (~df["co_municipio"].between(1_000_000, 5_399_999)).sum()
    print(f"Códigos IBGE fora do padrão de 7 dígitos: {codigos_invalidos}")
    anos = set(df["ano"])
    faltando = sorted(set(range(inicio, fim + 1)) - anos)
    print(f"Anos ausentes: {faltando or 'nenhum'}")


# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="Extrai PIB municipal do IBGE (SIDRA).")
    parser.add_argument("--inicio", type=int, default=2014)
    parser.add_argument("--fim", type=int, default=2023)
    parser.add_argument("--ano-base", type=int, default=2023,
                        help="ano de referência para os valores deflacionados")
    args = parser.parse_args()

    DIR_RAW.mkdir(parents=True, exist_ok=True)
    DIR_PROC.mkdir(parents=True, exist_ok=True)

    bruto = extrair_pib(args.inicio, args.fim)
    ipca = extrair_ipca(args.inicio, args.fim)
    tratado = transformar(bruto, ipca, args.ano_base)
    validar(tratado, args.inicio, args.fim)

    saida = DIR_PROC / "pib_municipal.csv"
    tratado.to_csv(saida, index=False, encoding="utf-8")
    print(f"\nArquivo gerado: {saida}")


if __name__ == "__main__":
    main()
