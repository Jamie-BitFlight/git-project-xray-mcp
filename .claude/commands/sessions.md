---
allowed-tools: Bash(sessions/bin/sessions*), Bash(sessions/bin/sessions.bat*)
argument-hint: "Use '/sessions help' for all commands"
description: "Unified sessions management (tasks, state, config, uninstall)"
disable-model-invocation: true
---
!sessions/bin/sessions $ARGUMENTS --from-slash

Present the output to the user.
