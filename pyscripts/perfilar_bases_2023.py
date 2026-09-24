"""
Perfilamento preliminar das bases (ano de referência 2023) - Etapa 1 do projeto de BI.

Gera os números exigidos na Entrega 1 (registros, variáveis, nulos, qualidade)
e testa se a integração ENEM x Censo Escolar x PIB funciona na prática.

Uso:
  pip install pandas
  python perfilar_bases_2023.py \
      --enem  data/raw/enem/MICRODADOS_ENEM_2023.csv \
      --censo data/raw/censo/microdados_ed_basica_2023.csv \
      --pib   data/processed/pib_municipal.csv

Saída: docs/perfilamento_2023.md (e o mesmo conteúdo no terminal)
"""

import argparse
from pathlib import Path

import pandas as pd

CHUNK = 500_000
CHAVE = ["co_municipio", "tp_dependencia", "tp_localizacao"]

INFRA = [
    "IN_BIBLIOTECA", "IN_LABORATORIO_INFORMATICA", "IN_LABORATORIO_CIENCIAS",
    "IN_QUADRA_ESPORTES", "IN_INTERNET",
    # só coletadas a partir de 2019 -> perfiladas, mas fora do índice da série
    "IN_AGUA_POTAVEL", "IN_BANHEIRO",
]
NOTAS = ["NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO"]
PRESENCAS = ["TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC", "TP_PRESENCA_MT"]

relatorio: list[str] = []


def out(texto: str = "") -> None:
    print(texto)
    relatorio.append(texto)


def pct(parte, total) -> str:
    return f"{100 * parte / total:.1f}%" if total else "n/a"


def ler_csv(caminho, **kw):
    """Arquivos do INEP costumam vir em latin-1 com ';'. Tenta UTF-8 se falhar."""
    for enc in ("latin-1", "utf-8"):
        try:
            return pd.read_csv(caminho, sep=";", encoding=enc, low_memory=False, **kw)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Não foi possível ler {caminho}")


# --------------------------------------------------------------------------- #
def perfilar_enem(caminho: str) -> pd.DataFrame:
    out("## ENEM 2023\n")
    total, colunas, nulos = 0, None, None
    conclusao = pd.Series(dtype="int64")
    treineiros = presentes_todas = zeros_redacao = 0
    concluintes = concl_com_escola = 0
    chaves = []

    for bloco in ler_csv(caminho, chunksize=CHUNK):
        total += len(bloco)
        colunas = bloco.columns
        n = bloco.isna().sum()
        nulos = n if nulos is None else nulos + n

        conclusao = conclusao.add(bloco["TP_ST_CONCLUSAO"].value_counts(), fill_value=0)
        treineiros += (bloco["IN_TREINEIRO"] == 1).sum()
        presentes_todas += (bloco[PRESENCAS] == 1).all(axis=1).sum()
        zeros_redacao += (bloco["NU_NOTA_REDACAO"] == 0).sum()

        # População de interesse: concluintes em 2023 (TP_ST_CONCLUSAO = 2)
        conc = bloco[bloco["TP_ST_CONCLUSAO"] == 2]
        concluintes += len(conc)
        conc = conc[conc["CO_MUNICIPIO_ESC"].notna()]
        concl_com_escola += len(conc)

        # Somente quem fez as 4 provas objetivas entra na análise de desempenho
        validos = conc[(conc[PRESENCAS] == 1).all(axis=1)]
        chaves.append(pd.DataFrame({
            "co_municipio": validos["CO_MUNICIPIO_ESC"].astype(int),
            "tp_dependencia": validos["TP_DEPENDENCIA_ADM_ESC"].astype("Int64"),
            "tp_localizacao": validos["TP_LOCALIZACAO_ESC"].astype("Int64"),
            "media": validos[NOTAS].mean(axis=1),
        }))

    out(f"- Registros: **{total:,}** | Variáveis: **{len(colunas)}**")
    out(f"- Treineiros: {treineiros:,} ({pct(treineiros, total)})")
    out(f"- Presentes nas 4 provas objetivas: {presentes_todas:,} ({pct(presentes_todas, total)})")
    out(f"- Redações com nota zero: {zeros_redacao:,}")
    out("- Situação de conclusão (TP_ST_CONCLUSAO):")
    for cod, qtd in conclusao.sort_index().items():
        out(f"  - {int(cod)}: {int(qtd):,} ({pct(qtd, total)})")
    out(f"- Concluintes 2023: {concluintes:,}; com município da escola preenchido: "
        f"{concl_com_escola:,} ({pct(concl_com_escola, concluintes)})")

    out("\n**Variáveis com mais nulos (top 15):**\n")
    out("| Variável | Nulos | % |")
    out("|---|---|---|")
    for col, qtd in nulos.sort_values(ascending=False).head(15).items():
        out(f"| {col} | {int(qtd):,} | {pct(qtd, total)} |")

    base = pd.concat(chaves, ignore_index=True)
    out(f"\n- Participantes aptos à análise (concluintes, com escola, presentes): **{len(base):,}**")
    out(f"- Municípios de escola distintos: {base['co_municipio'].nunique():,}")
    out("- Distribuição por dependência administrativa (1=Fed, 2=Est, 3=Mun, 4=Priv):")
    for cod, qtd in base["tp_dependencia"].value_counts(dropna=False).sort_index().items():
        out(f"  - {cod}: {qtd:,} ({pct(qtd, len(base))})")
    return base


