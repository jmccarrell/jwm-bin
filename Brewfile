# Common Brewfile — every mac. Read via `brew bundle --file`; never stowed.
#
# Hard requirements only: what bin/daily, bin/update and jwm_update_tools invoke
# with no `command -v` guard, per the policy stated at bin/daily:44. A guarded
# reference degrades gracefully when absent and belongs in a host file instead.
#
# rustup is a hard requirement this file cannot express: jwm_update_tools runs
# `rustup update` unguarded, but rustup comes from rustup.rs, not Homebrew.

brew "bash"  # shebang for bin/daily and bin/update; a dependency, not a leaf
brew "git"
brew "just"
brew "stow"
brew "uv"
