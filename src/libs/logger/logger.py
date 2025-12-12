from colored import Fore, Style


def info(message: str):
    print(f"{Fore.cyan}[*] {message}{Style.reset}", flush=True)


def success(message: str):
    print(f"{Fore.green}[+] {message}{Style.reset}", flush=True)


def warning(message: str):
    print(f"{Fore.yellow}[!] {message}{Style.reset}", flush=True)


def error(message: str):
    print(f"{Fore.red}[ERROR] {message}{Style.reset}", flush=True)


def debug(message: str):
    print(f"{Fore.grey_50}[DEBUG] {message}{Style.reset}", flush=True)


def trace(message: str):
    print(f"{Fore.grey_30}[TRACE] {message}{Style.reset}", flush=True)


def plain(message: str):
    print(f"    {message}", flush=True)


def step(message: str):
    print(f"{Fore.magenta}[→] {message}{Style.reset}", flush=True)


def data(message: str):
    print(f"{Fore.blue}[DATA] {message}{Style.reset}", flush=True)
