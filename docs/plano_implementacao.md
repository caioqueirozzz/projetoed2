# Adaptive Music Explorer
## Plano de Implementação — Busca Musical com Skip List e Splay Tree

## 1. Visão Geral

O projeto **Adaptive Music Explorer** será um sistema interativo de exploração e recomendação musical construído sobre o dataset **FMA (Free Music Archive) — Medium**.

A proposta central é demonstrar, na prática, como duas estruturas de dados podem ser usadas em conjunto para resolver problemas diferentes dentro de um sistema multimídia:

- **Skip List** como estrutura principal de indexação e recuperação de candidatos acusticamente próximos;
- **Splay Tree (Árvore de Afunilamento)** como estrutura adaptativa para representar o perfil de reprodução do usuário.

O sistema terá como funcionalidade principal a busca por músicas semelhantes a uma música escolhida. Como funcionalidades secundárias, permitirá:

- explorar músicas por características acústicas;
- reproduzir os áudios disponíveis;
- visualizar atributos das músicas;
- registrar o comportamento de navegação/reprodução do usuário;
- visualizar a reorganização da Splay Tree;
- comparar as estruturas implementadas com outras abordagens;
- executar benchmarks de desempenho.

O foco acadêmico e da apresentação deve permanecer nas **estruturas de dados**, e não em Machine Learning.

---

# 2. Objetivo Principal

A pergunta que orienta o projeto será:

> **Como Skip Lists e Splay Trees podem ser combinadas para tornar a busca e o acesso a músicas mais eficientes e adaptativos?**

O sistema deverá demonstrar duas estratégias distintas:

1. **Skip List**
   - reduzir o espaço de busca;
   - recuperar candidatos próximos;
   - realizar consultas em estrutura ordenada;
   - permitir análise de desempenho em inserção, remoção e busca.

2. **Splay Tree**
   - adaptar sua estrutura ao padrão de acesso do usuário;
   - aproximar itens recentemente acessados da raiz;
   - explorar localidade temporal;
   - demonstrar rotações e autoajuste.

---

# 3. Dataset

Será utilizado inicialmente o:

## FMA Medium — Free Music Archive

Características gerais:

- aproximadamente **25.000 faixas**;
- músicas com cerca de **30 segundos**;
- aproximadamente **16 gêneros**;
- arquivos de áudio;
- metadados;
- características acústicas pré-calculadas.

Arquivos relevantes:

- `tracks.csv`
- `features.csv`
- `genres.csv`
- arquivos de áudio do FMA Medium.

O projeto utilizará principalmente:

- metadados;
- features acústicas já extraídas;
- arquivos de áudio para reprodução e visualização.

A princípio, **não será necessário extrair todas as features diretamente do áudio**, pois isso desviaria o foco do trabalho para processamento digital de sinais.

---

# 4. Arquitetura Geral

```text
                  FMA MEDIUM
                     │
            ┌────────┴────────┐
            │                 │
        tracks.csv        features.csv
            │                 │
            └────────┬────────┘
                     │
              PREPROCESSAMENTO
                   Python
                     │
                     ▼
            dataset_processado
                     │
         ┌───────────┴────────────┐
         │                        │
         ▼                        ▼
      SKIP LIST                SPLAY TREE
  índice acústico          perfil de reprodução
         │                        │
         └───────────┬────────────┘
                     │
              MOTOR DE BUSCA
                    C++
                     │
                     ▼
                 Streamlit
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   Similaridade   Exploração    Perfil
     musical       acústica     adaptativo
```

---

# 5. Tecnologias

## C++

Responsável por:

- implementação da Skip List;
- implementação da Splay Tree;
- cálculo de similaridade;
- geração e uso da Acoustic Key;
- busca de candidatos;
- estruturas auxiliares;
- benchmarks;
- testes de desempenho.

## Python

Responsável por:

- leitura inicial dos arquivos do FMA;
- limpeza e preparação dos dados;
- normalização das features;
- geração do dataset processado;
- interface Streamlit;
- gráficos;
- reprodução dos áudios;
- comunicação com o núcleo em C++.

