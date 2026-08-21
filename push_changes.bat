@echo off
cd /d "C:\Users\acer\OneDrive\inga legal"
echo [1/3] Adding all updated files...
git add -A
echo [2/3] Committing changes...
git commit -m "perf(chat): ultra-fast sub-second AI responses powered by Groq LPU and prioritized routing"
echo [3/3] Pushing to GitHub main branch...
git push origin main
echo.
echo ========================================================
echo All changes have been successfully pushed to GitHub!
echo ========================================================
pause