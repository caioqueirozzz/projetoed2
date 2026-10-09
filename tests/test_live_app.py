"""Opt-in integration tests against the actual running Streamlit server.

AME_LIVE_URL=http://127.0.0.1:8501 python -m unittest discover -s tests -p test_live_app.py -v
Unlike HTTP health checks, these tests execute page scripts over the Streamlit
protocol and fail on exceptions, including stale imported Python components.
"""
from __future__ import annotations
import asyncio
import json
import os
import unittest
from urllib.parse import urljoin
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.websocket import websocket_connect
from streamlit.proto.BackMsg_pb2 import BackMsg
from streamlit.proto.ForwardMsg_pb2 import ForwardMsg
from streamlit.proto.WidgetStates_pb2 import WidgetState

LIVE_URL = os.environ.get('AME_LIVE_URL', '').rstrip('/')

@unittest.skipUnless(LIVE_URL, 'Set AME_LIVE_URL to test the running server')
class LiveApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        socket_url = LIVE_URL.replace('http://', 'ws://', 1).replace('https://', 'wss://', 1)
        self.socket = await websocket_connect(
            HTTPRequest(socket_url + '/_stcore/stream', headers={'Origin': LIVE_URL}, connect_timeout=10),
            subprotocols=['streamlit'])
        self.addAsyncCleanup(self.close_socket)
        self.widgets = {}
        self.elements = []
        self.pages = []
        self.page = ''

    async def close_socket(self):
        self.socket.close()

    def element(self, kind, label):
        return next(getattr(e, kind) for e in self.elements
                    if e.WhichOneof('type') == kind and getattr(e, kind).label == label)

    def set_value(self, kind, label, value):
        proto = self.element(kind, label)
        state = self.widgets[proto.id]
        if kind in ('radio', 'selectbox', 'text_input'):
            state.string_value = value
        elif kind == 'checkbox':
            state.bool_value = value
        elif kind == 'slider':
            state.double_array_value.data[:] = [value]
        elif kind == 'number_input':
            if proto.data_type == 0:
                state.int_value = int(value)
            else:
                state.double_value = value
        elif kind == 'button':
            state.trigger_value = value
        else:
            raise ValueError(kind)

    def metric(self, label):
        return self.element('metric', label).body

    async def click(self, label):
        self.set_value('button', label, True)
        await self.run_page()

    async def run_page(self, page=None):
        if page is not None and page != self.page:
            self.page = page
            self.widgets.clear()
        request = BackMsg()
        request.rerun_script.page_name = self.page
        request.rerun_script.widget_states.widgets.extend(self.widgets.values())
        await self.socket.write_message(request.SerializeToString(), binary=True)
        self.elements = []
        async with asyncio.timeout(60):
            while True:
                raw = await self.socket.read_message()
                self.assertIsNotNone(raw, 'Server disconnected before finishing the page')
                msg = ForwardMsg.FromString(raw)
                kind = msg.WhichOneof('type')
                if kind == 'navigation':
                    self.pages = list(msg.navigation.app_pages)
                if kind == 'page_not_found':
                    self.fail(f'Page not found: {self.page}')
                if kind == 'delta' and msg.delta.HasField('new_element'):
                    element = msg.delta.new_element
                    if element.HasField('exception'):
                        self.fail(f'{self.page}: {element.exception.type}: {element.exception.message}')
                    self.elements.append(element)
                if kind == 'script_finished':
                    if msg.script_finished == ForwardMsg.FINISHED_EARLY_FOR_RERUN:
                        self.elements = []
                        continue
                    break
        previous_widgets = self.widgets
        self.widgets = {}
        for element in self.elements:
            kind = element.WhichOneof('type')
            if kind == 'bidi_component':
                self.widgets[element.bidi_component.id] = WidgetState(
                    id=element.bidi_component.id, json_value='{}')
                continue
            if kind not in {'selectbox', 'radio', 'text_input', 'checkbox', 'slider', 'number_input', 'button'}:
                continue
            proto = getattr(element, kind)
            if proto.id in previous_widgets:
                self.widgets[proto.id] = previous_widgets[proto.id]
                if kind == 'button':
                    self.widgets[proto.id].trigger_value = False
                continue
            state = WidgetState(id=proto.id)
            if kind in ('selectbox', 'radio') and proto.options:
                state.string_value = proto.options[proto.default]
            elif kind == 'text_input':
                state.string_value = proto.default
            elif kind == 'checkbox':
                state.bool_value = proto.default
            elif kind == 'slider':
                state.double_array_value.data[:] = proto.default
            elif kind == 'number_input':
                if proto.data_type == 0:
                    state.int_value = int(proto.default)
                else:
                    state.double_value = proto.default
            elif kind == 'button':
                state.trigger_value = False
            self.widgets[proto.id] = state

    async def test_music_search_modes_recommendations_and_served_audio(self):
        await self.run_page('')
        self.assertEqual([page.page_name for page in self.pages],
                         ['Music Explorer', 'Playback Profile', 'Structures Lab'])
        self.assertTrue(self.pages[0].is_default)
        self.assertEqual(self.pages[0].url_pathname, '')
        self.assertTrue(any(e.HasField('heading') and e.heading.body == 'Music Explorer' for e in self.elements))
        self.assertEqual(sum(e.HasField('audio') for e in self.elements), 1)
        self.set_value('checkbox', 'Comparar com busca exaustiva (Recall@K)', True)
        await self.click('Encontrar músicas semelhantes')
        k = min(10, int(self.metric('Faixas no índice')) - 1)
        self.assertEqual(self.metric(f'Recall@{k} medido'), '100.0%')
        self.assertEqual(sum(e.HasField('audio') for e in self.elements), k + 1)
        self.assertFalse(any(e.HasField('dataframe') for e in self.elements))
        self.assertEqual(sum(e.HasField('markdown') and 'Distância:' in e.markdown.body for e in self.elements), k)
        for element in self.elements:
            if element.HasField('audio'):
                response = await AsyncHTTPClient().fetch(HTTPRequest(
                    urljoin(LIVE_URL + '/', element.audio.url), headers={'Range': 'bytes=0-1023'}))
                self.assertIn(response.code, (200, 206))
                self.assertGreater(len(response.body), 0)
                self.assertTrue(response.headers['Content-Type'].startswith('audio/'))
        self.set_value('slider', 'Top-K resultados', 1)
        self.set_value('radio', 'Modo de busca', 'Aproximada experimental')
        await self.click('Encontrar músicas semelhantes')
        self.assertEqual(sum(e.HasField('audio') for e in self.elements), 2)
        choices = self.element('selectbox', 'Selecione uma faixa').options
        self.set_value('selectbox', 'Selecione uma faixa', choices[1])
        self.set_value('radio', 'Modo de busca', 'Exata certificada')
        await self.click('Encontrar músicas semelhantes')
        self.assertEqual(self.metric('Recall@1 medido'), '100.0%')

    async def test_playback_events_update_the_session_profile(self):
        await self.run_page('Playback_Profile')
        self.assertTrue(any(e.HasField('alert') and 'histórico está vazio' in e.alert.body
                            for e in self.elements))
        await self.run_page('')
        component = next(e.bidi_component for e in self.elements if e.HasField('bidi_component'))
        track_id = json.loads(component.json)['track_id']
        trigger_id = f'$$STREAMLIT_INTERNAL_KEY_{component.id}__events'
        self.widgets[trigger_id] = WidgetState(
            id=trigger_id,
            json_trigger_value=json.dumps([{'event': 'started', 'value': {
                'track_id': track_id, 'token': 'live-player', 'sequence': 1}}]))
        await self.run_page()
        await self.run_page('Playback_Profile')
        self.assertEqual(self.metric('Músicas no histórico'), '1')
        self.assertEqual(self.metric('Reproduções na sessão'), '1')
        self.assertEqual(sum(e.HasField('audio') for e in self.elements), 1)
        self.assertFalse(any(e.HasField('dataframe') for e in self.elements))
        selector = self.element('selectbox', 'Buscar no histórico por título, artista ou ID')
        self.assertEqual(len(selector.options), 1)
        self.set_value('selectbox', selector.label, selector.options[0])
        await self.run_page()
        self.assertEqual(self.metric('Reproduções na sessão'), '1')
        self.assertEqual(sum(e.HasField('audio') for e in self.elements), 1)
        component = next(e.bidi_component for e in self.elements if e.HasField('bidi_component'))
        trigger_id = f'$$STREAMLIT_INTERNAL_KEY_{component.id}__events'
        self.widgets[trigger_id] = WidgetState(
            id=trigger_id,
            json_trigger_value=json.dumps([{'event': 'started', 'value': {
                'track_id': track_id, 'token': 'live-history', 'sequence': 1}}]))
        await self.run_page()
        self.assertEqual(self.metric('Reproduções na sessão'), '1')
        await self.run_page()
        self.assertEqual(self.metric('Reproduções na sessão'), '1')
        await self.click('Atualizar')
        self.assertEqual(self.metric('Reproduções na sessão'), '2')
        await self.run_page('')
        await self.run_page('Playback_Profile')
        self.assertEqual(self.metric('Reproduções na sessão'), '2')

    async def test_laboratory_operations_and_benchmark_tables(self):
        await self.run_page('Structures_Lab')
        await self.click('Executar operação na Skip List')
        self.assertEqual(self.metric('Nós na Skip List do laboratório'), '1')
        self.set_value('selectbox', 'Operação da Skip List', 'Buscar')
        await self.run_page()
        self.assertFalse(any(e.HasField('number_input') and e.number_input.label == 'ID do nó' for e in self.elements))
        self.set_value('text_input', 'Chave inteira sem sinal', '10')
        await self.click('Executar operação na Skip List')
        self.assertTrue(any(e.HasField('alert') and '1 nó(s) encontrado(s)' in e.alert.body for e in self.elements))
        self.set_value('selectbox', 'Operação da Skip List', 'Atualizar chave')
        await self.run_page()
        self.set_value('text_input', 'Nova chave (atualização)', '20')
        await self.click('Executar operação na Skip List')
        self.set_value('selectbox', 'Operação da Skip List', 'Remover')
        await self.run_page()
        await self.click('Executar operação na Skip List')
        self.assertEqual(self.metric('Nós na Skip List do laboratório'), '0')
        for node in range(1, 5):
            self.set_value('number_input', 'ID na Splay', node)
            await self.click('Executar operação na Splay')
            self.assertEqual(self.metric('Raiz atual do laboratório'), str(node))
        self.set_value('selectbox', 'Operação da Splay Tree', 'Buscar')
        await self.run_page()
        self.set_value('number_input', 'ID na Splay', 1)
        await self.click('Executar operação na Splay')
        self.assertEqual(self.metric('Rotações'), '3')
        self.set_value('selectbox', 'Operação da Splay Tree', 'Limpar')
        await self.run_page()
        self.assertFalse(any(e.HasField('number_input') and e.number_input.label == 'ID na Splay' for e in self.elements))
        await self.click('Executar operação na Splay')
        self.assertEqual(self.metric('Nós na Splay do laboratório'), '0')
        self.assertEqual(sum(e.HasField('download_button') for e in self.elements), 4)

if __name__ == '__main__':
    unittest.main()
