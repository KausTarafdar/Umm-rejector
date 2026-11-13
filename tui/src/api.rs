use serde::Deserialize;
use serde_json::Value;
use std::sync::mpsc::Sender;

/// HTTP client for the Python orchestrator daemon on 127.0.0.1:8123.
/// This is the only module allowed to import reqwest.
pub struct DaemonClient {
    http: reqwest::Client,
    base: String,
}

#[derive(Debug, Deserialize)]
pub struct SessionStart {
    pub session_id: String,
    pub question: String,
    pub duration_secs: u32,
}

#[allow(dead_code)] // timestamp/score fields power future report views
#[derive(Debug, Deserialize)]
pub struct FillerEvent {
    pub label: String,
    pub t_start: f64,
    pub t_end: f64,
    pub score: f64,
}

#[allow(dead_code)] // report shape mirrors the daemon JSON for future views
#[derive(Debug, Deserialize)]
pub struct Report {
    pub duration_secs: f64,
    pub fillers_per_minute: f64,
    pub words_per_minute: f64,
    pub filler_count: usize,
    pub filler_breakdown: std::collections::HashMap<String, u32>,
    pub filler_events: Vec<FillerEvent>,
    pub transcript: String,
}

#[derive(Debug, Deserialize)]
pub struct SessionStop {
    pub report: Report,
    pub question: String,
}

/// Live spotter messages pushed by the daemon over the audio WebSocket.
pub enum LiveMessage {
    FillerUpdate(Vec<FillerEvent>),
}

impl DaemonClient {
    pub fn new() -> Self {
        Self {
            http: reqwest::Client::new(),
            base: "http://127.0.0.1:8123".to_string(),
        }
    }

    pub async fn health(&self) -> anyhow::Result<()> {
        self.http.get(format!("{}/health", self.base)).send().await?.error_for_status()?;
        Ok(())
    }

    pub async fn start_session(&self) -> anyhow::Result<SessionStart> {
        let res = self
            .http
            .post(format!("{}/session/start", self.base))
            .send()
            .await?
            .error_for_status()?
            .json()
            .await?;
        Ok(res)
    }

    pub async fn stop_session(&self, session_id: &str, wav: Vec<u8>) -> anyhow::Result<SessionStop> {
        let res = self
            .http
            .post(format!("{}/session/{}/stop", self.base, session_id))
            .header("content-type", "audio/wav")
            .body(wav)
            .send()
            .await?
            .error_for_status()?
            .json()
            .await?;
        Ok(res)
    }

    // TODO: history(), trends(), heatmap()
}

/// WebSocket URL for streaming raw PCM16 chunks to the daemon.
pub fn ws_url(session_id: &str) -> String {
    format!("ws://127.0.0.1:8123/ws/audio?session_id={}", session_id)
}

/// Stream PCM16 chunks to the daemon and receive live spotter updates.
/// Runs until the sender is dropped (session ends).
pub async fn stream_audio(
    session_id: String,
    mut chunk_rx: tokio::sync::mpsc::UnboundedReceiver<Vec<u8>>,
    live_tx: Sender<LiveMessage>,
) -> anyhow::Result<()> {
    use futures_util::{SinkExt, StreamExt};
    use tokio_tungstenite::tungstenite::Message;

    let (mut ws, _) = tokio_tungstenite::connect_async(ws_url(&session_id)).await?;
    loop {
        tokio::select! {
            chunk = chunk_rx.recv() => {
                match chunk {
                    Some(bytes) => {
                        if ws.send(Message::Binary(bytes)).await.is_err() {
                            break;
                        }
                    }
                    None => {
                        // Session over: tell the daemon we are done streaming.
                        let _ = ws.send(Message::Close(None)).await;
                        break;
                    }
                }
            }
            msg = ws.next() => {
                match msg {
                    Some(Ok(Message::Text(text))) => {
                        if let Ok(Value::Object(obj)) = serde_json::from_str::<Value>(&text) {
                            if obj.get("type").and_then(|t| t.as_str()) == Some("filler_update") {
                                if let Ok(events) =
                                    serde_json::from_value::<Vec<FillerEvent>>(
                                        obj.get("events").cloned().unwrap_or_default(),
                                    )
                                {
                                    let _ = live_tx.send(LiveMessage::FillerUpdate(events));
                                }
                            }
                        }
                    }
                    Some(Ok(Message::Close(_))) | None => break,
                    Some(Ok(_)) => {}
                    Some(Err(_)) => break,
                }
            }
        }
    }
    Ok(())
}
