# Common Brewfile — every mac. Read via `brew bundle --file`; never stowed.
#
# Two tiers, kept apart because they are re-derived by different rules. Adding an
# entry to the wrong one makes it unclear later why it is here at all.
#
# rustup belongs in the first tier and cannot be expressed: jwm_update_tools runs
# `rustup update` unguarded, but rustup comes from rustup.rs, not Homebrew.

# Tier 1 — hard requirements. Invoked by bin/daily, bin/update or jwm_update_tools
# with no `command -v` guard, per the policy at bin/daily:44. Absence breaks a
# chore run outright.
brew "bash"  # shebang for bin/daily and bin/update; a dependency, not a leaf
brew "git"
brew "just"
brew "stow"
brew "uv"

# Tier 2 — named by the tracked config behind a `command -v` guard, and present on
# both macs. Absence degrades a shell feature rather than breaking a run, so these
# are here by evidence rather than necessity.
brew "ack"
brew "bash-completion@2"
brew "direnv"
brew "fzf"
brew "gh"
brew "go"
brew "grep"
brew "k9s"
brew "kubectx"
brew "kubernetes-cli"
brew "mise"
brew "ripgrep"
brew "starship"
brew "tree"
brew "worktrunk"
brew "yazi"
brew "zoxide"
