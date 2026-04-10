// textReplacer_halfwidth.cpp
//
// Modified GetGlyphOutlineA hook that adjusts glyph advance width (gmCellIncX)
// for single-byte ASCII characters, enabling half-width English text rendering
// in engines that use fixed full-width character spacing.
//
// Based on LIB/textReplacer.cpp, with the following changes:
// - HOOK_GetGlyphOutlineA_HalfWidth: after calling the real GetGlyphOutlineA/W,
//   checks if the character is single-byte (ASCII). If so, halves gmCellIncX
//   so the engine advances the cursor by half the normal width.
// - Keeps the data.bin character replacement logic for any non-ASCII chars
//   that still need substitution.

#include "textReplacer.h"
#include "textReplacer_halfwidth.h"

// -----------------------------------------------------------------------
// Half-width GetGlyphOutlineA hook
// -----------------------------------------------------------------------
DWORD WINAPI HOOK_GetGlyphOutlineA_HalfWidth(
    HDC hdc,
    UINT uChar,
    UINT uFormat,
    LPGLYPHMETRICS lpgm,
    DWORD cbBuffer,
    LPVOID lpvBuffer,
    const MAT2* lpmat2)
{
    char bytes[3];
    UINT t = uChar;
    bytes[0] = static_cast<char>((t >> 8) & 0xFF);
    bytes[1] = static_cast<char>(t & 0xFF);
    bytes[2] = '\0';

    // --- Single-byte character (ASCII / half-width) ---
    if (bytes[0] == '\x00') {
        DWORD res = TrueGetGlyphOutlineA(hdc, uChar, uFormat, lpgm, cbBuffer, lpvBuffer, lpmat2);
        if (res != GDI_ERROR && lpgm != NULL) {
            // Halve the horizontal advance so ASCII takes half the cell width.
            // The engine normally advances by a full CJK character width (e.g. 24px);
            // this makes it advance by half (e.g. 12px) for Latin characters.
            lpgm->gmCellIncX = static_cast<short>(lpgm->gmCellIncX / 2);
        }
        return res;
    }

    // --- 0xF0xx range: pass through unchanged ---
    if (bytes[0] == '\xf0') {
        DWORD res = TrueGetGlyphOutlineA(hdc, uChar, uFormat, lpgm, cbBuffer, lpvBuffer, lpmat2);
        return res;
    }

    // --- 0x81xx range (Japanese punctuation/symbols): pass through unchanged ---
    if (bytes[0] == '\x81') {
        DWORD res = TrueGetGlyphOutlineA(hdc, uChar, uFormat, lpgm, cbBuffer, lpvBuffer, lpmat2);
        return res;
    }

    // --- Double-byte character: apply data.bin replacement ---
    std::string str(bytes);
    std::wstring wstr = sjisStringToWString(str);

    HFONT hFont = (HFONT)GetCurrentObject(hdc, OBJ_FONT);
    LOGFONTA logFont;
    GetObjectA(hFont, sizeof(LOGFONTA), &logFont);

    // Use Arial for English rendering (matches HOOK_main.cpp font override)
    strcpy_s(logFont.lfFaceName, LF_FACESIZE, "Arial");
    logFont.lfCharSet = ANSI_CHARSET;

    HFONT hNewFont = CreateFontIndirectA(&logFont);
    HFONT hOldFont = (HFONT)SelectObject(hdc, hNewFont);

    // Apply character substitution from data.bin if a mapping exists
    if (charReplaceMap.find(wstr) != charReplaceMap.end()) {
        wstr = charReplaceMap[wstr];
    }

    uChar = static_cast<UINT>(wstr.c_str()[0]);
    DWORD res = GetGlyphOutlineW(hdc, uChar, uFormat, lpgm, cbBuffer, lpvBuffer, lpmat2);

    SelectObject(hdc, hOldFont);
    DeleteObject(hNewFont);
    return res;
}

// -----------------------------------------------------------------------
// Half-width TextOutA hook
// -----------------------------------------------------------------------
BOOL WINAPI HOOK_TextOutA_HalfWidth(
    HDC hdc,
    int nXStart,
    int nYStart,
    LPCSTR lpString,
    int cbString)
{
    std::wstring new_wstr = changeText(std::string(lpString, cbString));
    HFONT hFont = (HFONT)GetCurrentObject(hdc, OBJ_FONT);
    LOGFONTA logFont;
    GetObjectA(hFont, sizeof(LOGFONTA), &logFont);

    if (cbString == 2 && lpString[0] == '\x81') {
        // Japanese symbols: keep original font
        strcpy_s(logFont.lfFaceName, 11, "MS Gothic");
    }
    else {
        logFont.lfCharSet = ANSI_CHARSET;
        strcpy_s(logFont.lfFaceName, LF_FACESIZE, "Arial");
    }
    HFONT hNewFont = CreateFontIndirectA(&logFont);
    HFONT hOldFont = (HFONT)SelectObject(hdc, hNewFont);
    BOOL result = TextOutW(hdc, nXStart, nYStart, new_wstr.c_str(), (int)wcslen(new_wstr.c_str()));
    SelectObject(hdc, hOldFont);
    DeleteObject(hNewFont);
    return result;
}

// -----------------------------------------------------------------------
// Half-width ExtTextOutA hook
// -----------------------------------------------------------------------
BOOL WINAPI HOOK_ExtTextOutA_HalfWidth(
    HDC hdc,
    int X, int Y,
    UINT fuOptions,
    const RECT* lprc,
    LPCSTR lpString,
    UINT cbCount,
    const INT* lpDx)
{
    if (lpString == NULL) {
        return TrueExtTextOutA(hdc, X, Y, fuOptions, lprc, lpString, cbCount, lpDx);
    }
    std::wstring new_wstr = changeText(lpString);
    auto res = ExtTextOutW(hdc, X, Y, fuOptions, lprc, new_wstr.c_str(), (UINT)wcslen(new_wstr.c_str()), lpDx);
    return res;
}

// -----------------------------------------------------------------------
// Installer
// -----------------------------------------------------------------------
void install_hook_textreplace_halfwidth(int mode, std::string filepath, std::string key) {
    charReplaceMap = readReplaceMap(filepath, key);
    DetourTransactionBegin();
    DetourUpdateThread(GetCurrentThread());
    if (mode == 1) {
        DetourAttach(&(PVOID&)TrueTextOutA, HOOK_TextOutA_HalfWidth);
    }
    else if (mode == 2) {
        DetourAttach(&(PVOID&)TrueGetGlyphOutlineA, HOOK_GetGlyphOutlineA_HalfWidth);
    }
    else if (mode == 3) {
        DetourAttach(&(PVOID&)TrueExtTextOutA, HOOK_ExtTextOutA_HalfWidth);
    }
    DetourTransactionCommit();
}
