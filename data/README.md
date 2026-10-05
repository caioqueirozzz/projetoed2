# FMA Medium: download e importação

O projeto usa o [FMA — Free Music Archive: Small & Medium do Kaggle](https://www.kaggle.com/datasets/imsparsh/fma-free-music-archive-small-medium), com o formato do [FMA oficial](https://github.com/mdeff/fma). O código não exige credenciais do Kaggle: baixe os arquivos pela sua conta e informe o caminho local.

## 1. Arquivos necessários

- `tracks.csv`: metadados, com cabeçalho de dois níveis.
- `features.csv`: características pré-calculadas, com cabeçalho de três níveis.
- `genres.csv`: catálogo de gêneros; preservado quando disponível. O gênero de cada música já vem de `track.genre_top`.
- `fma_medium/000/000002.mp3`, etc.: trechos de áudio organizados pelo ID de seis dígitos.

No Kaggle, baixe o arquivo completo ou os componentes que contenham **fma_metadata** e **fma_medium**. O projeto importa os MP3s de Medium e ignora a cópia de Small. Se o pacote baixado não incluir alguma dessas partes, os links para `fma_metadata.zip` e `fma_medium.zip` estão na [documentação oficial](https://github.com/mdeff/fma#data).

Medium tem 25.000 faixas antes da limpeza. Seus metadados incluem os rótulos **small e medium**, pois os subconjuntos são aninhados. Filtrar somente `subset == medium` exclui as 8.000 faixas de Small. O áudio Medium ocupa aproximadamente 22 GiB; reserve espaço adicional para manter o ZIP durante a extração.

## 2. Preparar o ambiente

Execute na raiz do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r preprocessing/requirements.txt -r app/requirements.txt
```

## 3. Importar os dados

Escolha uma das formas abaixo. Os caminhos podem conter espaços, desde que estejam entre aspas.

**ZIP baixado do Kaggle:**

```bash
python preprocessing/build_dataset.py --import-zip "/caminho/archive.zip"
```

O importador extrai apenas as tabelas utilizadas e os MP3s de `fma_medium`, para `data/raw/`. Aceita pastas aninhadas como `fma_medium/fma_medium/`. Não é necessário extrair o pacote manualmente. ZIPs que contenham outros ZIPs precisam ser descompactados em uma primeira etapa; depois, passe os ZIPs internos ao comando abaixo.

**ZIPs separados de metadados e áudio:**

```bash
python preprocessing/build_dataset.py \
  --import-zip "/caminho/fma_metadata.zip" \
  --import-zip "/caminho/fma_medium.zip" \
  --require-audio
```

**Pasta já extraída, inclusive em outro disco:**

```bash
python preprocessing/build_dataset.py \
  --source "/caminho/dataset-extraido" \
  --audio-dir "/outro/disco/fma_medium" \
  --require-audio
```

`--source` pode apontar à pasta que contém as tabelas ou a uma pasta acima delas. `--audio-dir` deve conter diretamente as subpastas `000/`, `001/`, etc. É opcional quando `fma_medium` está dentro de `--source`. O pipeline usa os arquivos nessa localização sem copiar toda a coleção.

**Arquivos já colocados em `data/raw/`:**

```text
data/raw/
├── fma_metadata/
│   ├── tracks.csv
│   ├── features.csv
│   └── genres.csv
└── fma_medium/
    ├── 000/000002.mp3
    └── ...
```

```bash
python preprocessing/build_dataset.py --require-audio
```

Por padrão, áudios ausentes não impedem a geração do índice: são listados no relatório. `--require-audio` exige um MP3 presente e não vazio para cada faixa que permanecer após a limpeza. Essa verificação não decodifica o áudio; um arquivo danificado internamente ainda pode falhar no player.

## 4. Arquivos produzidos

Em `data/processed/`:

- `tracks_processed.csv`: `track_id`, `title`, `artist`, `genre`, `audio_path` e as 44 características normalizadas.
- `normalization_params.json`: mínimos, máximos e ordem das características.
- `dataset_report.json`: quantidade de faixas, gêneros, IDs sem características, IDs descartados e áudios ausentes.
- `genres.csv`: catálogo de gêneros, quando fornecido.

As seis primeiras características são RMS, ZCR, centroide, largura de banda, rolloff e MFCC-1. Essa ordem define a Acoustic Key. Linhas com valores ausentes, infinitos ou não numéricos são removidas. Colunas com mais de 50% de valores inválidos causam erro; nenhuma característica é descartada silenciosamente.

O CSV guarda caminhos absolutos dos áudios para permitir armazenamento externo. Ao mover os arquivos, gere novamente o CSV ou defina a pasta de áudio ao iniciar a interface:

```bash
FMA_AUDIO_DIR="/novo/disco/fma_medium" streamlit run app/app.py
```

Para um CSV processado fora do caminho padrão, use `AME_DATASET_CSV="/caminho/tracks_processed.csv"`. O parâmetro `--output-dir` do pipeline permite escolher a pasta de saída.

## 5. Executar

```bash
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
streamlit run app/app.py
```

Se CMake não estiver instalado, instale no ambiente virtual com `python -m pip install cmake`. É necessário um compilador C++17.

Em todos os seletores de músicas, inclusive nas recomendações, clique no próprio
campo e digite para filtrar a lista a cada letra, sem pressionar Enter. Você pode
rolar pelas opções filtradas; ao apagar o texto, todas as opções daquele seletor
voltam a aparecer. A busca ignora diferenças entre maiúsculas e minúsculas.

**Music Explorer** permite buscar em todo o catálogo e ouvir a faixa escolhida e as recomendações. Selecione o modo de busca, a quantidade inicial de candidatos e o Top-K; clique em **Encontrar músicas semelhantes**. O modo exato expande a busca quando necessário para certificar o resultado. A comparação exaustiva opcional mede Recall@K e o tempo da referência.

**Structures Lab** reúne as operações e visualizações de Skip List e Splay Tree em instâncias independentes do catálogo. O laboratório aceita IDs de demonstração e funciona mesmo sem importar o FMA; a busca musical exige a base processada. Os benchmarks de similaridade também exigem a base.

## 6. Benchmarks com o dataset real

Na raiz, execute `python benchmark/run_benchmarks.py --repeats 5`. O script mede a busca aproximada, a busca exata certificada e os comparativos das estruturas, registra a identificação da base e publica os CSVs em `benchmark/results/`. O laboratório exibe resultados, médias, desvios e exportações, e avisa quando os arquivos não correspondem à base/código atual.

A faixa consultada é excluída do ranking e da referência exaustiva. Para menos de 11 faixas, `top_k` informa o K efetivo. O campo `mode` separa o método certificado da janela aproximada. Use `--dataset` para uma base externa e `--output` para outro diretório.

`./build/benchmark_similarity --synthetic` mantém uma demonstração sintética separada. No Music Explorer, a busca exata é o padrão e a janela aproximada está disponível como modo experimental.

## Validação e origem

Os testes Python constroem CSVs pequenos no formato FMA e verificam importação, inclusão de Small, normalização, caminhos com espaços, títulos com aspas/quebras de linha e comunicação com C++. Não incluem a coleção real nem validam a decodificação dos 25.000 MP3s.

```bash
python -m unittest discover -s tests -p 'test_dataset.py' -v
```

Os dados e resultados gerados não são versionados. Cite **Defferrard et al., FMA: A Dataset For Music Analysis, ISMIR 2017** no relatório acadêmico. Os metadados são CC BY 4.0; cada áudio conserva a licença escolhida pelo artista, conforme a [fonte oficial](https://github.com/mdeff/fma#acknowledgments-and-licenses).
