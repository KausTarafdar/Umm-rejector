use ratatui::Frame;
use ratatui::layout::{Alignment, Constraint, Layout};
use ratatui::style::{Color, Modifier, Style};
use ratatui::widgets::{Block, Borders, Paragraph};

use crate::app::App;

pub fn draw(f: &mut Frame, app: &App) {
    let [question_area, counter_area, help_area] = Layout::vertical([
        Constraint::Min(3),
        Constraint::Length(1),
        Constraint::Length(1),
    ])
    .areas(f.area());

    let remaining = app
        .question
        .as_ref()
        .map(|_| 60u32.saturating_sub(app.elapsed_secs))
        .unwrap_or(0);

    let question = Paragraph::new(app.question.clone().unwrap_or_default())
        .block(
            Block::new()
                .borders(Borders::ALL)
                .title(format!("Question | {}s remaining", remaining)),
        )
        .wrap(ratatui::widgets::Wrap { trim: true })
        .style(Style::new().add_modifier(Modifier::BOLD));
    f.render_widget(question, question_area);

    let counter = Paragraph::new(format!("UMM count: {}", app.filler_count))
        .style(Style::new().fg(Color::Yellow))
        .alignment(Alignment::Center);
    f.render_widget(counter, counter_area);

    f.render_widget(
        Paragraph::new("speak until the timer ends   [Esc] stop"),
        help_area,
    );
}
