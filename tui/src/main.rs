mod app;
mod audio;
mod api;
mod ui;

use anyhow::Result;

#[tokio::main]
async fn main() -> Result<()> {
    let mut terminal = ui::init_terminal()?;
    let result = app::run(&mut terminal).await;
    ui::restore_terminal(&mut terminal)?;
    result
}
