//! The daemon's local socket: a Unix socket, or a named pipe on Windows.

use crate::paths;
use anyhow::{Context, Result};
use std::io;

#[cfg(unix)]
pub use tokio::net::UnixStream as Stream;
#[cfg(windows)]
pub use tokio::net::windows::named_pipe::NamedPipeClient as Stream;

/// The daemon's end of a client's connection.
#[cfg(unix)]
pub use tokio::net::UnixStream as Accepted;
#[cfg(windows)]
pub use tokio::net::windows::named_pipe::NamedPipeServer as Accepted;

#[cfg(unix)]
pub async fn connect() -> io::Result<Stream> {
    Stream::connect(paths::socket()).await
}

#[cfg(windows)]
pub async fn connect() -> io::Result<Stream> {
    use std::os::windows::io::AsRawHandle;
    use tokio::net::windows::named_pipe::ClientOptions;
    let mut tries = 0;
    let pipe = loop {
        match ClientOptions::new().open(paths::socket()) {
            // Every instance is taken for a moment while the daemon opens the next one.
            Err(e)
                if e.raw_os_error() == Some(windows_sys::Win32::Foundation::ERROR_PIPE_BUSY as i32) && tries < 20 =>
            {
                tries += 1
            }
            r => break r?,
        }
        tokio::time::sleep(std::time::Duration::from_millis(25)).await;
    };
    // Anyone on the machine can make a pipe by that name: talk only to the daemon that holds our lock.
    let mut server = 0;
    // SAFETY: asks about the pipe handle we hold.
    unsafe { windows_sys::Win32::System::Pipes::GetNamedPipeServerProcessId(pipe.as_raw_handle(), &mut server) };
    if crate::client::running_daemon() != Some(server) {
        return Err(io::Error::other(format!("{} is not this user's network daemon", paths::socket().display())));
    }
    Ok(pipe)
}

/// Where the daemon takes connections. Only the daemon holding the lock opens it.
pub struct Listener(#[cfg(unix)] tokio::net::UnixListener, #[cfg(windows)] Accepted);

impl Listener {
    #[cfg(unix)]
    pub fn bind() -> Result<Self> {
        let sock = paths::socket();
        paths::ensure_socket_dir()?;
        let _ = std::fs::remove_file(&sock);
        let listener = tokio::net::UnixListener::bind(&sock).with_context(|| format!("binding {}", sock.display()))?;
        crate::util::chmod(&sock, 0o600)?;
        paths::link_legacy_socket(&sock);
        Ok(Listener(listener))
    }

    /// The first instance of the pipe, so nobody else holds its name.
    #[cfg(windows)]
    pub fn bind() -> Result<Self> {
        Ok(Listener(pipe(true).with_context(|| format!("creating {}", paths::socket().display()))?))
    }

    #[cfg(unix)]
    pub async fn accept(&mut self) -> io::Result<Accepted> {
        Ok(self.0.accept().await?.0)
    }

    /// Each client gets an instance of its own: once one connects, the next waits for whoever comes after.
    #[cfg(windows)]
    pub async fn accept(&mut self) -> io::Result<Accepted> {
        loop {
            let connected = self.0.connect().await;
            let this = std::mem::replace(&mut self.0, pipe(false)?);
            // One that left before we got to it is dropped.
            if connected.is_ok() {
                return Ok(this);
            }
        }
    }
}

#[cfg(windows)]
fn pipe(first: bool) -> io::Result<Accepted> {
    tokio::net::windows::named_pipe::ServerOptions::new().first_pipe_instance(first).create(paths::socket())
}
