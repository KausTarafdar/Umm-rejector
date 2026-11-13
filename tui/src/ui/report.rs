use ratatui::Frame;
use ratatui::layout::{Constraint, Layout};
use ratatui::style::{Modifier, Style};
use ratatui::widgets::{Block, Borders, Paragraph};

use crate::app::App;

pub fn draw(f: &mut Frame, app: &App) {
    let [body_area, help_area] =
        Layout::vertical([Constraint::Min(3), Constraint::Length(1)]).areas(f.area());

    let body = Paragraph::new(vec![
        "Session report".into(),
        "".into(),
        format!("fillers per minute: pending"), // TODO: from daemon report
        format!("words per minute: pending"),
        format!("filler breakdown: pending"),
        format!("transcript: pending"),
    ])
    .block(Block::new().borders(Borders::ALL).title("Report"))
    .style(Style::new().add_modifier(Modifier::BOLD));
    f.render_widget(body, body_area);

    f.render_widget(Paragraph::new("[Enter] back to home"), help_area);
}