---

# 6. Representação das Músicas

Cada música será representada por uma estrutura semelhante a:

```cpp
struct Track {
    int id;

    std::string title;
    std::string artist;
    std::string genre;

    std::vector<double> features;

    uint64_t acousticKey;

    std::string audioPath;
};
```

---

# 7. Features Acústicas

O FMA fornece um conjunto amplo de características extraídas por ferramentas como Librosa.

Para o projeto, deve-se selecionar um subconjunto suficientemente informativo, mas que não torne o sistema desnecessariamente complexo.

Sugestão inicial:

- MFCC mean — 20 valores;
- Chroma CQT mean — 12 valores;
- Spectral Contrast mean — 7 valores;
- RMS mean — 1 valor;
- Zero Crossing Rate mean — 1 valor;
- Spectral Centroid mean — 1 valor;
- Spectral Bandwidth mean — 1 valor;
- Spectral Rolloff mean — 1 valor.

Total aproximado:

**44 características por música.**

---

# 8. Pré-processamento

Pipeline:

```text
dados brutos
    ↓
seleção das músicas do FMA Medium
    ↓
remoção/tratamento de valores ausentes
    ↓
seleção de features
    ↓
normalização
    ↓
geração da Acoustic Key
    ↓
dataset processado
```

A normalização é necessária porque diferentes características acústicas possuem escalas muito distintas.

Pode ser utilizada normalização Min-Max:

```text
x_normalizado = (x - min) / (max - min)
```

ou padronização Z-Score, dependendo dos testes realizados.

---

# 9. Similaridade entre Músicas

A similaridade será calculada sem Machine Learning.

O objetivo é manter o foco nas estruturas de dados.

Inicialmente será utilizada distância Euclidiana:

```text
D(A,B) = sqrt(
    Σ (Ai - Bi)²
)
```

Quanto menor a distância:

- mais semelhantes as músicas;
- maior a similaridade acústica.

Busca trivial:

```text
para cada música do dataset:
    calcular distância para a música escolhida

ordenar os resultados

retornar Top-K
```

Essa abordagem custa aproximadamente:

```text
O(n)
```

por consulta.

A Skip List será utilizada justamente para reduzir o número de músicas analisadas.

---

# 10. Skip List — Estrutura Principal de Busca

A Skip List será uma das duas estruturas protagonistas do projeto.

Ela será implementada manualmente.

Objetivos:

- armazenar as músicas de forma ordenada;
- permitir inserção eficiente;
- permitir remoção eficiente;
- localizar rapidamente uma região próxima da música consultada;
- reduzir o conjunto de candidatos usado no cálculo exato de similaridade.

---

# 11. Acoustic Key

Uma Skip List necessita de uma chave ordenável.

Porém, cada música será representada por dezenas de features.

Para permitir a indexação será criada uma:

## Acoustic Key

A Acoustic Key será uma representação numérica compacta das características acústicas da música.

Pipeline conceitual:

```text
Features acústicas
        ↓
normalização
        ↓
seleção de dimensões principais
        ↓
quantização
        ↓
linearização multidimensional
        ↓
Acoustic Key
```

Uma possibilidade inicial é usar uma estratégia inspirada em:

## Morton Code / Z-order

Exemplo:

```text
Características

RMS
ZCR
Spectral Centroid
Spectral Bandwidth
Spectral Rolloff
MFCC-1

        ↓

normalização entre 0 e 1

[0.81, 0.22, 0.73, 0.51, 0.62, 0.31]

        ↓

quantização

[829, 225, 747, 522, 634, 317]

        ↓

combinação dos bits

Acoustic Key

937182736182...
```

A finalidade é fazer com que músicas acusticamente semelhantes tendam a ocupar regiões próximas do índice.

A Acoustic Key não substituirá a distância real.

Ela servirá apenas para:

> **localizar candidatos rapidamente.**

---

# 12. Estrutura da Skip List

Modelo conceitual:

