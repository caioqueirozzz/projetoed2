"""Independent, bounded laboratories and reproducible experimental evidence."""
from __future__ import annotations
import sys
import subprocess
import json
from pathlib import Path
import streamlit as st
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.core_bridge import get_bridge
from services.dataset import PROCESSED_CSV
from services.benchmarks import provenance_warnings, read_benchmark

ROOT = Path(__file__).resolve().parents[2]
st.set_page_config(page_title="Structures Lab — AME", layout="wide")
st.title("Laboratório de Estruturas")
st.caption("Experimente Skip List e Splay Tree em estruturas independentes do catálogo musical. Limite de 128 nós por laboratório; desenho da Splay limitado a 40 nós.")
bridge = get_bridge()
if bridge is None:
    st.error(st.session_state.get("bridge_error", "Núcleo indisponível")); st.stop()
sl_tab, sp_tab, bench_tab = st.tabs(["Skip List", "Splay Tree", "Benchmarks"])
with sl_tab:
    # Outside the form so each operation immediately displays only its own inputs.
    operations = {"Inserir": "insert", "Buscar": "search", "Remover": "remove", "Atualizar chave": "update", "Percorrer": "traverse", "Limpar": "reset"}
    op = st.selectbox("Operação da Skip List", list(operations), key="sl_operation")
    state = bridge.lab_skip()
    nodes = state["levels"][0] if state["levels"] else []
    node_options = {f"{node['key']}:{node['id']}": node for node in nodes}
    if st.session_state.get("sl_target") not in node_options:
        st.session_state.pop("sl_target", None)
    if op == "Buscar":
        st.caption("Informe a chave para encontrar todos os nós com esse valor. Os IDs aparecem no resultado.")
    elif op in {"Remover", "Atualizar chave"}:
        st.caption("Escolha o nó cadastrado. O ID distingue nós que têm a mesma chave.")
        if not nodes:
            st.info("A Skip List está vazia. Insira um nó primeiro.")
    with st.form("sl_form"):
        key, tid, new_key = "0", 0, "0"
        if op in {"Inserir", "Buscar"}:
            key = st.text_input("Chave inteira sem sinal", "10", key="sl_key")
        if op == "Inserir":
            tid = st.number_input("ID do nó", 1, 2147483647, 1, key="sl_id")
        if op in {"Remover", "Atualizar chave"}:
            target = st.selectbox("Nó a remover" if op == "Remover" else "Nó a atualizar", list(node_options),
                                 format_func=lambda value: f"Chave {node_options[value]['key']} — ID {node_options[value]['id']}",
                                 key="sl_target", disabled=not nodes)
            if target is not None:
                key, tid = node_options[target]["key"], node_options[target]["id"]
        if op == "Atualizar chave":
            new_key = st.text_input("Nova chave (atualização)", "20", key="sl_new_key")
        submit = st.form_submit_button("Executar operação na Skip List", disabled=op in {"Remover", "Atualizar chave"} and not nodes)
    if submit:
        try:
            try:
                k, nk = int(key), int(new_key)
            except ValueError:
                raise ValueError("Digite uma chave inteira válida.") from None
            if not (0 <= k < 2**64 and 0 <= nk < 2**64):
                raise ValueError("As chaves devem estar entre 0 e 2⁶⁴−1.")
            st.session_state.sl_lab_result = bridge.lab_skip(operations[op], k, int(tid), nk)
            st.rerun()
        except (ValueError, RuntimeError) as exc:
            st.session_state.pop("sl_lab_result", None)
            st.error(str(exc))
    result = st.session_state.get("sl_lab_result")
    if result:
        action, outcome = result["operation"], result["outcome"]
        st.caption(f"Última operação executada: {next(label for label, code in operations.items() if code == action)}")
        if action == "search":
            if result["matches"]:
                st.success(f"Chave {result['key']}: {len(result['matches'])} nó(s) encontrado(s).")
                st.dataframe([{"Chave": node["key"], "ID": node["id"]} for node in result["matches"]], hide_index=True, width="stretch")
            else:
                st.info(f"Nenhum nó encontrado com a chave {result['key']}.")
        elif action == "traverse":
            ordered = result["levels"][0] if result["levels"] else []
            if ordered:
                st.success(f"Percurso completo: {len(ordered)} nó(s), em ordem de chave e ID.")
                st.dataframe([{"Chave": node["key"], "ID": node["id"]} for node in ordered], hide_index=True, width="stretch")
            else:
                st.info("A Skip List está vazia; não há nós para percorrer.")
        elif action == "reset":
            st.success("Skip List limpa: nenhum nó armazenado.")
        elif outcome == "duplicate":
            duplicate_key = result["new_key"] if action == "update" else result["key"]
            st.warning(f"O nó com chave {duplicate_key} e ID {result['id']} já existe. Nenhum nó foi alterado.")
        elif outcome == "not_found":
            st.warning(f"Nó com chave {result['key']} e ID {result['id']} não encontrado.")
        elif outcome == "unchanged":
            st.info(f"O nó de ID {result['id']} já tem a chave {result['key']}. Nenhuma alteração necessária.")
        elif action == "update":
            st.success(f"Nó de ID {result['id']}: chave alterada de {result['key']} para {result['new_key']}.")
        else:
            st.success(f"Nó com chave {result['key']} e ID {result['id']} {'inserido' if action == 'insert' else 'removido'}.")
    a, b, c = st.columns(3)
    a.metric("Nós na Skip List do laboratório", state["size"])
    b.metric("Níveis reais", len(state["levels"]) if state["size"] else 0)
    c.metric("Comparações da última operação", state["comparisons"])
    if result:
        st.caption(f"Tempo da última operação: {result['operation_ms']:.4f} ms. Comparações contam testes de ordenação/chave; avanços e memória não são comparações.")
        if result["path"] and result["operation"] != "traverse":
            st.write("Avanços da última operação (nível, ID):", result["path"])
    st.subheader("Níveis e ligações reais")
    lines = []
    for level in reversed(range(len(state["levels"]))):
        chain = " → ".join(f"{node['key']} (#{node['id']})" for node in state["levels"][level])
        lines.append(f"Nível {level}: HEAD → {chain + ' → ' if chain else ''}∅")
    st.code("\n".join(lines), language=None)
    st.caption("O nível 0 é o percurso completo em ordem (chave, ID). A mesma semente reproduz os níveis para a mesma sequência de operações.")
