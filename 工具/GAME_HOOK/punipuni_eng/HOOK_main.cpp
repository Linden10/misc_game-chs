#include <Windows.h>
#include <Shlwapi.h>
#include <fstream>
#include <iostream>
#include "HOOK_main.h"
#include "HookTitle.h"
#include "text_process.h"
#include "textReplacer.h"
#include "textReplacer_halfwidth.h"

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

	// --- Half-width English text via GetGlyphOutlineA hook ---
	// Mode 2 = hook GetGlyphOutlineA with half-width support for ASCII
	install_hook_textreplace_halfwidth(2, "trans\\data.bin", "yorimichi");

	// --- Font override ---
	// Use a proportional-friendly font; charset 0 = ANSI_CHARSET
	newFontName = L"Arial";
	newCharset = 0;  // ANSI_CHARSET (supports half-width Latin)
	installFontHook_main(1, 1, 1, 0);
}
