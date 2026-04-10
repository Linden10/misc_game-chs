#pragma once
#include <Windows.h>
#include <string>

// Install the half-width-aware text replacement hook.
// mode: 1=TextOutA, 2=GetGlyphOutlineA (recommended), 3=ExtTextOutA
void install_hook_textreplace_halfwidth(int mode, std::string filepath, std::string key);
