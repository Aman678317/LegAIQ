@echo off
cd /d "C:\Users\acer\OneDrive\inga legal"
echo [1/3] Adding all updated files...
git add -A
echo [2/3] Committing changes...
git commit -m "fix(chat): optimize universal chatbot cloud routing with Groq, NVIDIA and OpenAI fallbacks"
echo [3/3] Pushing to GitHub main branch...
git push origin main
echo.
echo ========================================================
echo All changes have been successfully pushed to GitHub!
echo ========================================================
pause