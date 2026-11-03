//! A machine that ran tincan on its own moves over once. tincan's last update installed reason-network beside it,
//! with a copy under the old name for what still starts that: the old login service, agents' configs, and the old
//! updater checking the version. `paths` has already moved the state; the daemon's first start here rewires the
//! agents and swaps the login service. Agent sessions started before keep working until they end.

use crate::{AGENT_NAME, LEGACY_NAME, paths, setup, util};

/// Started under the old name, runs as reason-network instead, so everything after this is our own binary.
pub fn as_ours() {
    let Ok(me) = util::current_exe() else { return };
    let ours = me.with_file_name(format!("{AGENT_NAME}{}", std::env::consts::EXE_SUFFIX));
    if me.file_stem().is_none_or(|s| s != LEGACY_NAME) || !ours.exists() {
        return;
    }
    let mut cmd = std::process::Command::new(ours);
    cmd.args(std::env::args_os().skip(1));
    #[cfg(unix)]
    eprintln!("{AGENT_NAME}: {}", std::os::unix::process::CommandExt::exec(&mut cmd));
    #[cfg(windows)]
    if let Ok(status) = cmd.status() {
        std::process::exit(status.code().unwrap_or(1));
    }
}

/// Whether a tincan copy beside `exe` is still waiting to be moved over: a copy of this very binary.
pub fn waiting(exe: &std::path::Path) -> bool {
    let old = setup::legacy_exe(exe);
    std::fs::symlink_metadata(&old).is_ok_and(|m| m.is_file())
        && std::fs::read(&old).is_ok_and(|b| std::fs::read(exe).is_ok_and(|o| o == b))
}

/// After an update replaced `exe`, keeps a copy that was waiting a copy of the new binary, so the move-over can still
/// finish. A new file renamed over it: never a moment without tincan, nor a half-written one. (A tincan.exe that's
/// running can't be replaced: it stays as it was, still handing over to us.)
pub fn keep_waiting_copy(exe: &std::path::Path) {
    let old = setup::legacy_exe(exe);
    let new = old.with_extension("new");
    if std::fs::copy(exe, &new).is_err() || std::fs::rename(&new, &old).is_err() {
        let _ = std::fs::remove_file(&new);
    }
}

/// Moves this machine's agents and login service over from the tincan beside us, if that hasn't happened yet.
/// Lines go to `log`.
pub async fn run(log: fn(&str)) {
    let Ok(exe) = setup::exe() else { return };
    let old = setup::legacy_exe(&exe);
    // Only tincan's last update leaves this: a copy of this very binary under the old name. Anything else called tincan
    // (a tincan of its own, a script) isn't ours to move. Once moved, it's a link to us, or gone.
    let copy = waiting(&exe);
    // Where the Reason CLI's engine is installed too, it owns the agents and the service.
    let reason_cli = paths::user_home().join(".reason").join("bin").join(exe.file_name().unwrap_or_default()).exists();
    if util::from_source() || crate::managed() || reason_cli || !copy {
        return;
    }
    let out = setup::apply(&exe, &setup::legacy_wiring(&exe), &[], None, false).await;
    for line in out.lines.iter().chain(&out.notes) {
        log(&format!("moved over from {LEGACY_NAME}: {line}"));
    }
    // The login service: ours goes in first, and the old one only once it has (stopped last: it may be what runs this
    // very process; ours takes over when it's gone).
    let service = paths::env_var_os("NO_SERVICE").is_none();
    #[cfg(unix)]
    let legacy = service && setup::legacy_service(&exe);
    #[cfg(unix)]
    let swap = legacy
        && match setup::install_service_from_daemon(&exe).await {
            Ok(s) => {
                log(&format!("moved over from {LEGACY_NAME}: service: {s}"));
                true
            }
            Err(e) => {
                log(&format!("moved over from {LEGACY_NAME}: kept its service, ours didn't install: {e:#}"));
                false
            }
        };
    // (A Run entry can't carry an explicit home.)
    #[cfg(windows)]
    if service && paths::env_var_os("HOME").is_none() {
        setup::move_legacy_run_entry(&exe);
    }
    // The copy becomes a link to us, so `tincan` keeps working, once no agent and no service still runs it (else the
    // next start tries again). Windows removes it instead, once nothing runs it: the next start.
    #[cfg(unix)]
    let service_moved = !legacy || swap;
    #[cfg(windows)]
    let service_moved = !setup::legacy_run_entry(&exe);
    let left = setup::legacy_wiring(&exe);
    if !left.is_empty() {
        log(&format!("moved over from {LEGACY_NAME}: kept it for {} until they move over", left.join(", ")));
    } else if service_moved && std::fs::remove_file(&old).is_ok() {
        #[cfg(unix)]
        let _ = std::os::unix::fs::symlink(AGENT_NAME, &old);
    }
    #[cfg(unix)]
    if swap {
        setup::unregister_legacy_service(&exe);
        setup::stop_legacy_service();
    }
}
