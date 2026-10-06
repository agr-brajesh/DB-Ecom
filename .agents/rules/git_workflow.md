# Git Workflow Rules: No Automatic Staging, Committing, or Pushing

## Strict Policy:
1. **NEVER execute `git add`**: The assistant must NOT automatically stage files or changes.
2. **NEVER execute `git commit`**: The assistant must NOT automatically commit changes.
3. **NEVER execute `git push`**: The assistant must NOT push to remote repositories (GitHub, GitLab, etc.).
4. **Manual User Control**: All Git actions—staging, reviewing diffs, writing commit messages, committing, and pushing—must be performed manually by the user.
5. **No exceptions**: Even at the end of a phase, task, or milestone, do NOT propose or run git staging, commits, or pushes. Provide only the summary of file changes and test results.
