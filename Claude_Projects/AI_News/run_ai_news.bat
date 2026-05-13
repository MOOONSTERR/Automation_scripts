@echo off
:: 进入项目目录
cd /d "C:\Users\hubin\OneDrive - JP NELSON EQUIPMENT PTE LTD\Documents\Claude_Projects\AI_News"

:: 使用绝对路径输出日志，确保文件一定能生成
".\node_modules\.bin\tsx.cmd" ".\src\index.ts" >> "C:\Users\hubin\OneDrive - JP NELSON EQUIPMENT PTE LTD\Documents\Claude_Projects\AI_News\task_log.txt" 2>&1