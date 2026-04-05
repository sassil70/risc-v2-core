Remove-NetFirewallRule -DisplayName "Open 8002 TCP" -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName "Allow Python Uvicorn" -ErrorAction SilentlyContinue

New-NetFirewallRule -DisplayName "Open 8002 TCP" -Direction Inbound -LocalPort 8002 -Protocol TCP -Action Allow -Profile Any
New-NetFirewallRule -DisplayName "Allow Python Uvicorn" -Direction Inbound -Program "C:\Users\Salim B Assil\AppData\Local\Programs\Python\Python311\python.exe" -Action Allow -Profile Any
