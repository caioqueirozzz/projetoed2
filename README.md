# Adaptive Music Explorer

Busca por similaridade musical sobre o **FMA Medium**, com duas áreas:

- **Music Explorer** — funcionalidade contextualizada: selecionar uma música,
  encontrar as K faixas mais semelhantes e ouvir a referência e as recomendações.
  Duas **Skip Lists** indexam o catálogo e um heap mantém os melhores resultados.
- **Structures Lab** — apoio ao estudo e teste de **Skip List** e **Splay Tree**,
  com operações interativas, visualizações, métricas e benchmarks. As estruturas
  do laboratório são independentes do catálogo musical.

O núcleo de estruturas é escrito em **C++**; o pré-processamento dos dados e a
interface (**Streamlit**) são escritos em **Python**. A Splay Tree demonstra
localidade de acesso no laboratório e nos experimentos.

## Estrutura do repositório

```
core/          Núcleo C++ (Skip List, Splay Tree, similaridade, Acoustic Key)
preprocessing/ Pipeline Python de preparação do FMA -> tracks_processed.csv
app/           Aplicação Streamlit (início + Music Explorer + Structures Lab)
benchmark/     Benchmarks C++ (estruturas e similaridade) + resultados CSV
tests/         Testes C++, integração Python e interface Streamlit
data/          raw/ (FMA baixado) e processed/ (dataset gerado)
```

## Build do núcleo C++

```bash
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure   # roda os testes
```

Binários gerados em `build/`:
`ame_core_app`, `benchmark_skiplist`, `benchmark_splay`, `benchmark_similarity`.

## Dataset: FMA Medium (Kaggle)

Baixe os arquivos em [FMA — Small & Medium no Kaggle](https://www.kaggle.com/datasets/imsparsh/fma-free-music-archive-small-medium).
São necessários os metadados (`tracks.csv`, `features.csv`, `genres.csv`) e os
áudios de `fma_medium`. O Medium inclui as faixas rotuladas `small` e `medium`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r preprocessing/requirements.txt -r app/requirements.txt
python preprocessing/build_dataset.py --import-zip "/caminho/archive.zip"
```

O pipeline produz o CSV com 44 características, parâmetros de normalização e
um relatório de faixas/áudios ausentes. Também aceita pastas extraídas e áudios
em outro disco. Veja [data/README.md](data/README.md) para as opções de importação,
validação dos áudios e instruções completas.

## Interface (Streamlit)

```bash
pip install -r app/requirements.txt
streamlit run app/app.py
```

Execute a partir da raiz do repositório para carregar `.streamlit/config.toml`,
que usa verificação periódica dos arquivos Python. Após alterar dependências ou
assinaturas de componentes, encerre o servidor anterior com `Ctrl+C` e inicie-o
novamente. Uma porta ocupada indica que a nova instância não foi iniciada.

Para conferir as páginas no servidor em execução, incluindo busca, áudio e
operações do laboratório, use a base importada e os benchmarks já gerados:

```bash
AME_LIVE_URL=http://127.0.0.1:8501 python -m unittest discover -s tests -p test_live_app.py -v
```

Esse teste executa os scripts pelo protocolo do Streamlit e verifica exceções;
uma resposta HTTP 200 do servidor, isoladamente, não valida as páginas.

## Estado atual e validação

Music Explorer oferece busca **exata certificada** nas 44 características e janela aproximada experimental, com comparação exaustiva opcional, Recall@K e tempos separados. A certificação usa expansão bilateral em uma Skip List ordenada por distância a pivô e limites da desigualdade triangular. Pode ser mais lenta que a busca exaustiva em consultas pouco seletivas.

Structures Lab permite inserir, buscar, remover, acessar, atualizar chaves e limpar as estruturas conforme suas operações. Mostra níveis reais da Skip List, árvores antes/depois e a sequência completa de rotações da Splay. Os benchmarks comparam desempenho, contagens e localidade de acesso.

```bash
ctest --test-dir build --output-on-failure
python benchmark/run_benchmarks.py --repeats 5
```

Use o Python do ambiente virtual na configuração do CMake para habilitar os testes Python, de interface e benchmarks:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DPython3_EXECUTABLE="$PWD/.venv/bin/python"
cmake --build build
```

Os testes combinam amostras sintéticas, invariantes das estruturas e interações via Streamlit AppTest. Os experimentos reais são executados separadamente sobre o FMA local.
