# Adaptive Music Explorer

Busca musical adaptativa sobre o dataset **FMA Medium**, construída em torno de
duas estruturas de dados protagonistas:

- **Skip List** — índice acústico probabilístico que reduz o espaço de busca e
  recupera candidatos acusticamente próximos.
- **Splay Tree** — estrutura autoajustável que modela o perfil de reprodução do
  usuário, aproximando da raiz as músicas acessadas recentemente.

O núcleo de estruturas é escrito em **C++**; o pré-processamento dos dados e a
interface (**Streamlit**) são escritos em **Python**. O foco do projeto está nas
estruturas de dados — a interface e o dataset existem para demonstrá-las.

Veja o plano completo em `docs/plano_implementacao.md`.

## Estrutura do repositório

```
core/          Núcleo C++ (Skip List, Splay Tree, similaridade, Acoustic Key)
preprocessing/ Pipeline Python de preparação do FMA -> tracks_processed.csv
app/           Aplicação Streamlit (4 páginas)
benchmark/     Benchmarks C++ (Skip List e Splay Tree) + resultados CSV
tests/         Testes unitários do núcleo C++
data/          raw/ (FMA baixado) e processed/ (dataset gerado)
docs/          Plano e documentação experimental
```

## Build do núcleo C++

```bash
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure   # roda os testes
```

Binários gerados em `build/`:
`ame_core_app`, `benchmark_skiplist`, `benchmark_splay`, `benchmark_similarity`.

## Pipeline de dados (Python)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r preprocessing/requirements.txt
python preprocessing/build_dataset.py    # gera data/processed/tracks_processed.csv
```

## Interface (Streamlit)

```bash
pip install -r app/requirements.txt
streamlit run app/app.py
```

## Status

Scaffold inicial. As estruturas de dados e o pipeline estão declarados com
stubs marcados por `TODO`, seguindo a ordem de desenvolvimento do plano
(§40–§48). Comece pela Fase 2 (Skip List) e Fase 3 (Splay Tree) no núcleo C++.

## Equipe

Cinco integrantes, com divisão de responsabilidades descrita no plano (§39):
Skip List / Acoustic Key, Splay Tree, processamento do FMA, Streamlit, e
benchmarks / integração.
# projetoed2
