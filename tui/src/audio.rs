//! Microphone capture: cpal -> 16 kHz mono PCM16 chunks via rubato.
//!
//! Blocking capture runs on its own thread; the TUI polls the latest
//! buffer for display and accumulates WAV bytes for the stop request.

pub struct Capture {
    // TODO: cpal stream handle, rubato resampler, accumulated PCM buffer,
    // live spotter event channel from the daemon.
}

impl Capture {
    pub fn new() -> anyhow::Result<Self> {
        // TODO: pick default input device, negotiate 16 kHz mono fallback
        // with resampling, spawn capture thread.
        Ok(Self {})
    }

    pub fn start(&mut self) -> anyhow::Result<()> {
        // TODO
        Ok(())
    }

    pub fn stop(&mut self) -> anyhow::Result<Vec<u8>> {
        // TODO: return assembled WAV bytes (16 kHz mono PCM16).
        Ok(Vec::new())
    }
}
