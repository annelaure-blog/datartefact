#!/bin/bash
set -e

echo "→ Pushing to GitHub..."
git add -A
git commit -m "Deploy $(date '+%Y-%m-%d %H:%M')" || echo "Nothing to commit."
git push origin main 2>&1

echo "→ Deploying to server..."
rsync -az --delete \
  --exclude='.git' \
  --exclude='.DS_Store' \
  --exclude='deploy.sh' \
  "/Users/annefreant/Desktop/datartefact index/" \
  debian@54.37.230.99:/tmp/datartefact-deploy/

ssh debian@54.37.230.99 "
  sudo rsync -a --delete /tmp/datartefact-deploy/ /var/www/datartefact/ &&
  sudo chown -R datartefact:datartefact /var/www/datartefact &&
  rm -rf /tmp/datartefact-deploy
"

echo "✓ Done — https://datartefact.com is up to date."
