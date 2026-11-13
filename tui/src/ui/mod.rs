mod home;
mod exercise;
mod report;

use ratatui::backend::CrosstermBackend;
use ratatui::Terminal;

use crate::app::{App, Screen};

pub fn init_terminal() -> anyhow::Result<Terminal<CrosstermBackend<std::io::Stdout>>> {
    crossterm::terminal::enable_raw_mode()?;
    let mut stdout = std::io::stdout();
    crossterm::execute!(stdout, crossterm::terminal::EnterAlternateScreen, crossterm::event::EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    Ok(Terminal::new(backend)?)
}

pub fn restore_terminal(terminal: &mut Terminal<CrosstermBackend<std::io::Stdout>>) -> anyhow::Result<()> {
    crossterm::execute!(
        terminal.backend_mut(),
        crossterm::event::DisableMouseCapture,
        crossterm::terminal::LeaveAlternateScreen
    )?;
    crossterm::terminal::disable_raw_mode()?;
    Ok(())
}

pub fn draw(terminal: &mut Terminal<CrosstermBackend<std::io::Stdout>>, app: &App) -> anyhow::Result<()> {
    terminal.draw(|f| match app.screen {
        Screen::Home => home::draw(f, app),
        Screen::Exercise => exercise::draw(f, app),
        Screen::Report => report::draw(f, app),
    })?;
    Ok(())
}