# --------------------------------------------------------------------------- #
def perfilar_censo(caminho: str) -> pd.DataFrame:
    out("\n## Censo Escolar 2023 (tabela de escolas)\n")
    df = ler_csv(caminho)
    out(f"- Registros (todas as escolas): **{len(df):,}** | Variáveis: **{df.shape[1]}**")

    em = df[(df["IN_MED"] == 1) & (df["TP_SITUACAO_FUNCIONAMENTO"] == 1)].copy()
    out(f"- Escolas em atividade com ensino médio: **{len(em):,}**")
    out(f"- Municípios com ao menos uma escola de EM: {em['CO_MUNICIPIO'].nunique():,}")

    out("\n| Variável de infraestrutura | Nulos | % com o item (entre não nulos) |")
    out("|---|---|---|")
    for col in INFRA:
        if col not in em:
            out(f"| {col} | coluna ausente | - |")
            continue
        out(f"| {col} | {pct(em[col].isna().sum(), len(em))} | {pct((em[col] == 1).sum(), em[col].notna().sum())} |")

    for col in ["QT_MAT_MED", "QT_DOC_MED"]:
        if col in em:
            out(f"- {col}: nulos {pct(em[col].isna().sum(), len(em))}, "
                f"zeros {pct((em[col] == 0).sum(), len(em))}")

    return em.rename(columns={
        "CO_MUNICIPIO": "co_municipio",
        "TP_DEPENDENCIA": "tp_dependencia",
        "TP_LOCALIZACAO": "tp_localizacao",
    })[CHAVE + [c for c in INFRA if c in em]]


# --------------------------------------------------------------------------- #
def testar_integracao(enem: pd.DataFrame, censo: pd.DataFrame, caminho_pib: str | None):
    out("\n## Teste de integração\n")
    censo = censo.astype({"co_municipio": int, "tp_dependencia": "Int64", "tp_localizacao": "Int64"})
    chaves_censo = censo[CHAVE].drop_duplicates()

    casados = enem.merge(chaves_censo, on=CHAVE, how="left", indicator=True)
    ok = (casados["_merge"] == "both").sum()
    out(f"- Participantes do ENEM cuja chave (município + rede + localização) existe no Censo: "
        f"**{ok:,} de {len(enem):,} ({pct(ok, len(enem))})**")

    grupos_enem = enem[CHAVE].drop_duplicates()
    sem_enem = chaves_censo.merge(grupos_enem, on=CHAVE, how="left", indicator=True)
    sem_enem = (sem_enem["_merge"] == "left_only").sum()
    out(f"- Grupos do Censo sem nenhum participante no ENEM: {sem_enem:,} de {len(chaves_censo):,}")

    tamanho = enem.groupby(CHAVE).size()
    out(f"- Grupos com menos de 10 participantes (médias instáveis): "
        f"{(tamanho < 10).sum():,} de {len(tamanho):,}")

    if caminho_pib and Path(caminho_pib).exists():
        pib = pd.read_csv(caminho_pib)
        pib23 = set(pib.loc[pib["ano"] == 2023, "co_municipio"])
        mun_enem = set(enem["co_municipio"])
        out(f"- Municípios do ENEM encontrados no PIB 2023: "
            f"{len(mun_enem & pib23):,} de {len(mun_enem):,} ({pct(len(mun_enem & pib23), len(mun_enem))})")
    else:
        out("- PIB não informado ou arquivo não encontrado: teste pulado.")


# --------------------------------------------------------------------------- #
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--enem", required=True)
    p.add_argument("--censo", required=True)
    p.add_argument("--pib", default="data/processed/pib_municipal.csv")
    p.add_argument("--saida", default="docs/perfilamento_2023.md")
    args = p.parse_args()

    out("# Perfilamento preliminar das bases - 2023\n")
    enem = perfilar_enem(args.enem)
    censo = perfilar_censo(args.censo)
    testar_integracao(enem, censo, args.pib)

    saida = Path(args.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text("\n".join(relatorio), encoding="utf-8")
    print(f"\nRelatório salvo em {saida}")


if __name__ == "__main__":
    main()
