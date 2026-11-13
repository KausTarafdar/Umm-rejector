use anyhow::Result;
use crossterm::event::{self, Event, KeyCode, KeyEventKind};
use ratatui::backend::CrosstermBackend;
use ratatui::Terminal;
use std::sync::mpsc::Receiver;
use std::time::{Duration, Instant};

use crate::api::{DaemonClient, LiveMessage, Report, SessionStop};
use crate::audio::{pcm_bytes, Capture};
use crate::ui;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Screen {
    Home,
    Exercise,
    Report,
}

struct LiveSession {
    session_id: String,
    duration_secs: u32,
    started_at: Instant,
    capture: Capture,
    chunk_tx: tokio::sync::mpsc::UnboundedSender<Vec<u8>>,
    live_rx: Receiver<LiveMessage>,
}

pub struct App {
    pub screen: Screen,
    pub daemon: DaemonClient,
    pub daemon_online: bool,
    pub question: Option<String>,
    pub filler_count: usize,
    pub recording: bool,
    pub elapsed_secs: u32,
    pub report: Option<(String, Report)>,
    pub error: Option<String>,
    pub quit: bool,
    live: Option<LiveSession>,
}

impl App {
    pub fn new() -> Self {
        Self {
            screen: Screen::Home,
            daemon: DaemonClient::new(),
            daemon_online: false,
            question: None,
            filler_count: 0,
            recording: false,
            elapsed_secs: 0,
            report: None,
            error: None,
            quit: false,
            live: None,
        }
    }

    pub async fn poll_daemon(&mut self) {
        self.daemon_online = self.daemon.health().await.is_ok();
    }

    pub async fn on_key(&mut self, key: KeyCode) {
        self.error = None;
        match self.screen {
            Screen::Home => match key {
                KeyCode::Char('q') => self.quit = true,
                KeyCode::Enter => self.start_session().await,
                _ => {}
            },
            Screen::Exercise => {
                if key == KeyCode::Esc {
                    self.stop_session().await;
                }
            }
            Screen::Report => match key {
                KeyCode::Esc | KeyCode::Enter => {
                    self.screen = Screen::Home;
                    self.report = None;
                }
                _ => {}
            },
        }
    }

    async fn start_session(&mut self) {
        match self.daemon.start_session().await {
            Ok(session) => {
                let mut capture = match Capture::new() {
                    Ok(capture) => capture,
                    Err(e) => {
                        self.error = Some(e.to_string());
                        return;
                    }
                };
                if let Err(e) = capture.start() {
                    self.error = Some(e.to_string());
                    return;
                }
                let (chunk_tx, chunk_rx) = tokio::sync::mpsc::unbounded_channel();
                let (live_tx, live_rx) = std::sync::mpsc::channel::<LiveMessage>();
                let session_id = session.session_id.clone();
                tokio::spawn(crate::api::stream_audio(
                    session_id.clone(),
                    chunk_rx,
                    live_tx,
                ));
                self.live = Some(LiveSession {
                    session_id,
                    duration_secs: session.duration_secs,
                    started_at: Instant::now(),
                    capture,
                    chunk_tx,
                    live_rx,
                });
                self.question = Some(session.question);
                self.filler_count = 0;
                self.elapsed_secs = 0;
                self.recording = true;
                self.screen = Screen::Exercise;
            }
            Err(e) => self.error = Some(e.to_string()),
        }
    }

    async fn stop_session(&mut self) {
        let mut live = match self.live.take() {
            Some(l) => l,
            None => {
                self.screen = Screen::Home;
                return;
            }
        };
        drop(live.chunk_tx); // signals stream_audio to close the WebSocket
        let pcm = live.capture.stop();
        self.recording = false;
        match crate::audio::encode_wav(&pcm) {
            Ok(wav) => match self.daemon.stop_session(&live.session_id, wav).await {
                Ok(SessionStop { report, question }) => {
                    self.report = Some((question, report));
                    self.screen = Screen::Report;
                }
                Err(e) => {
                    self.error = Some(e.to_string());
                    self.screen = Screen::Home;
                }
            },
            Err(e) => {
                self.error = Some(e.to_string());
                self.screen = Screen::Home;
            }
        }
    }

    /// Feed captured audio to the WS task, consume live spotter updates,
    /// and end the session automatically when the timer runs out.
    async fn tick(&mut self) {
        if let Some(live) = &mut self.live {
            let pcm = live.capture.take_pcm();
            if !pcm.is_empty() {
                let _ = live.chunk_tx.send(pcm_bytes(&pcm));
            }
            self.elapsed_secs = live.started_at.elapsed().as_secs() as u32;
            while let Ok(msg) = live.live_rx.try_recv() {
                match msg {
                    LiveMessage::FillerUpdate(events) => self.filler_count = events.len(),
                }
            }
            if self.elapsed_secs >= live.duration_secs {
                self.stop_session().await;
            }
        }
    }
}

pub async fn run(terminal: &mut Terminal<CrosstermBackend<std::io::Stdout>>) -> Result<()> {
    let mut app = App::new();
    app.poll_daemon().await;

    while !app.quit {
        app.tick().await;
        ui::draw(terminal, &app)?;
        if event::poll(Duration::from_millis(100))? {
            if let Event::Key(key) = event::read()? {
                if key.kind == KeyEventKind::Press {
                    app.on_key(key.code).await;
                }
            }
        }
        if app.screen == Screen::Home {
            app.poll_daemon().await;
        }
    }
    Ok(())
}
