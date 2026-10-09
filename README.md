# Adaptive Music Explorer

Busca por similaridade musical sobre o **FMA Medium**, com três áreas:

- **Music Explorer** — funcionalidade contextualizada: selecionar uma música,
  encontrar as K faixas mais semelhantes e ouvir a referência e as recomendações.
  Duas **Skip Lists** indexam o catálogo e um heap mantém os melhores resultados.
  Os resultados aparecem em cartões numerados por proximidade, com distância e player.
- **Structures Lab** — apoio ao estudo e teste de **Skip List** e **Splay Tree**,
  com operações interativas, visualizações, métricas e benchmarks. As estruturas
  do laboratório são independentes do catálogo musical.
- **Perfil de reprodução** — histórico das músicas ouvidas na sessão, com
  contagem de reproduções e busca por ID em uma **Splay Tree** própria.
  O campo de seleção permite filtrar título, artista ou ID das faixas ouvidas.

O núcleo de estruturas é escrito em **C++**; o pré-processamento dos dados e a
interface (**Streamlit**) são escritos em **Python**. A Splay Tree aplica
localidade de acesso ao histórico e também é estudada no laboratório e nos experimentos.

## Estrutura do repositório

```
core/          Núcleo C++ (Skip List, Splay Tree, similaridade, Acoustic Key)
preprocessing/ Pipeline Python de preparação do FMA -> tracks_processed.csv
app/           Aplicação Streamlit (Explorer, Perfil de reprodução e Lab)
benchmark/     Benchmarks C++ (estruturas e similaridade) + resultados CSV
tests/         Testes C++, integração Python e interface Streamlit
data/          raw/ (FMA baixado) e processed/ (dataset gerado)
```

## Comandos para o dia a dia

Abra um terminal na pasta do projeto. Com o ambiente virtual e o dataset já
preparados, basta executar:

```bash
cd "/home/user/Documentos/Estrutura de Dados 2/projeto1/projetoed2"
.venv/bin/python -m streamlit run app/app.py --server.address 127.0.0.1 --server.port 8501
```

Abra **http://127.0.0.1:8501**. A primeira tela é o Music Explorer.
Mantenha esse terminal aberto. Para parar, pressione **Ctrl+C** nele. Para
reiniciar, execute novamente o mesmo comando. Não é necessário ativar a
`.venv` porque o comando já utiliza o Python dela.

Após mudanças no Python ou JavaScript, pare e inicie novamente para garantir
que os componentes novos sejam carregados. Após mudanças no C++, pare o servidor,
recompile e só então inicie novamente. O histórico da sessão é perdido ao reiniciar.

Se aparecer `Port 8501 is already in use`, há outro servidor nessa porta.
Encerre-o no terminal em que foi iniciado ou use `--server.port 8502` e abra
**http://127.0.0.1:8502**. Atualizar o navegador não substitui reiniciar o servidor.

Para recompilar somente o núcleo, usando o `g++` já disponível neste ambiente:

```bash
mkdir -p build
g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic -I core/include core/main.cpp core/src/*.cpp -o build/ame_core_app
```

Esse comando gera o executável usado pela aplicação. Para gerar também todos
os testes e benchmarks, use o build completo com CMake descrito abaixo.

Em uma instalação nova, prepare as dependências Python uma única vez:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r app/requirements.txt -r preprocessing/requirements.txt
```

A importação do FMA é separada e está documentada em **Dataset**, abaixo;
não é necessário importar novamente a cada execução.

## Build completo com CMake

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

## Perfil de reprodução

Iniciar o áudio no player adiciona a faixa ao histórico imediatamente, sem
tempo mínimo. Selecionar uma música, filtrar opções, buscar semelhantes ou
abrir uma página não conta como reprodução. Cada novo início (inclusive retomar
depois de pausar) incrementa a contagem da faixa. Isso vale para a referência,
as recomendações e o player do próprio perfil.

O evento `play` do player nativo é comunicado ao Python por um
[componente Streamlit v2](https://docs.streamlit.io/develop/api-reference/custom-components/st.components.v2.component).
Uma sequência por player evita contagem duplicada em reruns e preserva inícios
agrupados na mesma atualização. O núcleo C++ valida o ID e registra a reprodução
na Splay Tree da sessão, sem alterar a árvore do laboratório.

Cada faixa possui um único nó, com contador e ordem da última reprodução.
Reproduzir ou buscar uma faixa leva esse nó à raiz. A busca não incrementa o
contador nem muda a ordem de reprodução; a listagem cronológica é calculada
separadamente, pois a árvore não ordena todas as faixas por recência. A interface
mostra a árvore e as comparações/rotações da última operação em um expansor.

O histórico vive no processo C++ associado à sessão Streamlit e permanece ao
navegar entre páginas. Uma nova sessão começa vazia; não há gravação em disco.
Reiniciar o núcleo, recompilar o binário ou recarregar o dataset também limpa
esse histórico. A contagem não significa que o arquivo foi ouvido até o fim.

O Music Explorer é a página inicial. O menu lateral tem apenas Music Explorer,
Playback Profile e Structures Lab, nessa ordem.
Cada música é exibida em um cartão com título, artista, detalhes e player.
A busca filtra esses cartões. Ao ouvir pelo perfil, a reprodução é registrada
imediatamente, mas a ordem e as contagens exibidas ficam estáveis durante a visita.
O botão **Atualizar**, no canto superior direito, ou sair e voltar à página
carrega as informações mais recentes, incluindo a visualização da árvore.
Por padrão, o perfil mostra as 10 músicas distintas mais recentes. Quando houver
mais, **Ver histórico completo** expande a lista e **Ver menos** recolhe. A busca
sempre inclui todo o histórico. Expandir a lista mantém a atualização da visita;
ao sair e voltar, a página volta a mostrar as 10 mais recentes.

Os testes do histórico integram a suíte C++ e o AppTest. Com Node.js 20 ou superior,
`node --test tests/test_playback_events.mjs` verifica a captura e limpeza dos
eventos do player. Os testes opcionais do servidor também verificam o caminho
dos eventos até o perfil usando o protocolo Streamlit.
