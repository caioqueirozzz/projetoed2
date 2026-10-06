"""Regressions for visible state, all laboratory operations and page isolation."""
from __future__ import annotations
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'app'), str(ROOT / 'preprocessing')]
from build_dataset import build
from fma_fixture import make_fma
from services import core_bridge, dataset
CORE = Path(os.environ.get('AME_CORE_BINARY', ROOT / 'build/ame_core_app'))

@unittest.skipUnless(CORE.is_file(), 'Build core first')
class UIRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        make_fma(root / 'raw')
        with contextlib.redirect_stdout(io.StringIO()):
            build(root / 'raw', root / 'processed')
        cls.csv = root / 'processed/tracks_processed.csv'
    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
    def setUp(self):
        actual = core_bridge.CoreBridge
        self.bridge_type = actual
        self.patches = [patch.object(dataset, 'PROCESSED_CSV', self.csv),
                        patch.object(core_bridge, 'CSV', self.csv),
                        patch.object(core_bridge, 'BINARY', CORE),
                        patch.object(core_bridge, 'CoreBridge', lambda: actual(CORE, self.csv))]
        for p in self.patches: p.start()
        self.apps = []
    def tearDown(self):
        for at in self.apps:
            if 'bridge' in at.session_state and at.session_state['bridge']:
                at.session_state['bridge'].close()
        for p in reversed(self.patches): p.stop()
    def page(self, name):
        at = AppTest.from_file(str(ROOT / 'app' / name), default_timeout=30).run()
        self.apps.append(at); self.assertFalse(at.exception)
        return at
    def widget(self, at, kind, label):
        return next(w for w in getattr(at, kind) if w.label == label)
    def click(self, at, label):
        self.widget(at, 'button', label).click().run()
        self.assertFalse(at.exception)
    def metric(self, at, label):
        return self.widget(at, 'metric', label).value
    def test_music_hides_stale_results_and_measures_recall(self):
        at = self.page('pages/1_Music_Explorer.py')
        self.widget(at, 'checkbox', 'Comparar com busca exaustiva (Recall@K)').check().run()
        self.click(at, 'Encontrar músicas semelhantes')
        self.assertEqual(len(at.dataframe[0].value), 2)
        self.assertEqual(self.metric(at, 'Recall@2 medido'), '100.0%')
        self.widget(at, 'slider', 'Top-K resultados').set_value(1).run()
        self.assertEqual(len(at.dataframe), 0)
        self.assertTrue(any('parâmetros mudaram' in x.value for x in at.info))
        self.click(at, 'Encontrar músicas semelhantes')
        self.assertEqual(len(at.dataframe[0].value), 1)
    def test_lab_state_updates_immediately_and_is_independent(self):
        at = self.page('pages/2_Structures_Lab.py')
        self.click(at, 'Executar operação na Skip List')
        self.assertEqual(self.metric(at, 'Nós na Skip List do laboratório'), '1')
        self.widget(at, 'selectbox', 'Operação da Skip List').set_value('Atualizar chave').run()
        self.click(at, 'Executar operação na Skip List')
        self.assertTrue(any('20 (#1)' in c.value for c in at.code))
        self.widget(at, 'selectbox', 'Operação da Skip List').set_value('Remover').run()
        self.click(at, 'Executar operação na Skip List')
        self.assertEqual(self.metric(at, 'Nós na Skip List do laboratório'), '0')
        for i in range(1, 5):
            self.widget(at, 'number_input', 'ID na Splay').set_value(i)
            self.click(at, 'Executar operação na Splay')
            self.assertEqual(self.metric(at, 'Raiz atual do laboratório'), str(i))
        self.widget(at, 'selectbox', 'Operação da Splay Tree').set_value('Buscar').run()
        self.widget(at, 'number_input', 'ID na Splay').set_value(1)
        self.click(at, 'Executar operação na Splay')
        self.assertTrue(any('ZigZig → Zig' in x.value for x in at.markdown))
        bridge = at.session_state['bridge']
        self.assertEqual(bridge.track_count, 3)
        self.assertEqual(bridge.get_skiplist_state().size, 3)
        self.assertEqual(len(bridge.find_similar(2, 50, 10)[0]), 2)
    def test_navigation_preserves_search_and_isolates_laboratory(self):
        at = self.page('app.py')
        self.assertEqual({link.label for link in at.get('page_link')},
                         {'Music Explorer', 'Structures Lab'})
        self.assertEqual({path.name for path in (ROOT / 'app/pages').glob('*.py')},
                         {'1_Music_Explorer.py', '2_Structures_Lab.py'})
        at.switch_page('pages/1_Music_Explorer.py').run()
        self.assertFalse(at.exception)
        self.click(at, 'Encontrar músicas semelhantes')
        expected = at.dataframe[0].value.copy()
        self.assertEqual([button.label for button in at.button], ['Encontrar músicas semelhantes'])
        bridge = at.session_state['bridge']
        self.assertEqual(bridge.lab_splay()['size'], 0)

        at.switch_page('pages/2_Structures_Lab.py').run()
        self.assertFalse(at.exception)
        self.widget(at, 'selectbox', 'Operação da Splay Tree').set_value('Acessar ou inserir').run()
        self.widget(at, 'number_input', 'ID na Splay').set_value(999)
        self.click(at, 'Executar operação na Splay')
        self.assertEqual(self.metric(at, 'Raiz atual do laboratório'), '999')
        self.widget(at, 'selectbox', 'Operação da Splay Tree').set_value('Remover').run()
        self.click(at, 'Executar operação na Splay')
        self.assertEqual(self.metric(at, 'Nós na Splay do laboratório'), '0')

        at.switch_page('pages/1_Music_Explorer.py').run()
        self.assertFalse(at.exception)
        self.assertIs(at.session_state['bridge'], bridge)
        self.assertTrue(at.dataframe[0].value.equals(expected))
        self.assertEqual(bridge.track_count, 3)
    def test_laboratory_runs_without_music_dataset(self):
        missing = self.csv.with_name('not_imported.csv')
        with patch.object(dataset, 'PROCESSED_CSV', missing), \
             patch.object(core_bridge, 'CSV', missing), \
             patch.object(core_bridge, 'CoreBridge', lambda: self.bridge_type(CORE, missing)):
            at = self.page('app.py')
            self.assertFalse(at.session_state['bridge'].is_loaded)
            at.switch_page('pages/2_Structures_Lab.py').run()
            self.assertFalse(at.exception)
            self.click(at, 'Executar operação na Skip List')
            self.click(at, 'Executar operação na Splay')
            self.assertEqual(self.metric(at, 'Nós na Skip List do laboratório'), '1')
            self.assertEqual(self.metric(at, 'Nós na Splay do laboratório'), '1')
            at.switch_page('pages/1_Music_Explorer.py').run()
            self.assertFalse(at.exception)
            self.assertTrue(any('Importe o FMA' in warning.value for warning in at.warning))
    def test_skip_operations_validate_only_their_required_fields(self):
        at = self.page('pages/2_Structures_Lab.py')
        self.assertEqual([w.label for w in at.text_input], ['Chave inteira sem sinal'])
        self.click(at, 'Executar operação na Skip List')
        self.widget(at, 'selectbox', 'Operação da Skip List').set_value('Atualizar chave').run()
        self.assertEqual([w.label for w in at.text_input], ['Nova chave (atualização)'])
        self.assertFalse(any(w.label == 'ID do nó' for w in at.number_input))
        self.widget(at, 'text_input', 'Nova chave (atualização)').set_value('inválida')
        self.click(at, 'Executar operação na Skip List')
        self.assertTrue(any('chave inteira válida' in e.value for e in at.error))
        self.assertEqual(self.metric(at, 'Nós na Skip List do laboratório'), '1')
        for operation, size in [('Percorrer', '1'), ('Limpar', '0')]:
            self.widget(at, 'selectbox', 'Operação da Skip List').set_value(operation).run()
            self.assertEqual(len(at.text_input), 0)
            self.assertFalse(any(w.label == 'ID do nó' for w in at.number_input))
            self.click(at, 'Executar operação na Skip List')
            self.assertFalse(at.error)
            self.assertEqual(self.metric(at, 'Nós na Skip List do laboratório'), size)
        for operation in ['Remover', 'Atualizar chave']:
            self.widget(at, 'selectbox', 'Operação da Skip List').set_value(operation).run()
            self.assertTrue(self.widget(at, 'button', 'Executar operação na Skip List').disabled)

    def test_skip_search_returns_ids_and_mutations_select_existing_nodes(self):
        at = self.page('pages/2_Structures_Lab.py')
        for key, tid in [('60', 9), ('60', 6), ('70', 6)]:
            self.widget(at, 'text_input', 'Chave inteira sem sinal').set_value(key)
            self.widget(at, 'number_input', 'ID do nó').set_value(tid)
            self.click(at, 'Executar operação na Skip List')
        self.click(at, 'Executar operação na Skip List')
        self.assertTrue(any('já existe' in w.value for w in at.warning))
        self.assertEqual(self.metric(at, 'Nós na Skip List do laboratório'), '3')
        self.widget(at, 'selectbox', 'Operação da Skip List').set_value('Buscar').run()
        self.assertFalse(any(w.label == 'ID do nó' for w in at.number_input))
        self.assertEqual([w.label for w in at.text_input], ['Chave inteira sem sinal'])
        self.widget(at, 'text_input', 'Chave inteira sem sinal').set_value('60')
        self.click(at, 'Executar operação na Skip List')
        self.assertEqual(at.dataframe[0].value.to_dict('records'), [{'Chave': '60', 'ID': 6}, {'Chave': '60', 'ID': 9}])
        self.widget(at, 'text_input', 'Chave inteira sem sinal').set_value('61')
        self.click(at, 'Executar operação na Skip List')
        self.assertFalse(any(list(frame.value.columns) == ['Chave', 'ID'] for frame in at.dataframe))
        self.assertTrue(any('Nenhum nó encontrado com a chave 61' in e.value for e in at.info))
        self.widget(at, 'selectbox', 'Operação da Skip List').set_value('Atualizar chave').run()
        self.widget(at, 'selectbox', 'Nó a atualizar').set_value('60:6')
        self.widget(at, 'text_input', 'Nova chave (atualização)').set_value('70')
        self.click(at, 'Executar operação na Skip List')
        self.assertTrue(any('já existe' in w.value for w in at.warning))
        self.assertEqual(self.metric(at, 'Nós na Skip List do laboratório'), '3')
        self.widget(at, 'text_input', 'Nova chave (atualização)').set_value('60')
        self.click(at, 'Executar operação na Skip List')
        self.assertTrue(any('Nenhuma alteração necessária' in i.value for i in at.info))
        self.widget(at, 'text_input', 'Nova chave (atualização)').set_value('80')
        self.click(at, 'Executar operação na Skip List')
        self.assertTrue(any('de 60 para 80' in s.value for s in at.success))
        self.widget(at, 'selectbox', 'Operação da Skip List').set_value('Remover').run()
        self.assertFalse(at.text_input)
        self.widget(at, 'selectbox', 'Nó a remover').set_value('60:9')
        self.click(at, 'Executar operação na Skip List')
        self.assertEqual(self.metric(at, 'Nós na Skip List do laboratório'), '2')
        self.assertEqual(self.widget(at, 'selectbox', 'Nó a remover').options, ['Chave 70 — ID 6', 'Chave 80 — ID 6'])
        self.widget(at, 'selectbox', 'Operação da Skip List').set_value('Percorrer').run()
        self.click(at, 'Executar operação na Skip List')
        self.assertEqual(at.dataframe[0].value.to_dict('records'), [{'Chave': '70', 'ID': 6}, {'Chave': '80', 'ID': 6}])

    def test_splay_reports_found_missing_existing_and_access_insertion(self):
        at = self.page('pages/2_Structures_Lab.py')
        self.click(at, 'Executar operação na Splay')
        self.click(at, 'Executar operação na Splay')
        self.assertTrue(any('já existe' in i.value for i in at.info))
        self.assertEqual(self.metric(at, 'Nós na Splay do laboratório'), '1')
        self.widget(at, 'selectbox', 'Operação da Splay Tree').set_value('Buscar').run()
        self.widget(at, 'number_input', 'ID na Splay').set_value(99)
        self.click(at, 'Executar operação na Splay')
        self.assertTrue(any('ID 99 não encontrado' in i.value for i in at.info))
        self.assertEqual(self.metric(at, 'Nós na Splay do laboratório'), '1')
        self.widget(at, 'number_input', 'ID na Splay').set_value(1)
        self.click(at, 'Executar operação na Splay')
        self.assertTrue(any('ID 1 encontrado' in s.value for s in at.success))
        self.widget(at, 'selectbox', 'Operação da Splay Tree').set_value('Acessar ou inserir').run()
        self.widget(at, 'number_input', 'ID na Splay').set_value(99)
        self.click(at, 'Executar operação na Splay')
        self.assertTrue(any('ID 99 inserido' in s.value for s in at.success))
        self.click(at, 'Executar operação na Splay')
        self.assertTrue(any('ID 99 acessado' in s.value for s in at.success))
        self.widget(at, 'selectbox', 'Operação da Splay Tree').set_value('Remover').run()
        self.click(at, 'Executar operação na Splay')
        self.assertTrue(any('ID 99 removido' in s.value for s in at.success))
        self.widget(at, 'selectbox', 'Operação da Splay Tree').set_value('Limpar').run()
        self.assertFalse(any(w.label == 'ID na Splay' for w in at.number_input))
        self.click(at, 'Executar operação na Splay')
        self.assertEqual(self.metric(at, 'Nós na Splay do laboratório'), '0')

    def test_music_modes_track_changes_and_players(self):
        at = self.page('pages/1_Music_Explorer.py')
        # Fixture audio paths exist; this checks both render_player call sites.
        self.assertEqual(len(at.get('audio')), 1)
        self.widget(at, 'checkbox', 'Comparar com busca exaustiva (Recall@K)').check().run()
        for mode in ['Aproximada experimental', 'Exata certificada']:
            self.widget(at, 'radio', 'Modo de busca').set_value(mode).run()
            self.click(at, 'Encontrar músicas semelhantes')
            self.assertEqual(len(at.get('audio')), 2)
            self.assertEqual(self.metric(at, 'Recall@2 medido'), '100.0%')
            self.assertEqual(len(at.dataframe[0].value), 2)
        self.widget(at, 'selectbox', 'Selecione uma faixa').set_value(3).run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.dataframe), 0)
        self.click(at, 'Encontrar músicas semelhantes')
        self.assertEqual({r.track_id for r in at.session_state['search_snapshot']['results']}, {2, 4})
        self.widget(at, 'selectbox', 'Ouvir uma recomendação').set_value(4).run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.get('audio')), 2)
    def test_benchmark_reader_rejects_unrenderable_files(self):
        from services.benchmarks import read_benchmark
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'benchmark_splay_uniform.csv'
            for contents in ['', 'unexpected\n1\n', 'structure,n,time_ms\n',
                             'structure,n,time_ms\nSplayTree,100,invalid\n',
                             'structure,n,time_ms\nSplayTree,100,inf\n']:
                with self.subTest(contents=contents):
                    path.write_text(contents)
                    with self.assertRaisesRegex(ValueError, 'Execute novamente os benchmarks'):
                        read_benchmark(path)
            path.write_text('structure,n,time_ms,avg_depth\nStdMap,100,0.2,\n')
            data = read_benchmark(path)
            self.assertEqual(data.time_ms.iloc[0], 0.2)
            self.assertTrue(data.avg_depth.isna().all())
    def test_dead_core_recovers_on_rerun(self):
        at = self.page('app.py')
        old = at.session_state['bridge']; old._proc.kill(); old._proc.wait()
        at.run()
        self.assertFalse(at.exception)
        self.assertTrue(at.session_state['bridge'].alive)
        self.assertIsNot(old, at.session_state['bridge'])

if __name__ == '__main__': unittest.main()
