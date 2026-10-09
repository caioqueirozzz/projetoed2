import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../app/components/playback_events.js", import.meta.url), "utf8");
const { default: mount } = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);

function player(trackId) {
    const listeners = new Set();
    const events = [];
    const container = {
        addEventListener(name, fn, capture) {
            assert.equal(name, "play");
            assert.equal(capture, true, "Audio play events require capture");
            listeners.add(fn);
        },
        removeEventListener(name, fn, capture) {
            assert.equal(name, "play");
            assert.equal(capture, true);
            listeners.delete(fn);
        },
    };
    const component = {
        data: { track_id: trackId, container_key: `playback_player_test_${trackId}` },
        parentElement: {
            closest(selector) {
                assert.equal(selector, `.st-key-playback_player_test_${trackId}`);
                return container;
            },
        },
        setTriggerValue(name, value) { events.push({ name, value }); },
    };
    return {
        events,
        mount: () => mount(component),
        start: (tagName = "AUDIO") => listeners.forEach(fn => fn({ target: { tagName } })),
    };
}

test("mounting does not count; every audio start counts immediately", () => {
    const p = player(2);
    p.mount();
    assert.equal(p.events.length, 0);
    p.start("VIDEO");
    assert.equal(p.events.length, 0);
    p.start();
    p.start();
    assert.deepEqual(p.events.map(e => [e.name, e.value.track_id, e.value.sequence]),
        [["started", 2, 1], ["started", 2, 2]]);
    assert.equal(p.events[0].value.token, p.events[1].value.token);
});

test("rerender cleanup prevents duplicate listeners and preserves sequence", () => {
    const p = player(3);
    let cleanup = p.mount();
    p.start();
    cleanup();
    p.start();
    assert.equal(p.events.length, 1);
    cleanup = p.mount();
    assert.equal(p.events.length, 1);
    p.start();
    assert.equal(p.events.length, 2);
    assert.equal(p.events[1].value.sequence, 2);
    assert.equal(p.events[0].value.token, p.events[1].value.token);
    cleanup();
});

test("reference and recommendation players keep independent identities", () => {
    const reference = player(2), recommendation = player(4);
    reference.mount();
    recommendation.mount();
    recommendation.start();
    assert.equal(reference.events.length, 0);
    reference.start();
    assert.equal(reference.events[0].value.track_id, 2);
    assert.equal(recommendation.events[0].value.track_id, 4);
    assert.notEqual(reference.events[0].value.token, recommendation.events[0].value.token);
});
