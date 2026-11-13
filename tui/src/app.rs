use anyhow::Result;
use crossterm::event::{self, Event, KeyCode, KeyEventKind};
use ratatui::backend::CrosstermBackend;
use ratatui::Terminal;
use std::time::Duration;

use crate::api::DaemonClient;
use crate::ui;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Screen {
    Home,
    Exercise,
    Report,
}

pub struct App {
    pub screen: Screen,
    pub daemon: DaemonClient,
    pub daemon_online: bool,
    pub question: Option<String>,
    pub filler_count: u32,
    pub recording: bool,
    pub quit: bool,
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
            quit: false,
        }
    }

    pub async fn poll_daemon(&mut self) {
        self.daemon_online = self.daemon.health().await.is_ok();
    }

    pub async fn on_key(&mut self, key: KeyCode) {
        match self.screen {
            Screen::Home => match key {
                KeyCode::Char('q') => self.quit = true,
                KeyCode::Enter => self.start_session().await,
                _ => {}
            },
            Screen::Exercise => match key {
                KeyCode::Esc => self.stop_session().await,
                _ => {}
            },
            Screen::Report => match key {
                KeyCode::Esc | KeyCode::Enter => {
                    self.screen = Screen::Home;
                    self.question = None;
                    self.filler_count = 0;
                }
                _ => {}
            },
        }
    }

    async fn start_session(&mut self) {
        // TODO: begin audio capture and stream chunks to the daemon,
        // then fetch the drawn question from /session/start.
        if let Ok(session) = self.daemon.start_session().await {
            self.question = Some(session.question);
            self.filler_count = 0;
            self.recording = true;
            self.screen = Screen::Exercise;
        }
    }

    async fn stop_session(&mut self) {
        self.recording = false;
        // TODO: stop capture, POST accumulated WAV, fetch report.
        self.screen = Screen::Report;
    }
}

pub async fn run(terminal: &mut Terminal<CrosstermBackend<std::io::Stdout>>) -> Result<()> {
    let mut app = App::new();
    app.poll_daemon().await;

    while !app.quit {
        ui::draw(terminal, &app)?;
        if event::poll(Duration::from_millis(100)) {
            if let Event::Key(key) = event::read()? {
                if key.kind == KeyEventKind::Press {
                    app.on_key(key.code).await;
                }
            }
        }
        app.poll_daemon().await;
    }
    Ok(())
}
