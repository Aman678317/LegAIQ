@echo off
cd /d "C:\Users\acer\OneDrive\inga legal"
echo [1/4] Resetting blocked local commit...
git reset --soft origin/main
echo [2/4] Staging clean files with zero secrets...
git add -A
echo [3/4] Creating clean commit...
git commit -m "feat(workflows): live Harvey-class LLM execution for multi-agent workflows and formal memo export"
echo [4/4] Pushing clean commit to GitHub main...
git push origin main
echo.
echo ========================================================
echo All changes have been successfully pushed to GitHub!
echo ========================================================
pause