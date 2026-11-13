use serde::Deserialize;

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

    // TODO: stop_session(wav_bytes) -> Report
    // TODO: stream PCM chunks over WebSocket /ws/audio
    // TODO: history(), trends(), heatmap()
}
