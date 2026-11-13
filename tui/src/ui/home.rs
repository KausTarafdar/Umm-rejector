use ratatui::Frame;
use ratatui::layout::{Alignment, Constraint, Layout};
use ratatui::style::{Color, Modifier, Style};
use ratatui::widgets::{Block, Borders, Paragraph};

use crate::app::App;

pub fn draw(f: &mut Frame, app: &App) {
    let [status_area, body_area, help_area] = Layout::vertical([
        Constraint::Length(1),
        Constraint::Min(3),
        Constraint::Length(1),
    ])
    .areas(f.area());

    let status = if app.daemon_online {
        Paragraph::new("daemon: online").style(Style::new().fg(Color::Green))
    } else {
        Paragraph::new("daemon: offline, run `umm-serve`").style(Style::new().fg(Color::Red))
    };
    f.render_widget(status.alignment(Alignment::Right), status_area);

    let body = Paragraph::new(vec![
        "Umm-rejector".into(),
        "".into(),
        "Press Enter to start a session, q to quit.".into(),
    ])
    .block(Block::new().borders(Borders::ALL).title("Home"))
    .style(Style::new().add_modifier(Modifier::BOLD));
    f.render_widget(body, body_area);

    f.render_widget(
        Paragraph::new("[Enter] start   [q] quit"),
        help_area,
    );
}