```cpp
struct SkipNode {
    uint64_t key;

    int trackId;

    std::vector<SkipNode*> forward;
};
```

Classe:

```cpp
class SkipList {
private:
    int maxLevel;
    double probability;

public:
    void insert(uint64_t key, int trackId);

    void remove(uint64_t key, int trackId);

    SkipNode* search(uint64_t key);

    std::vector<int> nearest(
        uint64_t key,
        int numberOfCandidates
    );
};
```

Operações obrigatórias:

- inserção;
- busca;
- remoção;
- vizinhança;
- percurso;
- visualização dos níveis;
- coleta de métricas.

---

# 13. Funcionamento da Busca por Similaridade

O fluxo principal será:

```text
Música selecionada
        ↓
obter vetor de features
        ↓
obter Acoustic Key
        ↓
localizar região correspondente na Skip List
        ↓
selecionar músicas vizinhas
        ↓
calcular distância acústica real
        ↓
usar Heap / Priority Queue
        ↓
retornar Top-K músicas similares
```

Exemplo:

```text
25.000 músicas
        ↓
Skip List
        ↓
500 candidatos
        ↓
distância Euclidiana
        ↓
Top 10
```

---

# 14. Priority Queue como Estrutura Complementar

Após a Skip List selecionar os candidatos, será utilizado um Heap através de:

```cpp
std::priority_queue
```

Objetivo:

- manter apenas os melhores resultados;
- evitar ordenar completamente todos os candidatos;
- recuperar o Top-K.

Fluxo:

```text
500 candidatos
        ↓
calcular distância
        ↓
Priority Queue
        ↓
10 menores distâncias
```

A Priority Queue será uma estrutura auxiliar.

Ela não deve roubar o protagonismo da Skip List.

---

# 15. Experimento da Skip List

Um dos principais experimentos será investigar:

> **Quantos candidatos devem ser recuperados para obter boa qualidade de recomendação sem perder desempenho?**

Valores a testar:

```text
50
100
250
500
1000
2500
5000
```

---

# 16. Recall@10

Para medir a qualidade da busca aproximada será utilizado:

## Recall@10

Primeiro será realizada uma busca exaustiva:

```text
música X
    ↓
comparar com todas as 25.000 músicas
    ↓
Top 10 real
```

Depois será feita a busca usando Skip List:

```text
música X
    ↓
Skip List
    ↓
N candidatos
    ↓
Top 10 aproximado
```

Calcula-se:

```text
Recall@10 =
quantidade de itens corretos encontrados / 10
```

Exemplo hipotético:

| Candidatos | Recall@10 | Tempo |
|---:|---:|---:|
| 50 | 60% | 0,08 ms |
| 100 | 70% | 0,11 ms |
| 250 | 80% | 0,19 ms |
| 500 | 90% | 0,31 ms |
| 1.000 | 100% | 0,58 ms |
| Força bruta | 100% | 7,80 ms |

Os valores reais deverão ser medidos durante a implementação.

Esse será um dos experimentos mais importantes do projeto.

---

# 17. Splay Tree — Perfil Adaptativo de Reprodução

A Splay Tree será a segunda estrutura protagonista.

Objetivo:

> representar o padrão de acesso do usuário às músicas de forma autoajustável.

Cada vez que uma música for:

- aberta;
- selecionada;
- reproduzida;
- favoritada;
- acessada por recomendação;

ela será procurada na árvore.

Após a busca:

```text
search(trackId)
        +
splay(trackId)
```

A música será movida para a raiz.

---

# 18. Estrutura da Splay Tree

Modelo:

```cpp
struct SplayNode {
    int trackId;

    int playCount;

    SplayNode* left;
    SplayNode* right;
    SplayNode* parent;
};
```

Classe:

```cpp
class SplayTree {
private:
    SplayNode* root;

    void rotateLeft(SplayNode* node);
    void rotateRight(SplayNode* node);

    void splay(SplayNode* node);

public:
    void insert(int trackId);

    SplayNode* search(int trackId);

    void remove(int trackId);

    void access(int trackId);

    SplayNode* getRoot();
};
```

