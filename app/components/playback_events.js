// Streamlit v2 calls cleanup before rebinding or unmounting this component.
export default function ({ data, parentElement, setTriggerValue }) {
    const container = parentElement.closest(`.st-key-${data.container_key}`);
    if (!container) return;
    // Persist across Python reruns. The cumulative sequence also preserves
    // multiple play events batched into the same Streamlit rerun.
    if (container.amePlayback?.trackId !== data.track_id) {
        const token = Array.from(crypto.getRandomValues(new Uint32Array(4)), n => n.toString(16)).join("-");
        container.amePlayback = { trackId: data.track_id, token, sequence: 0 };
    }
    const state = container.amePlayback;

    const onPlay = (event) => {
        if (event.target.tagName !== "AUDIO") return;
        setTriggerValue("started", {
            track_id: data.track_id,
            token: state.token,
            sequence: ++state.sequence,
        });
    };
    // Media events do not bubble. Capture also covers a replaced audio element.
    container.addEventListener("play", onPlay, true);
    return () => container.removeEventListener("play", onPlay, true);
}
