@echo off
echo ============================================
echo  LegAIQ — Push All Fixes to GitHub
echo ============================================
echo.
cd /d "C:\Users\acer\OneDrive\inga legal"
echo [1/4] Staging all changed files...
git add -A
echo [2/4] Creating commit...
git commit -m "fix: universal AI fallback everywhere — chat, questions, backend always respond"
echo [3/4] Pushing to GitHub main branch...
git push origin main
echo.
echo ============================================
echo  SUCCESS! Vercel + Render will auto-redeploy
echo  Wait ~60 seconds then test the site
echo ============================================
echo.
pause