---

# 19. Operações da Splay Tree

Deverão ser demonstrados explicitamente:

## Zig

Quando o nó possui pai, mas não possui avô.

## Zig-Zig

Quando nó e pai estão na mesma direção.

Exemplos:

- esquerda-esquerda;
- direita-direita.

## Zig-Zag

Quando nó e pai estão em direções diferentes.

Exemplos:

- esquerda-direita;
- direita-esquerda.

---

# 20. Perfil de Reprodução

A Splay Tree representará o contexto recente do usuário.

Exemplo de acessos:

```text
7
14
32
7
18
7
7
```

Após acessos repetidos:

```text
                [7]
               /   \
             ...   ...
```

A música mais recentemente acessada permanece próxima da raiz.

O comportamento permite demonstrar:

- localidade temporal;
- custo amortizado;
- autoajuste;
- reorganização por acesso.

---

# 21. Personalização Opcional

O sistema poderá utilizar a Splay Tree para influenciar levemente a recomendação.

Exemplo:

```text
similaridade_final =
    0.90 * similaridade_acustica
    +
    0.10 * afinidade_com_perfil
```

Essa funcionalidade deve ser opcional.

Interface:

```text
Personalização

[ OFF | ON ]
```

Isso permite comparar:

- recomendação puramente acústica;
- recomendação acústica influenciada pelo perfil.

Importante:

A personalização é uma função secundária.

O principal objetivo da Splay Tree é demonstrar comportamento adaptativo.

---

# 22. Interface Streamlit

A aplicação será organizada em quatro páginas principais.

---

# 23. Página 1 — Music Explorer

Página principal.

Funcionalidades:

- selecionar música;
- reproduzir trecho;
- visualizar artista;
- visualizar gênero;
- visualizar Acoustic Key;
- encontrar músicas semelhantes;
- ouvir resultados.

Exemplo:

```text
┌──────────────────────────────────────────────┐
│ Adaptive Music Explorer                     │
│                                              │
│ Escolha uma música                          │
│ [ Track X - Artist Y              ▼ ]       │
│                                              │
│ ▶ ━━━━━━━━━━━━━━━ 0:13 / 0:30               │
│                                              │
│ Gênero: Rock                                │
│ Acoustic Key: 827193817                     │
│                                              │
│ [ Encontrar músicas semelhantes ]           │
└──────────────────────────────────────────────┘
```

Resultados:

```text
Top 10

1. Track A        96.3%    ▶
2. Track B        93.1%    ▶
3. Track C        91.8%    ▶
...
```

---

# 24. Métricas da Busca

Cada consulta deverá exibir:

- número total de músicas;
- número de candidatos retornados;
- número de comparações;
- tempo da busca na Skip List;
- tempo de cálculo de similaridade;
- tempo total;
- Recall estimado ou calculado em modo experimental.

Exemplo:

```text
Dataset total:          25.000
Candidatos analisados:     500
Comparações realizadas:    500
Tempo Skip List:         0.10 ms
Tempo similaridade:      0.22 ms
Tempo total:             0.32 ms
```

---

# 25. Página 2 — Exploração Acústica

Objetivo:

visualizar e explorar características das músicas.

Mostrar atributos como:

```text
RMS                   █████████░
Spectral Centroid     ██████░░░░
ZCR                   ███░░░░░░░
Bandwidth             ███████░░░
Rolloff               ████████░░
```

Permitir filtros.

Exemplo:

```text
RMS
[──────●────────]

Spectral Centroid
[──────────●────]

ZCR
[────●──────────]
```

Os filtros deverão usar a região acústica da Skip List como ponto inicial e depois aplicar filtros exatos nos candidatos.

---

# 26. Página 3 — Perfil de Reprodução

Objetivo:

demonstrar a Splay Tree.

Mostrar:

- música atual;
- última música acessada;
- número de acessos;
- número de comparações;
- número de rotações;
- altura da árvore;
- profundidade do elemento antes do splay;
- profundidade depois do splay.

