#include "textReplacer.h"
#include "text_process.h"
#include "HookTitle.h"
#include <regex>
#include <filesystem>

int mode;
int type;
int retAddAddr = 5;

DWORD originalFuncAddr;
DWORD returnAddress;
DWORD callAddress;
DWORD originalFuncAddr2;
DWORD returnAddress2;
DWORD callAddress2;
DWORD originalFuncAddr3;
DWORD returnAddress3;
DWORD callAddress3;
DWORD originalFuncAddr4;
DWORD returnAddress4;
DWORD callAddress4;

const int maxbuffersize = 0x1000000;
int stridx = 0;

std::string fileContent;
void replace_file_path(char** filename) {
	printf("filename: %s\n", *filename);
    std::filesystem::path fn = std::filesystem::path(*filename).filename();
    std::filesystem::path new_filename = std::filesystem::path("trans") / fn;
	std::string nf = "trans//" + fn.string();
    if (std::filesystem::exists(new_filename)) {
		printf("replace file path: %s -> %s\n", *filename, nf.c_str());
        strcpy_s(*filename, nf.size() + 1, nf.c_str());
    }
}

std::map<std::string, std::string> replaceMap;

void addSjisReplaceMap(std::wstring key, std::wstring value) {
	std::string sjisKey = WideStringToSJISLPCSTR(key);
	std::string sjisValue = WideStringToSJISLPCSTR(value);
	replaceMap[sjisKey] = sjisValue;
}

void init_replaceMap() {
    // English version: no hardcoded Chinese text replacements needed.
    // If English EXE-text replacements are needed in the future,
    // add them here with addSjisReplaceMap().
}


void replace_text(char** text) {
	auto it = replaceMap.find(*text);
	if (it != replaceMap.end()) {
		printf("replace text: %s -> %s\n", *text, it->second.c_str());
		*text = (char*)it->second.c_str();
	}
}

void __declspec(naked) HookFunction_replacePath()
{
    __asm
    {
        pushad
        pushfd

        mov eax, esp
		add eax, 0x24 + 0x0c
        push eax
		call replace_file_path
		add esp, 4

        popfd
        popad

        push callAddress
     
        jmp dword ptr[returnAddress]
    }
}

void __declspec(naked) HookFunction_replacePath2()
{
    __asm
    {
        mov ecx, edi

        pushad
        pushfd

        mov eax, esp
        add eax, 0x24 + 0x00
        push eax
        call replace_file_path
        add esp, 4

        popfd
        popad

        call [edx + 0xC]

        jmp dword ptr[returnAddress2]
    }
}

void __declspec(naked) HookFunction_replaceText1()
{
    __asm
    {

        pushad
        pushfd

        mov eax, esp
        add eax, 0x24 + 0x04
        push eax
        call replace_text
        add esp, 4

        popfd
        popad


        push esi
        mov esi, [esp + 8]

        jmp dword ptr[returnAddress3]
    }
}


void __declspec(naked) HookFunction_replaceText2()
{
    __asm
    {
        pushad
        pushfd

        mov eax, esp
        add eax, 0x24 + 0x04
        push eax
        call replace_text
        add esp, 4

        popfd
        popad


        push ebx
        mov ebx, ecx
        mov edx, [ebx + 0x18]

        jmp dword ptr[returnAddress4]
    }
}

void InstallHook_replacetext()
{
    init_replaceMap();
    DWORD oldProtect;
    originalFuncAddr = 0x4608b2;
    returnAddress = originalFuncAddr + 5;
    callAddress = 0x4AFC49;
    VirtualProtect((LPVOID)originalFuncAddr, 5, PAGE_EXECUTE_READWRITE, &oldProtect);
    *(BYTE*)originalFuncAddr = 0xE9;
    *(DWORD*)(originalFuncAddr + 1) = (DWORD)HookFunction_replacePath - originalFuncAddr - 5;
    VirtualProtect((LPVOID)originalFuncAddr, 5, oldProtect, &oldProtect);


    originalFuncAddr = 0x460d34;
    returnAddress2 = originalFuncAddr + 5;
    VirtualProtect((LPVOID)originalFuncAddr, 5, PAGE_EXECUTE_READWRITE, &oldProtect);
    *(BYTE*)originalFuncAddr = 0xE9;
    *(DWORD*)(originalFuncAddr + 1) = (DWORD)HookFunction_replacePath2 - originalFuncAddr - 5;
    VirtualProtect((LPVOID)originalFuncAddr, 5, oldProtect, &oldProtect);

    originalFuncAddr = 0x408300;
    returnAddress3 = originalFuncAddr + 5;
    VirtualProtect((LPVOID)originalFuncAddr, 5, PAGE_EXECUTE_READWRITE, &oldProtect);
    *(BYTE*)originalFuncAddr = 0xE9;
    *(DWORD*)(originalFuncAddr + 1) = (DWORD)HookFunction_replaceText1 - originalFuncAddr - 5;
    VirtualProtect((LPVOID)originalFuncAddr, 5, oldProtect, &oldProtect);

    originalFuncAddr = 0x4063d0;
    returnAddress4 = originalFuncAddr + 6;
    VirtualProtect((LPVOID)originalFuncAddr, 5, PAGE_EXECUTE_READWRITE, &oldProtect);
    *(BYTE*)originalFuncAddr = 0xE9;
    *(DWORD*)(originalFuncAddr + 1) = (DWORD)HookFunction_replaceText2 - originalFuncAddr - 5;
    VirtualProtect((LPVOID)originalFuncAddr, 5, oldProtect, &oldProtect);
}
