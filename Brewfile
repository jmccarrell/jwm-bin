# Common Brewfile — every mac. Read via `brew bundle --file`; never stowed.
#
# Three tiers, kept apart because each is re-derived by a different rule and the
# last cannot be re-derived at all. Put an entry in the wrong one and the next
# person re-deriving that tier will either keep something unwanted or delete
# something chosen.
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

# Tier 3 — wanted on both macs, and named by nothing. No config file invokes
# these, so unlike the tiers above they cannot be re-derived: they are here by
# decision, and only a decision removes them. Do not prune one for looking
# unreferenced.
brew "coreutils"
brew "crane"
brew "entr"
brew "gnupg"
brew "hadolint"
brew "helm"
brew "jq"
brew "skopeo"
brew "tmux"
brew "watch"
brew "wget"
brew "yamllint"
brew "yq"