---

# 27. Visualização da Splay Tree

Exemplo:

```text
             12
           /    \
          7      28
        /  \    /  \
       ...
```

Depois de acessar uma música:

```text
             22
            /  \
          12    28
         / ...
```

A interface deverá mostrar:

- árvore antes;
- operação realizada;
- árvore depois.

Também deverá indicar:

```text
zig
zig-zig
zig-zag
```

---

# 28. Página 4 — Laboratório de Estruturas

Essa página será dedicada exclusivamente à disciplina de Estrutura de Dados.

Ela deverá permitir demonstração isolada das duas estruturas.

---

# 29. Laboratório — Skip List

Visualização aproximada:

```text
Level 4 ──────────●───────────────────●
Level 3 ─────●────●─────────●─────────●
Level 2 ──●──●────●────●────●────●────●
Level 1 ●─●──●─●──●─●──●─●──●─●──●─●──●
```

Permitir:

- inserir;
- buscar;
- remover;
- visualizar níveis;
- mostrar percurso;
- contar comparações;
- medir tempo.

---

# 30. Laboratório — Splay Tree

Permitir:

- inserir nó;
- buscar nó;
- remover nó;
- executar acesso;
- visualizar árvore;
- mostrar rotações;
- mostrar nó atual;
- mostrar raiz anterior;
- mostrar nova raiz.

---

# 31. Benchmarks

Os benchmarks deverão ter protagonismo na apresentação.

---

# 32. Benchmark da Skip List

Comparar:

```text
Skip List

vs.

vector ordenado + binary_search

vs.

std::map
```

Operações:

- inserção;
- busca;
- remoção;
- busca de vizinhança;
- atualização.

Tamanhos:

```text
1.000
5.000
10.000
15.000
20.000
25.000
```

Métricas:

- tempo;
- número de comparações;
- consumo aproximado de memória;
- custo de inserção;
- custo de remoção;
- custo de busca.

---

# 33. Benchmark da Splay Tree

Comparar:

```text
Splay Tree

vs.

BST

vs.

AVL ou std::map
```

Executar dois cenários.

---

# 34. Cenário A — Distribuição Uniforme

Todas as músicas possuem aproximadamente a mesma probabilidade de acesso.

Exemplo:

```text
P(track_i) ≈ constante
```

Medir:

- comparações;
- profundidade média;
- rotações;
- tempo médio de busca.

---

# 35. Cenário B — Localidade de Acesso

Simular comportamento semelhante ao real.

Exemplo:

```text
20% das músicas
recebem
80% dos acessos
```

Esse cenário deverá favorecer a discussão sobre autoajuste.

Medir:

- comparações;
- profundidade média;
- profundidade das músicas mais populares;
- rotações;
- tempo;
- custo amortizado.

---

# 36. Gráficos de Benchmark

Sugestões:

## Skip List

- tempo × tamanho do dataset;
- inserção × estrutura;
- busca × estrutura;
- remoção × estrutura;
- número de comparações × estrutura;
- Recall@10 × número de candidatos;
- tempo × número de candidatos.

## Splay Tree

- tempo × padrão de acesso;
- profundidade média × número de acessos;
- número de comparações × estrutura;
- profundidade dos elementos frequentes;
- número de rotações;
- custo acumulado;
- árvore antes/depois de sequências de acesso.

---

# 37. Estruturas Complementares

Além das estruturas obrigatórias, poderão ser usadas:

## Priority Queue / Heap

Para:

- Top-K músicas similares.

## Unordered Map

Para:

- localizar metadados rapidamente;
- associar `track_id` a objetos Track;
- organizar artistas;
- organizar gêneros.

## Vector

Para:

- armazenar features;
- resultados temporários;
- listas de candidatos.

Essas estruturas devem ser tratadas como auxiliares.

---

# 38. Organização do Repositório

