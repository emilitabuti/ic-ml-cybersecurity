# Log de execução — Relatório Final de IC

- Data e hora: 2026-08-03T14:16:12-03:00
- Fonte textual: `docs/emili/relatorio-final/relatorio-final-emili.md`
- Codificação da fonte e do log: UTF-8

## 1. Arquivos obrigatórios

- `docs/compartilhado/relatorios-de-ic-parcial-e-final-v3.pdf`: acessível
- `docs/compartilhado/2-INSTRUCOES-PARA-FORMATACAO-DE-RESUMO-ESTENDIDO-0508-v2.docx`: acessível
- `docs/emili/RelatorioParcial - Emili Vieira Tabuti.docx`: acessível
- `docs/emili/Plano individual - Emili Vieira Tabuti.docx`: acessível
- `docs/compartilhado/ProjetoOrientador.docx`: acessível
- `docs/compartilhado/pesquisas-ml`: acessível
- `_bmad-output/emili/planning-artifacts`: acessível
- `_bmad-output/compartilhado`: acessível
- `ml-pipeline`: acessível

Observação: o pedido mencionava `relatorio-parcial.pdf` e `plano-individual.docx`.
No repositório, ambos foram localizados com nomes completos e em formato DOCX.

## 2. Etapas executadas

1. Extração do modelo institucional e do guia de resumo estendido.
2. Leitura do relatório parcial, plano individual e projeto do orientador.
3. Auditoria dos artefatos de planejamento, implementação, código e resultados.
4. Auditoria do piloto prospectivo, seus rótulos, atributos e divisão temporal.
5. Conferência dos metadados bibliográficos e DOI nos arquivos dos editores.
6. Redação em português acadêmico, com voz ativa e marcação de lacunas.
7. Geração do relatório e do resumo estendido em DOCX e PDF.
8. Validação de integridade, paginação, tamanho de papel e contagem de palavras.
9. Execução da suíte automatizada do pipeline.

## 3. Validações documentais

- Relatório PDF: 27 páginas; tamanhos [(595.3, 841.9), (612.0, 792.0)]; limite de 50 páginas: OK.
- Resumo PDF: 5 páginas; tamanhos [(595.3, 841.9)].
- Relatório DOCX: 256 parágrafos; 5 tabelas.
- Resumo DOCX: 53 parágrafos; 0 tabelas.
- Resumo introdutório: 186 palavras; limite de 250: OK.
- Resumo estendido: 1871 palavras; faixa de 1.000 a 2.000: OK.
- Figuras inseridas: nenhuma.
- Tabelas inseridas: somente tabelas derivadas dos CSV e relatórios JSON existentes.
- Citações diretas: nenhuma.
- Referências principais: padrão autor-data no relatório e padrão numérico no resumo estendido.
- Fontes: Times New Roman no DOCX; Times-Roman no PDF.

## 4. Controles e limitações metodológicas registrados

- O pré-processamento e a seleção foram ajustados somente no treino de cada fold temporal.
- Nenhuma janela cruza partição, sessão, bloco temporal ou arquivo-fonte.
- O teste futuro foi lido e avaliado uma única vez depois do congelamento.
- A execução final usou versões de NumPy, Pandas, PyArrow e scikit-learn diferentes das registradas no protocolo.
- O executor final foi criado depois do congelamento; seu hash consta no manifesto de execução.
- O rótulo corresponde ao último registro da janela, sem horizonte futuro.
- O piloto prospectivo controlou o tempo, mas restaram somente cinco eventos estritos.
- Validação e teste receberam um evento positivo cada no conjunto estrito.
- Os horizontes de 30 e 60 segundos não conservaram negativos nas partições futuras.
- O UNSW-NB15 não informa com clareza quais registros pertencem a cada evento de ataque.
- A análise por tipo segmenta previsões binárias; ela não é classificação multiclasse.
- A seleção foi usada nos modelos finais: top-10 na Decision Tree, top-20 na LSTM e top-30 no Random Forest.

## 5. Lacunas humanas

- TODO: confirmar mês e ano de encerramento
- TODO: confirmar se a periodicidade quinzenal foi mantida após março de 2026.
- TODO: informar e-mail institucional da estudante
- TODO: informar e-mail institucional do orientador
- TODO: informar seminários, cursos, apresentações ou eventos realizados após março de 2026.

## 6. Testes do pipeline

- Comando: `ml-pipeline/.venv/bin/python -m pytest tests -q`
- Código de saída: 0

```text
........................................................................ [ 41%]
........................................................................ [ 82%]
...............................                                          [100%]
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  <project-root>/ml-pipeline/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
175 passed, 1 warning in 17.19s
```

## 7. Artefatos e hashes SHA-256

- `docs/emili/relatorio-final/Relatorio-Final-IC-Emili-Vieira-Tabuti.docx`: `f2995a671e8f29349900caab9f6957523de61ee768e13340a29614aaa2710889`
- `docs/emili/relatorio-final/Relatorio-Final-IC-Emili-Vieira-Tabuti.pdf`: `125c60cd130f424a731a549231ae4c808fce955d7812c1d8279d8b5b9a6a4af1`
- `docs/emili/relatorio-final/Resumo-Estendido-Emili-Vieira-Tabuti.docx`: `9d15a03902b9220ae48f91e139f01f289ae421f5ec2ca5d0afcb21744f2ba4ad`
- `docs/emili/relatorio-final/Resumo-Estendido-Emili-Vieira-Tabuti.pdf`: `5a20461cc74d4fca3f022266f2873bbfab795f4968b2e038b8b06c478a86d4ca`
- `docs/emili/relatorio-final/relatorio-final-emili.md`: `dc18321555a2dff9b3905e3ca65881d29da7c25c70bb4efc7a183c53cf3a4276`
- `ml-pipeline/reports_temporal/unsw/protocol.json`: `ff08c3fc499f5679ea3d399021da9c476909eaecb73312fe85cb990fab37cc6f`
- `ml-pipeline/reports_temporal/unsw/final_test_metrics.json`: `8c3dc8d36aa617e074b0640208fdb4db139717e83adba093dd62bb015f566603`
- `ml-pipeline/reports_temporal/unsw/final_evaluation/execution_manifest.json`: `02654a7322c147cb1ad66794b62bf63d7d98d8052a31de844a422067b4bd80e7`
- `ml-pipeline/models/model_rf_temporal_v2.pkl`: `ef622fa6dc6f995ca83dafe555e4fafdaf425a0bff1ea751851a2ff71ae7c713`
