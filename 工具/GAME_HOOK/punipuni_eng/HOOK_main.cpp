#include <Windows.h>
#include <Shlwapi.h>
#include <fstream>
#include <iostream>
#include "HOOK_main.h"
#include "HookTitle.h"
#include "text_process.h"
#include "textReplacer.h"

void CreateConsole()
{
	if (AllocConsole())
	{
		FILE* fp;
		freopen_s(&fp, "CONOUT$", "w", stdout);
		SetConsoleOutputCP(CP_UTF8);
	}
}

void HOOK_main() {
	// --- File path redirection (trans/ folder) ---
	InstallHook_replacetext();

	// --- Window title ---
	changeWindowCfg.isCheckOri = false;
	changeWindowCfg.newWindowName = L"Punipuni - English";
	hookTitle_main();

	// --- Text replacement (reads trans\data.bin) ---
	install_hook_textreplaceEx(2, "trans\\data.bin", "yorimichi");
}
