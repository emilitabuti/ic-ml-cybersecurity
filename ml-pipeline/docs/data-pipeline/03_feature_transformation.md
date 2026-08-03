# 03 — Transformação temporal

Primeiro, `detection_temporal_splitter.py` ordena os fluxos e separa as três
sessões naturais. Depois, `FoldPreprocessor` aprende transformação logarítmica,
categorias e estatísticas do `RobustScaler` somente no treino de cada fold.

O ranking por importância também é ajustado somente no treino. As variantes
`all`, `top_10`, `top_20` e `top_30` são comparadas nos folds expansivos. As
janelas são construídas após a seleção e nunca cruzam partição, sessão, bloco
de desenvolvimento ou arquivo-fonte.

No artefato final, 43 campos brutos geram 204 atributos transformados; os 30
primeiros são selecionados e uma janela de dez registros produz 300 valores
para o Random Forest.