```text
adaptive-music-explorer/

├── README.md
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── README.md
│
├── preprocessing/
│   ├── load_fma.py
│   ├── clean_features.py
│   ├── normalize.py
│   └── build_dataset.py
│
├── core/
│   ├── include/
│   │   ├── skip_list.hpp
│   │   ├── splay_tree.hpp
│   │   ├── track.hpp
│   │   ├── similarity.hpp
│   │   └── acoustic_key.hpp
│   │
│   ├── src/
│   └── main.cpp
│
├── benchmark/
│   ├── benchmark_skiplist.cpp
│   ├── benchmark_splay.cpp
│   ├── benchmark_similarity.cpp
│   └── results/
│
├── app/
│   ├── app.py
│   ├── pages/
│   ├── components/
│   └── services/
│
├── tests/
│   ├── test_skiplist.cpp
│   ├── test_splay.cpp
│   └── test_similarity.cpp
│
└── docs/
```

---

# 39. Divisão da Equipe

Grupo com cinco integrantes.

## Pessoa 1

Responsável por:

- Skip List;
- Acoustic Key;
- operações de índice;
- testes da Skip List.

## Pessoa 2

Responsável por:

- Splay Tree;
- rotações;
- perfil adaptativo;
- visualização da árvore.

## Pessoa 3

Responsável por:

- processamento do FMA;
- seleção das features;
- normalização;
- similaridade acústica.

## Pessoa 4

Responsável por:

- Streamlit;
- player de áudio;
- gráficos;
- experiência da aplicação.

## Pessoa 5

Responsável por:

- benchmarks;
- integração;
- testes;
- coleta de métricas;
- documentação experimental.

Todos os membros devem entender:

- funcionamento da Skip List;
- funcionamento da Splay Tree;
- papel de cada estrutura no sistema.

---

# 40. Ordem de Desenvolvimento

## Fase 1 — Preparação do Dataset

Tarefas:

- baixar FMA Medium;
- baixar metadados;
- selecionar músicas correspondentes;
- carregar `tracks.csv`;
- carregar `features.csv`;
- selecionar features;
- tratar valores ausentes;
- normalizar;
- gerar arquivo processado.

Entregável:

```text
tracks_processed.csv
```

---

# 41. Fase 2 — Skip List

Implementar:

- nó;
- geração aleatória de nível;
- inserção;
- busca;
- remoção;
- busca por vizinhança;
- percurso;
- métricas internas;
- testes.

---

# 42. Fase 3 — Splay Tree

Implementar:

- nó;
- rotação esquerda;
- rotação direita;
- Zig;
- Zig-Zig;
- Zig-Zag;
- inserção;
- busca;
- acesso;
- remoção;
- coleta de métricas;
- testes.

---

# 43. Fase 4 — Acoustic Key

Implementar:

- escolha das dimensões;
- normalização;
- quantização;
- linearização;
- geração de `uint64_t`;
- testes de proximidade.

Verificar empiricamente:

> músicas acusticamente próximas realmente aparecem próximas na ordenação?

---

# 44. Fase 5 — Motor de Similaridade

Implementar:

```text
música
    ↓
Skip List
    ↓
candidatos
    ↓
distância
    ↓
Top-K
```

Primeiramente usar:

```text
500 candidatos
```

Depois tornar esse valor configurável.

---

# 45. Fase 6 — Perfil Adaptativo

Integrar:

```text
reprodução
    ↓
Splay Tree
    ↓
acesso
    ↓
splay
```

Registrar:

- quantidade de acessos;
- última reprodução;
- profundidade antes;
- profundidade depois;
- rotações.

---

# 46. Fase 7 — Benchmarks

Executar antes da construção final da interface.

Primeiro:

- Skip List × vector × map.

Depois:

- Splay × BST × AVL/map.

Gerar CSVs com resultados.

Exemplo:

```text
benchmark_skiplist.csv

benchmark_splay_uniform.csv

benchmark_splay_locality.csv

benchmark_recall.csv
```

---

# 47. Fase 8 — Streamlit

Construir somente após o núcleo estar funcional.

Criar páginas:

```text
Music Explorer

Acoustic Explorer

Playback Profile

Structures Lab
```

