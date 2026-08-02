home_dir := env("HOME")
test_dir := home_dir / "tmp/test-jwm-bin"

# This repo has exactly two install jobs -- put the bin/ scripts on PATH, and put
# the LaunchAgents where launchd reads them. Each subtree is stowed as its own
# package onto its own target, so the repo root is never a package and nothing
# else here (README, justfile, .git, whatever a tool drops next) reaches $HOME.
#
# --no-folding: make target dirs real dirs with per-file symlinks, never fold a
# whole dir into one symlink. It is what keeps ~/Library/LaunchAgents a real dir.
# Without it, a mac that does not have that dir yet gets it pointed at this repo,
# and every LaunchAgent installed later -- by any app -- lands inside the repo.
stow_flags := "--verbose --no-folding"

@_:
    just --list

# stow one package tree onto its target, creating the target if needed
[private]
stow-pkg target pkg *flags:
    mkdir -p {{target}}
    stow {{stow_flags}} {{flags}} -t {{target}} -S {{pkg}}

# Install the bin/ scripts and the LaunchAgents
install: (stow-pkg (home_dir / "bin") "bin") (stow-pkg (home_dir / "Library") "Library")

# Preview the install without writing anything
check:
    stow {{stow_flags}} --no -t {{home_dir / "bin"}} -S bin
    stow {{stow_flags}} --no -t {{home_dir / "Library"}} -S Library

# Test install into a temp directory
test: (stow-pkg (test_dir / "bin") "bin") (stow-pkg (test_dir / "Library") "Library")

# Clean test directory
clean:
    rm -rf {{test_dir}}
