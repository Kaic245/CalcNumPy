"""Ponto de entrada: janela por padrão, terminal ou exemplos quando solicitado."""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description='Simulador de propagação de erros numéricos')
    opcoes = parser.add_mutually_exclusive_group()
    opcoes.add_argument('--cli', action='store_true', help='Abrir o menu de terminal')
    opcoes.add_argument('--exemplos', action='store_true', help='Exibir os três exemplos do projeto')
    argumentos = parser.parse_args()

    if argumentos.cli:
        from frontend.terminal import main_loop
        main_loop()
        return 0
    if argumentos.exemplos:
        from frontend.terminal import demonstrar_exemplos
        demonstrar_exemplos()
        return 0
    try:
        from frontend.janela import iniciar
    except ModuleNotFoundError as erro:
        if erro.name and erro.name.startswith('PySide6'):
            print('Ative o ambiente virtual: source .venv/bin/activate')
            print('Instale as dependências: python -m pip install -r requirements.txt')
            print('Para usar apenas o terminal: python3 main.py --cli')
            return 1
        raise
    return iniciar()


if __name__ == '__main__':
    sys.exit(main())
