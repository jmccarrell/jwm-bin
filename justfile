home_dir := env("HOME")
test_dir := home_dir / "tmp/test-jwm-bin"

# What gets stowed is the whole repo tree ('.'), minus everything matched by
# .stow-local-ignore -- repo meta (justfile, README, .git, .claude) plus the
# scratch dirs. That file is the single source of truth for exclusions; there
# are deliberately no --ignore= flags here.
#
# flags shared by every stow call:
#   --no-folding : make target dirs real dirs with per-file symlinks, never fold a
#                  whole dir into one symlink. On a fresh mac ~/bin does not exist
#                  yet, and without this stow would point ~/bin at the repo's bin/
#                  -- so every later ~/bin file would land inside this repo.
#   NOTE: --adopt is deliberately NOT used. Adoption is a one-off import tool; in a
#   routine install it silently pulls target files into the repo and diverges machines.
stow_flags := "--verbose --no-folding"

@_:
    just --list

# Install the scripts into $HOME
install:
    stow {{stow_flags}} -t {{home_dir}} -S .

# Preview the install without writing anything
check:
    stow {{stow_flags}} --no -t {{home_dir}} -S .

# Test install into a temp directory
test:
    mkdir -p {{test_dir}}
    stow {{stow_flags}} -t {{test_dir}} -S .

# Clean test directory
clean:
    rm -rf {{test_dir}}