---

# 48. MVP Obrigatório

O projeto será considerado funcional quando conseguir executar a seguinte demonstração:

1. selecionar uma música;
2. reproduzir o áudio;
3. mostrar suas características;
4. gerar Acoustic Key;
5. localizar região correspondente na Skip List;
6. recuperar candidatos;
7. calcular similaridade;
8. mostrar Top 10;
9. ouvir uma recomendação;
10. registrar acesso na Splay Tree;
11. visualizar árvore antes;
12. executar Splay;
13. visualizar árvore depois;
14. demonstrar Zig, Zig-Zig ou Zig-Zag;
15. abrir área de benchmarks;
16. comparar Skip List com outras estruturas;
17. comparar Splay Tree em acesso uniforme e localizado.

---

# 49. Critérios de Qualidade

## Obrigatórios

- Skip List implementada manualmente;
- Splay Tree implementada manualmente;
- testes unitários;
- interface funcional;
- áudio reproduzível;
- benchmark reproduzível;
- documentação.

## Desejáveis

- visualização da Skip List;
- visualização animada da Splay Tree;
- personalização opcional;
- exportação dos benchmarks;
- configuração do número de candidatos;
- comparação com força bruta;
- Recall@K.

---

# 50. Perguntas que o Projeto Deve Responder

Ao final, o projeto deverá permitir responder:

### Skip List

- A Skip List reduz o número de candidatos necessários?
- Quanto tempo ela economiza?
- Quantos candidatos são necessários para preservar boa qualidade?
- Como ela se compara ao vector ordenado?
- Como ela se compara ao `std::map`?
- Qual o custo de inserção e remoção?

### Splay Tree

- O autoajuste melhora sequências com localidade?
- O que acontece com acessos uniformes?
- Quantas rotações são realizadas?
- A profundidade das músicas mais acessadas diminui?
- Como ela se compara a BST e AVL?

---

# 51. História Central para a Apresentação

A apresentação deve seguir esta lógica:

> Um algoritmo trivial de recomendação precisa comparar a música selecionada com todas as demais músicas do dataset. O Adaptive Music Explorer utiliza uma Skip List como índice probabilístico para localizar rapidamente uma região acústica e reduzir o conjunto de candidatos antes da comparação exata.

Em paralelo:

> O comportamento de reprodução do usuário apresenta localidade temporal. A Splay Tree explora essa característica reorganizando dinamicamente a árvore e aproximando músicas recentemente acessadas da raiz.

Assim, o projeto investiga duas estratégias:

```text
Skip List
        ↓
indexação probabilística
        ↓
redução do espaço de busca


Splay Tree
        ↓
estrutura autoajustável
        ↓
exploração de localidade de acesso
```

---

# 52. Diferencial do Trabalho

O diferencial não será apenas implementar duas estruturas.

O projeto deverá demonstrar:

- quando elas funcionam bem;
- quando não funcionam tão bem;
- quais custos possuem;
- como se comportam sob diferentes cargas;
- como interagem dentro de um sistema real.

Portanto, o projeto combina:

```text
Estrutura de Dados
        +
Dataset real
        +
Áudio
        +
Busca aproximada
        +
Benchmark
        +
Visualização
        +
Interface interativa
```

---

# 53. Resultado Esperado

Ao final, o Adaptive Music Explorer será uma aplicação capaz de:

- explorar o FMA Medium;
- reproduzir músicas;
- encontrar músicas acusticamente semelhantes;
- usar Skip List para restringir candidatos;
- calcular Top-K;
- registrar padrão de reprodução;
- reorganizar uma Splay Tree;
- visualizar as duas estruturas;
- executar benchmarks;
- comparar estruturas;
- gerar gráficos;
- demonstrar experimentalmente seus comportamentos.

O objetivo maior é que, durante a apresentação, fique evidente que:

> **a interface e o dataset existem para demonstrar as estruturas de dados, e não o contrário.**

A Skip List e a Splay Tree devem permanecer como protagonistas durante todo o projeto.
