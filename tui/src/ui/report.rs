use ratatui::Frame;
use ratatui::layout::{Constraint, Layout};
use ratatui::style::{Color, Modifier, Style};
use ratatui::widgets::{Block, Borders, Paragraph};

use crate::app::App;

pub fn draw(f: &mut Frame, app: &App) {
    let [body_area, help_area] =
        Layout::vertical([Constraint::Min(3), Constraint::Length(1)]).areas(f.area());

    let mut lines: Vec<String> = vec!["No report available.".into()];
    if let Some((question, report)) = &app.report {
        let breakdown = if report.filler_breakdown.is_empty() {
            "none".to_string()
        } else {
            let mut items: Vec<String> = report
                .filler_breakdown
                .iter()
                .map(|(word, count)| format!("{} x{}", word, count))
                .collect();
            items.sort();
            items.join(", ")
        };
        lines = vec![
            question.clone(),
            String::new(),
            format!(
                "duration: {:.1}s | fillers: {} ({:.2}/min) | wpm: {:.1}",
                report.duration_secs,
                report.filler_count,
                report.fillers_per_minute,
                report.words_per_minute
            ),
            format!("filler breakdown: {}", breakdown),
            String::new(),
            format!("transcript: {}", if report.transcript.is_empty() { "(empty)" } else { &report.transcript }),
        ];
    }

    let body = Paragraph::new(lines.into_iter().map(ratatui::text::Line::from).collect::<Vec<_>>())
        .block(Block::new().borders(Borders::ALL).title("Report"))
        .style(Style::new().add_modifier(Modifier::BOLD));
    f.render_widget(body, body_area);

    if let Some((_, report)) = &app.report {
        let good = report.fillers_per_minute < 2.0;
        let verdict = if good {
            Paragraph::new("clean delivery, keep it up").style(Style::new().fg(Color::Green))
        } else {
            Paragraph::new("filler rate above 2/min, try pausing instead").style(Style::new().fg(Color::Yellow))
        };
        f.render_widget(verdict, body_area);
    }

    f.render_widget(Paragraph::new("[Enter] back to home"), help_area);
}