with sp_tab:
    operations = {"Inserir": "insert", "Buscar": "search", "Remover": "remove", "Acessar ou inserir": "access", "Limpar": "reset"}
    op = st.selectbox("Operação da Splay Tree", list(operations), key="sp_operation")
    st.caption("Nesta árvore, o ID é a própria chave de busca.")
    if op == "Acessar ou inserir":
        st.caption("Acessa o ID e o move para a raiz. Se ele não existir, insere um novo nó.")
    with st.form("sp_form"):
        tid = st.number_input("ID na Splay", 1, 2147483647, 1, key="sp_id") if op != "Limpar" else 0
        submit = st.form_submit_button("Executar operação na Splay")
    if submit:
        try:
            st.session_state.sp_lab_result = bridge.lab_splay(operations[op], int(tid))
            st.rerun()
        except (ValueError, RuntimeError) as exc:
            st.session_state.pop("sp_lab_result", None)
            st.error(str(exc))
    state = bridge.lab_splay()
    result = st.session_state.get("sp_lab_result")
    if result:
        outcome, action = result["outcome"], result["operation"]
        st.caption(f"Última operação executada: {next(label for label, code in operations.items() if code == action)}")
        if outcome == "reset":
            st.success("Splay Tree limpa: nenhum nó armazenado.")
        elif outcome == "not_found":
            detail = "A árvore está vazia." if state["root_id"] < 0 else f"O último nó visitado, ID {state['root_id']}, foi movido para a raiz."
            st.info(f"ID {result['id']} não encontrado. {detail}")
        elif outcome == "removed":
            st.success(f"Nó de ID {result['id']} removido.")
        elif outcome == "inserted":
            st.success(f"ID {result['id']} inserido e posicionado na raiz.")
        elif outcome == "existing" and action == "insert":
            st.info(f"ID {result['id']} já existe. O nó foi movido para a raiz, sem criar uma cópia.")
        else:
            st.success(f"ID {result['id']} {'encontrado' if action == 'search' else 'acessado'} e posicionado na raiz.")
    a, b, c = st.columns(3)
    a.metric("Raiz atual do laboratório", state["root_id"] if state["root_id"] >= 0 else "—")
    b.metric("Altura", state["height"])
    c.metric("Nós na Splay do laboratório", state["size"])
    result = st.session_state.get("sp_lab_result")
    if result:
        st.write("Sequência completa: " + (" → ".join(result["steps"]) or "Sem rotação"))
        a, b, c, d = st.columns(4)
        a.metric("Comparações", result["comparisons"])
        b.metric("Rotações", result["rotations"])
        c.metric("Raiz anterior", result["previous_root"] if result["previous_root"] >= 0 else "—")
        d.metric("Tempo da operação (ms)", f"{result['operation_ms']:.4f}")
        a, b = st.columns(2)
        with a:
            st.write("Antes"); st.code(result["tree_before"], language=None)
        with b:
            st.write("Depois"); st.code(result["tree_ascii"], language=None)
    else:
        st.code(state["tree_ascii"], language=None)
    with st.expander("Sequências para demonstrar rotações"):
        st.markdown("Comece com **Limpar** em cada exemplo.\n\n"
                    "- Zig: insira 20, insira 10, busque 20.\n"
                    "- Zig-Zig: insira 1, 2 e 3; busque 1.\n"
                    "- Zig-Zag: insira 3, 1 e 2.\n"
                    "- Sequência mista: insira 1, 2, 3 e 4; busque 1.\n\n"
                    "A busca e a remoção ausentes também afunilam o último nó visitado. "
                    "A complexidade amortizada das operações é O(log n); uma operação isolada pode custar O(n). "
                    "Repetir o acesso à raiz custa O(1); popularidade por si só não garante custo constante para qualquer distribuição.")
