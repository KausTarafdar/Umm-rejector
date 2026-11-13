//! Microphone capture: cpal -> 16 kHz mono PCM16 via rubato.
//!
//! The blocking stream callback lives in its own thread and mixes all input
//! channels down to mono, resamples to 16 kHz, and appends to a shared
//! PCM16 buffer that the app drains for the WebSocket stream.

use anyhow::{anyhow, Result};
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use rubato::{FftFixedIn, Resampler};
use std::sync::{Arc, Mutex};

/// Target: 16 kHz mono PCM16, matching the daemon's spotter and whisper-server.
pub const TARGET_RATE: u32 = 16000;

/// Resampler input chunk size (samples per channel fed to rubato).
const CHUNK: usize = 1024;

#[derive(Default)]
pub struct Capture {
    shared: Arc<Shared>,
    stream: Option<cpal::Stream>,
}

#[derive(Default)]
struct Shared {
    pcm: Mutex<Vec<i16>>,
}

struct StreamState {
    resampler: FftFixedIn<f32>,
    input: Vec<f32>,
    output: Vec<Vec<f32>>,
    shared: Arc<Shared>,
}

impl StreamState {
    fn new(in_rate: usize, shared: Arc<Shared>) -> Result<Self> {
        Ok(Self {
            resampler: FftFixedIn::<f32>::new(in_rate, TARGET_RATE as usize, CHUNK, 2, 1)?,
            input: Vec::new(),
            output: vec![Vec::new(); 1],
            shared,
        })
    }

    fn push(&mut self, mono: f32) {
        self.input.push(mono);
        while self.input.len() >= CHUNK {
            let chunk: Vec<f32> = self.input.drain(..CHUNK).collect();
            let Ok((_, _)) = self.resampler.process_into_buffer(&[chunk], &mut self.output, None)
            else {
                continue;
            };
            let samples = self.output.first().cloned().unwrap_or_default();
            let mut pcm = self.shared.pcm.lock().unwrap();
            pcm.extend(samples.into_iter().map(clamp_to_i16));
        }
    }
}

impl Capture {
    pub fn new() -> Result<Self> {
        let host = cpal::default_host();
        let device = host
            .default_input_device()
            .ok_or_else(|| anyhow!("no microphone input device found"))?;
        let config = device.default_input_config()?;
        if !matches!(config.sample_format(), cpal::SampleFormat::F32 | cpal::SampleFormat::I16) {
            return Err(anyhow!(
                "unsupported mic sample format: {:?}",
                config.sample_format()
            ));
        }
        Ok(Self {
            shared: Arc::new(Shared::default()),
            stream: None,
        })
    }

    pub fn start(&mut self) -> Result<()> {
        if self.stream.is_some() {
            return Ok(());
        }
        let host = cpal::default_host();
        let device = host
            .default_input_device()
            .ok_or_else(|| anyhow!("no microphone input device found"))?;
        let config = device.default_input_config()?;
        let channels = config.channels() as usize;
        let sample_format = config.sample_format();
        let mut state =
            StreamState::new(config.sample_rate().0 as usize, Arc::clone(&self.shared))?;

        let err_fn = move |e| eprintln!("audio stream error: {e}");
        let stream_config: cpal::StreamConfig = config.clone().into();

        let stream = match sample_format {
            cpal::SampleFormat::F32 => device.build_input_stream(
                &stream_config,
                move |data: &[f32], _| {
                    // data is interleaved frames; mix each frame to one sample
                    for frame in data.chunks(channels) {
                        let mono = frame.iter().sum::<f32>() / frame.len().max(1) as f32;
                        state.push(mono);
                    }
                },
                err_fn,
                None,
            )?,
            cpal::SampleFormat::I16 => device.build_input_stream(
                &stream_config,
                move |data: &[i16], _| {
                    for frame in data.chunks(channels) {
                        let mono = frame.iter().map(|&s| s as f32 / i16::MAX as f32).sum::<f32>()
                            / frame.len().max(1) as f32;
                        state.push(mono);
                    }
                },
                err_fn,
                None,
            )?,
            _ => unreachable!("checked in new()"),
        };
        stream.play()?;
        self.stream = Some(stream);
        Ok(())
    }

    #[allow(dead_code)] // kept for future capture-state UI
    pub fn is_running(&self) -> bool {
        self.stream.is_some()
    }

    pub fn take_pcm(&self) -> Vec<i16> {
        std::mem::take(&mut self.shared.pcm.lock().unwrap())
    }

    pub fn stop(&mut self) -> Vec<i16> {
        self.stream = None;
        self.take_pcm()
    }
}

fn clamp_to_i16(x: f32) -> i16 {
    (x.clamp(-1.0, 1.0) * i16::MAX as f32) as i16
}

/// Encode 16 kHz mono PCM16 as an in-memory WAV buffer.
pub fn encode_wav(pcm: &[i16]) -> Result<Vec<u8>> {
    let spec = hound::WavSpec {
        channels: 1,
        sample_rate: TARGET_RATE,
        bits_per_sample: 16,
        sample_format: hound::SampleFormat::Int,
    };
    let mut cursor = std::io::Cursor::new(Vec::new());
    let mut writer = hound::WavWriter::new(&mut cursor, spec)?;
    for &s in pcm {
        writer.write_sample(s)?;
    }
    writer.finalize()?;
    Ok(cursor.into_inner())
}

/// Raw little-endian PCM16 bytes for the spotter WebSocket path.
pub fn pcm_bytes(pcm: &[i16]) -> Vec<u8> {
    pcm.iter().flat_map(|s| s.to_le_bytes()).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn wav_header_and_samples() {
        let pcm: Vec<i16> = vec![100, -100, 32000, -32000];
        let wav = encode_wav(&pcm).unwrap();
        assert_eq!(wav.len(), 44 + pcm.len() * 2);
        assert_eq!(&wav[0..4], b"RIFF");
        let mut reader = hound::WavReader::new(std::io::Cursor::new(&wav)).unwrap();
        let samples: Vec<i16> = reader.samples().map(|s| s.unwrap()).collect();
        assert_eq!(samples, pcm);
    }
}
