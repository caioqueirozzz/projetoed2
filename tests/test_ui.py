"""Regressions for visible state, all laboratory operations and page isolation."""
from __future__ import annotations
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
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
        # AppTest owns a distinct component registry per runtime. Reimport the
        # module so its v2 component is registered in this application's runtime.
        sys.modules.pop('components.music', None)
        sys.modules.pop('components.track_card', None)
        at = AppTest.from_file(str(ROOT / 'app/app.py'), default_timeout=30).run()
        if name != 'app.py':
            at.switch_page(name).run()
        self.apps.append(at); self.assertFalse(at.exception)
        return at
    def play(self, at, player='reference', sequence=1, token='test-player', track_id=None,
             player_track_id=None):
        component = next(x.proto for x in at.get('bidi_component')
                         if f'playback_event_{player}_' in x.proto.id
                         and (player_track_id is None or json.loads(x.proto.json)['track_id'] == player_track_id))
        data = json.loads(component.json)
        payload = {'track_id': data['track_id'] if track_id is None else track_id,
                   'token': token, 'sequence': sequence}
        states = at._tree.get_widget_states()
        # Custom components are UnknownElement to AppTest, so include the base
        # widget state that the real frontend sends alongside its trigger.
        for element in at.get('bidi_component'):
            states.widgets.add(id=element.proto.id, json_value='{}')
        trigger = states.widgets.add(id=f'$$STREAMLIT_INTERNAL_KEY_{component.id}__events')
        trigger.json_trigger_value = json.dumps([{'event': 'started', 'value': payload}])
        at._run(states)
        self.assertFalse(at.exception)
    def widget(self, at, kind, label):
        return next(w for w in getattr(at, kind) if w.label == label)
    def click(self, at, label):
        self.widget(at, 'button', label).click().run()
        self.assertFalse(at.exception)
    def metric(self, at, label):
        return self.widget(at, 'metric', label).value
    def player_tracks(self, at, player):
        return [json.loads(x.proto.json)['track_id'] for x in at.get('bidi_component')
                if f'playback_event_{player}_' in x.proto.id]
    def test_music_hides_stale_results_and_measures_recall(self):
        at = self.page('pages/1_Music_Explorer.py')
        self.widget(at, 'checkbox', 'Comparar com busca exaustiva (Recall@K)').check().run()
        self.click(at, 'Encontrar músicas semelhantes')
        self.assertEqual(len(self.player_tracks(at, 'recommendation')), 2)
        self.assertFalse(at.dataframe)
        self.assertEqual(self.metric(at, 'Recall@2 medido'), '100.0%')
        self.widget(at, 'slider', 'Top-K resultados').set_value(1).run()
        self.assertEqual(len(at.dataframe), 0)
        self.assertEqual(self.player_tracks(at, 'recommendation'), [])
        self.assertTrue(any('parâmetros mudaram' in x.value for x in at.info))
        self.click(at, 'Encontrar músicas semelhantes')
        self.assertEqual(len(self.player_tracks(at, 'recommendation')), 1)
    def test_lab_state_updates_immediately_and_is_independent(self):
        at = self.page('pages/3_Structures_Lab.py')
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
        self.assertEqual([title.value for title in at.title], ['Music Explorer'])
        self.assertEqual([p['page_name'] for p in at._registered_pages.values()],
                         ['Music Explorer', 'Playback Profile', 'Structures Lab'])
        self.assertEqual(next(iter(at._registered_pages.values()))['url_pathname'], '')
        self.assertEqual({path.name for path in (ROOT / 'app/pages').glob('*.py')},
                         {'1_Music_Explorer.py', '3_Structures_Lab.py', '2_Playback_Profile.py'})
        at.switch_page('pages/1_Music_Explorer.py').run()
        self.assertFalse(at.exception)
        self.click(at, 'Encontrar músicas semelhantes')
        expected = self.player_tracks(at, 'recommendation')
        self.assertEqual([button.label for button in at.button], ['Encontrar músicas semelhantes'])
        bridge = at.session_state['bridge']
        self.assertEqual(bridge.lab_splay()['size'], 0)

        at.switch_page('pages/3_Structures_Lab.py').run()
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
        self.assertEqual(self.player_tracks(at, 'recommendation'), expected)
        self.assertEqual(bridge.track_count, 3)
    def test_laboratory_runs_without_music_dataset(self):
        missing = self.csv.with_name('not_imported.csv')
        with patch.object(dataset, 'PROCESSED_CSV', missing), \
             patch.object(core_bridge, 'CSV', missing), \
             patch.object(core_bridge, 'CoreBridge', lambda: self.bridge_type(CORE, missing)):
            at = self.page('app.py')
            self.assertFalse(at.session_state['bridge'].is_loaded)
            at.switch_page('pages/3_Structures_Lab.py').run()
            self.assertFalse(at.exception)
            self.click(at, 'Executar operação na Skip List')
            self.click(at, 'Executar operação na Splay')
            self.assertEqual(self.metric(at, 'Nós na Skip List do laboratório'), '1')
            self.assertEqual(self.metric(at, 'Nós na Splay do laboratório'), '1')
            at.switch_page('pages/1_Music_Explorer.py').run()
            self.assertFalse(at.exception)
            self.assertTrue(any('Importe o FMA' in warning.value for warning in at.warning))
    def test_skip_operations_validate_only_their_required_fields(self):
        at = self.page('pages/3_Structures_Lab.py')
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
        at = self.page('pages/3_Structures_Lab.py')
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
        at = self.page('pages/3_Structures_Lab.py')
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
            self.assertEqual(len(at.get('audio')), 3)
            self.assertEqual(self.metric(at, 'Recall@2 medido'), '100.0%')
            self.assertFalse(at.dataframe)
            self.assertEqual(self.player_tracks(at, 'recommendation'),
                             [r.track_id for r in at.session_state['search_snapshot']['results']])
        self.widget(at, 'selectbox', 'Selecione uma faixa').set_value(3).run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.dataframe), 0)
        self.click(at, 'Encontrar músicas semelhantes')
        self.assertEqual({r.track_id for r in at.session_state['search_snapshot']['results']}, {2, 4})
        self.play(at, player='recommendation', player_track_id=4, token='card-4')
        self.assertFalse(at.exception)
        self.assertEqual(len(at.get('audio')), 3)
        self.assertEqual(at.session_state['bridge'].playback_history()['entries'][0]['track_id'], 4)
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
        self.play(at)
        old = at.session_state['bridge']; old._proc.kill(); old._proc.wait()
        self.play(at, sequence=2)
        self.assertFalse(at.exception)
        self.assertTrue(at.session_state['bridge'].alive)
        self.assertIsNot(old, at.session_state['bridge'])
        self.assertEqual(at.session_state['bridge'].playback_history()['total_plays'], 1)
        at.run()
        self.play(at, sequence=2)
        self.assertEqual(at.session_state['bridge'].playback_history()['total_plays'], 1)
        self.play(at, sequence=3)
        self.assertEqual(at.session_state['bridge'].playback_history()['total_plays'], 2)

    def test_playback_counts_only_player_starts_without_rerun_duplicates(self):
        at = self.page('pages/1_Music_Explorer.py')
        bridge = at.session_state['bridge']
        self.assertEqual(bridge.playback_history()['total_plays'], 0)
        self.widget(at, 'selectbox', 'Selecione uma faixa').set_value(3).run()
        self.click(at, 'Encontrar músicas semelhantes')
        self.assertEqual(bridge.playback_history()['total_plays'], 0)
        self.play(at)
        self.assertEqual(bridge.playback_history()['entries'],
                         [{'track_id': 3, 'play_count': 1, 'last_play_order': 1}])
        at.run()
        self.play(at)  # A redelivered event must not count again.
        self.assertEqual(bridge.playback_history()['total_plays'], 1)
        self.play(at, sequence=2)  # Pause/resume is a second start.
        self.assertEqual(bridge.playback_history()['total_plays'], 2)
        self.play(at, sequence=4)  # Two rapid starts may share a rerun.
        self.assertEqual(bridge.playback_history()['total_plays'], 4)
        self.play(at, sequence=5, track_id=4)  # Stale/wrong player event.
        self.assertEqual(bridge.playback_history()['total_plays'], 4)
        self.play(at, player='recommendation', token='recommendation')
        self.assertEqual(bridge.playback_history()['total_plays'], 5)
        self.assertEqual(bridge.playback_history()['size'], 2)
        self.assertEqual(bridge.lab_splay()['size'], 0)
        at.switch_page('pages/2_Playback_Profile.py').run()
        self.assertFalse(at.exception)
        self.assertEqual(self.metric(at, 'Reproduções na sessão'), '5')
        self.assertEqual(bridge.playback_history()['root_id'], 2)
        self.assertEqual(len(at.get('audio')), 2)
        self.assertFalse(at.dataframe)
        self.widget(at, 'selectbox', 'Buscar no histórico por título, artista ou ID').set_value(3).run()
        self.assertFalse(at.exception)
        self.assertEqual(bridge.playback_history()['root_id'], 3)
        self.assertEqual(bridge.playback_history()['entries'][0]['track_id'], 2)
        self.assertEqual(self.metric(at, 'Reproduções na sessão'), '5')
        self.assertEqual(len(at.get('audio')), 1)
        self.widget(at, 'selectbox', 'Buscar no histórico por título, artista ou ID').set_value(None).run()
        def visible_tracks():
            return [json.loads(x.proto.json)['track_id'] for x in at.get('bidi_component')]
        self.assertEqual(visible_tracks(), [2, 3])
        self.play(at, player='history', token='history', player_track_id=3)
        self.assertEqual(bridge.playback_history()['total_plays'], 6)
        self.assertEqual(bridge.playback_history()['entries'][0]['track_id'], 3)
        self.assertEqual(self.metric(at, 'Reproduções na sessão'), '5')
        self.assertEqual(visible_tracks(), [2, 3])
        self.assertTrue(any('4 reproduções' in caption.value for caption in at.caption))
        at.run()
        self.assertEqual(self.metric(at, 'Reproduções na sessão'), '5')
        self.assertEqual(visible_tracks(), [2, 3])
        self.click(at, 'Atualizar')
        self.assertEqual(self.metric(at, 'Reproduções na sessão'), '6')
        self.assertEqual(visible_tracks(), [3, 2])
        self.assertTrue(any('5 reproduções' in caption.value for caption in at.caption))
        self.play(at, player='history', token='other-history', player_track_id=2)
        self.assertEqual(self.metric(at, 'Reproduções na sessão'), '6')
        self.assertEqual(visible_tracks(), [3, 2])
        at.switch_page('pages/3_Structures_Lab.py').run()
        at.switch_page('pages/2_Playback_Profile.py').run()
        self.assertFalse(at.exception)
        self.assertEqual(self.metric(at, 'Reproduções na sessão'), '7')
        self.assertEqual(visible_tracks(), [2, 3])

    def test_history_empty_new_session_and_invalid_tracks(self):
        at = self.page('pages/2_Playback_Profile.py')
        self.assertTrue(any('histórico está vazio' in info.value for info in at.info))
        bridge = at.session_state['bridge']
        for tid in [0, -1, 999]:
            with self.assertRaises(RuntimeError):
                bridge.record_play(tid)
        self.assertFalse(bridge.search_history(2)['found'])
        self.assertEqual(bridge.playback_history()['size'], 0)
        bridge.record_play(2)
        fresh = self.page('pages/2_Playback_Profile.py')
        self.assertEqual(fresh.session_state['bridge'].playback_history()['total_plays'], 0)
        at.run()
        self.assertFalse(at.exception)
        self.assertTrue(any('histórico está vazio' in info.value for info in at.info))
        self.click(at, 'Atualizar')
        self.assertEqual(self.metric(at, 'Reproduções na sessão'), '1')

    def test_history_shows_ten_unique_tracks_and_expands_without_refreshing(self):
        # A larger catalogue exercises the 10/11 boundary using the actual core.
        frame = pd.read_csv(self.csv)
        extra = pd.concat([frame.iloc[[0]].copy() for _ in range(9)], ignore_index=True)
        extra['track_id'] = range(10, 19)
        frame = pd.concat([frame, extra], ignore_index=True)
        larger_csv = self.csv.with_name('history_catalog.csv')
        frame.to_csv(larger_csv, index=False)
        with patch.object(dataset, 'PROCESSED_CSV', larger_csv), \
             patch.object(core_bridge, 'CSV', larger_csv), \
             patch.object(core_bridge, 'CoreBridge', lambda: self.bridge_type(CORE, larger_csv)):
            at = self.page('app.py')
            bridge = at.session_state['bridge']
            ids = frame.track_id.astype(int).tolist()
            for track_id in ids[:10]:
                bridge.record_play(track_id)
            for _ in range(5):
                bridge.record_play(ids[9])
            at.switch_page('pages/2_Playback_Profile.py').run()
            self.assertFalse(at.exception)
            self.assertEqual(len(self.player_tracks(at, 'history')), 10)
            self.assertFalse(any(b.label == 'Ver histórico completo' for b in at.button))
            for track_id in ids[10:]:
                bridge.record_play(track_id)
            at.run()
            self.assertFalse(any(b.label == 'Ver histórico completo' for b in at.button))
            self.click(at, 'Atualizar')
            self.assertEqual(self.player_tracks(at, 'history'), list(reversed(ids))[:10])
            total = bridge.playback_history()['total_plays']
            self.widget(at, 'selectbox', 'Buscar no histórico por título, artista ou ID').set_value(ids[0]).run()
            self.assertEqual(self.player_tracks(at, 'history'), [ids[0]])
            self.assertEqual(bridge.playback_history()['root_id'], ids[0])
            self.widget(at, 'selectbox', 'Buscar no histórico por título, artista ou ID').set_value(None).run()
            self.click(at, 'Ver histórico completo')
            self.assertEqual(self.player_tracks(at, 'history'), list(reversed(ids)))
            self.assertEqual(bridge.playback_history()['total_plays'], total)
            self.play(at, player='history', player_track_id=ids[0], token='expanded-history')
            self.assertEqual(self.player_tracks(at, 'history'), list(reversed(ids)))
            self.assertEqual(self.metric(at, 'Reproduções na sessão'), str(total))
            self.click(at, 'Ver menos')
            self.assertEqual(self.player_tracks(at, 'history'), list(reversed(ids))[:10])
            self.click(at, 'Ver histórico completo')
            at.switch_page('pages/1_Music_Explorer.py').run()
            at.switch_page('pages/2_Playback_Profile.py').run()
            self.assertFalse(at.exception)
            self.assertEqual(len(self.player_tracks(at, 'history')), 10)
            self.assertEqual(self.player_tracks(at, 'history')[0], ids[0])
            self.assertEqual(self.metric(at, 'Reproduções na sessão'), str(total + 1))

if __name__ == '__main__': unittest.main()
