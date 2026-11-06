# Deployment target

Before deploying, check `PI_DECK_IP` in the current environment and then the
repository-local `.env.local`. If it is unset or empty in both places, ask the
user for the deck's current IP address. Do not guess the address or probe stale
addresses from documentation.

Once `PI_DECK_IP` is available, use `./scripts/deploy.sh`; it is the canonical
deployment path. `PI_DECK_USER` may override the SSH user and defaults to
`rafael`.

Never commit the actual private IP. Store it only in the ignored `.env.local`
file or export it in the shell.