with bench_tab:
    st.subheader("Experimentos reproduzíveis")
    st.caption("Tempos variam com a máquina e a carga. As tabelas incluem sementes, repetições, contagens reais e memória estimada. Campos não observáveis do std::map ficam vazios.")
    if st.button("Executar todos os benchmarks", key="run_benchmarks"):
        try:
            with st.spinner("Executando experimentos na base atual..."):
                result = subprocess.run([sys.executable, str(ROOT / "benchmark/run_benchmarks.py"), "--dataset", str(PROCESSED_CSV)], capture_output=True, text=True, timeout=180)
            if result.returncode:
                st.error(result.stderr[-3000:])
            else:
                st.success("Resultados atualizados.")
        except (OSError, subprocess.TimeoutExpired) as exc:
            st.error(str(exc))
    for warning in provenance_warnings(ROOT, PROCESSED_CSV):
        st.warning(warning + " Os dados abaixo são históricos até uma nova execução.")
    directory = ROOT / "benchmark/results"
    labels = {"benchmark_recall.csv": "Precisão e tempo da busca musical", "benchmark_skiplist.csv": "Skip List × vetor × árvore balanceada",
              "benchmark_splay_uniform.csv": "Splay × BST × árvore balanceada: uniforme",
              "benchmark_splay_locality.csv": "Splay × BST × árvore balanceada: localidade"}
    for filename, label in labels.items():
        st.subheader(label)
        path = directory / filename
        if not path.is_file():
            st.info("Experimento ainda não executado."); continue
        try:
            data = read_benchmark(path)
        except ValueError as exc:
            st.warning(str(exc)); continue
        st.dataframe(data, hide_index=True, width="stretch")
        st.download_button("Baixar CSV", path.read_bytes(), file_name=filename, mime="text/csv", key=filename)
        if filename == "benchmark_recall.csv" and "mode" in data:
            summary = data.groupby(["mode", "num_candidates"])[["recall_at_10", "avg_query_ms", "brute_force_ms", "avg_evaluated"]].agg(["mean", "std"])
            st.dataframe(summary, width="stretch")
            st.line_chart(data.pivot_table(index="num_candidates", columns="mode", values="recall_at_10"))
        elif "structure" in data:
            selected = data
            if "operation" in data:
                operation = st.selectbox("Operação comparada", data.operation.unique(), key="bench_operation")
                selected = data[data.operation == operation]
            st.dataframe(selected.groupby(["structure", "n"])["time_ms"].agg(["mean", "std"]), width="stretch")
            st.line_chart(selected.pivot_table(index="n", columns="structure", values="time_ms"))
    path = directory / "benchmark_splay_progress.csv"
    progress = None
    if path.is_file():
        try:
            progress = read_benchmark(path)
        except ValueError as exc:
            st.warning(str(exc))
    if progress is not None:
        st.subheader("Custo acumulado dos acessos")
        data = progress
        scenario = st.selectbox("Padrão de acesso", data.scenario.unique())
        size = st.selectbox("Tamanho da árvore", sorted(data.n.unique()))
        selected = data[(data.scenario == scenario) & (data.n == size)]
        st.line_chart(selected.pivot_table(index="accesses", columns="structure", values="cumulative_comparisons"))
    manifest = directory / "manifest.json"
    if manifest.is_file():
        with st.expander("Ambiente e identificação dos arquivos usados"):
            try:
                st.json(json.loads(manifest.read_text()))
            except (OSError, ValueError) as exc:
                st.warning(f"Identificação dos resultados indisponível: {exc}")
