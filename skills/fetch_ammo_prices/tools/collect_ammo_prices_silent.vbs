Set WshShell = CreateObject("WScript.Shell")
WshShell.Run Chr(34) & Replace(WScript.ScriptFullName, "collect_ammo_prices_silent.vbs", "collect_ammo_prices.bat") & Chr(34), 0, False
