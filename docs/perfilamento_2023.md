# Perfilamento preliminar das bases - 2023

## ENEM 2023

- Registros: **3,933,955** | Variáveis: **76**
- Treineiros: 620,067 (15.8%)
- Presentes nas 4 provas objetivas: 2,678,264 (68.1%)
- Redações com nota zero: 117,829
- Situação de conclusão (TP_ST_CONCLUSAO):
  - 1: 1,895,301 (48.2%)
  - 2: 1,401,164 (35.6%)
  - 3: 620,067 (15.8%)
  - 4: 17,423 (0.4%)
- Concluintes 2023: 1,401,164; com município da escola preenchido: 958,506 (68.4%)

**Variáveis com mais nulos (top 15):**

| Variável | Nulos | % |
|---|---|---|
| SG_UF_ESC | 2,975,449 | 75.6% |
| CO_UF_ESC | 2,975,449 | 75.6% |
| NO_MUNICIPIO_ESC | 2,975,449 | 75.6% |
| CO_MUNICIPIO_ESC | 2,975,449 | 75.6% |
| TP_LOCALIZACAO_ESC | 2,975,449 | 75.6% |
| TP_SIT_FUNC_ESC | 2,975,449 | 75.6% |
| TP_DEPENDENCIA_ADM_ESC | 2,975,449 | 75.6% |
| TP_ENSINO | 2,594,874 | 66.0% |
| CO_PROVA_CN | 1,241,528 | 31.6% |
| TX_GABARITO_MT | 1,241,528 | 31.6% |
| TX_RESPOSTAS_MT | 1,241,528 | 31.6% |
| TX_RESPOSTAS_CN | 1,241,528 | 31.6% |
| CO_PROVA_MT | 1,241,528 | 31.6% |
| NU_NOTA_MT | 1,241,528 | 31.6% |
| NU_NOTA_CN | 1,241,528 | 31.6% |

- Participantes aptos à análise (concluintes, com escola, presentes): **721,429**
- Municípios de escola distintos: 5,481
- Distribuição por dependência administrativa (1=Fed, 2=Est, 3=Mun, 4=Priv):
  - 1: 43,946 (6.1%)
  - 2: 456,911 (63.3%)
  - 3: 5,832 (0.8%)
  - 4: 214,740 (29.8%)

## Censo Escolar 2023 (tabela de escolas)

- Registros (todas as escolas): **217,625** | Variáveis: **408**
- Escolas em atividade com ensino médio: **29,754**
- Municípios com ao menos uma escola de EM: 5,563

| Variável de infraestrutura | Nulos | % com o item (entre não nulos) |
|---|---|---|
| IN_BIBLIOTECA | 0.0% | 70.6% |
| IN_LABORATORIO_INFORMATICA | 0.0% | 69.6% |
| IN_LABORATORIO_CIENCIAS | 0.0% | 49.7% |
| IN_QUADRA_ESPORTES | 0.0% | 77.9% |
| IN_INTERNET | 0.0% | 98.2% |
| IN_AGUA_POTAVEL | 0.0% | 95.9% |
| IN_BANHEIRO | 0.0% | 98.9% |
- QT_MAT_MED: nulos 0.0%, zeros 0.0%
- QT_DOC_MED: nulos 0.0%, zeros 0.0%

## Teste de integração

- Participantes do ENEM cuja chave (município + rede + localização) existe no Censo: **719,193 de 721,429 (99.7%)**
- Grupos do Censo sem nenhum participante no ENEM: 637 de 9,324
- Grupos com menos de 10 participantes (médias instáveis): 3,162 de 9,281
- Municípios do ENEM encontrados no PIB 2023: 5,481 de 5,481 (100.0%)