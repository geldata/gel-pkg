use std::ffi::OsString;
use std::os::unix::process::CommandExt;
use std::process::Command;

fn main() {
    let mut exe = std::env::current_exe().unwrap();
    if exe.is_symlink() {
        match exe.canonicalize() {
            Ok(target) => exe = target,
            Err(e) => panic!("failed to canonicalize executable path {exe:?}: {e:?}"),
        }
    }
    let exe_dir = match exe.parent() {
        Some(dir) => dir,
        None => panic!("current executable path is not a file?"),
    };
    let python = exe_dir.join("python3");
    if !python.exists() {
        panic!("python3 not found in {exe_dir:?}");
    }
    let mut args: Vec<_> = std::env::args_os().skip(1).collect();
    let mut py_script = exe.clone();
    py_script.set_extension("py");
    let mut script_args = vec![OsString::from("-I"), OsString::from(py_script)];
    script_args.append(&mut args);
    let err = Command::new(&python).args(&script_args).exec();
    panic!("failed to execute {python:?}: {err:?}");
}
