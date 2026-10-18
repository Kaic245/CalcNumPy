"""Menu de terminal opcional, usando as mesmas funções da janela."""
from decimal import DecimalException
from backend.calculos import calcular, comparar_sequencia
from frontend.apresentacao import formatar_erro_relativo


def exibir(resultado):
    """Mostra um resultado sem recalcular métricas no frontend."""
    mantissa, expoente = resultado['cientifico_aproximado']
    print(f"Referência: {resultado['exato']}")
    print(f"Aproximado: {resultado['aproximado']} = {mantissa} × 10^{expoente}")
    print(f"Erro absoluto: {resultado['erro_absoluto']}")
    print('Erro relativo: ' + formatar_erro_relativo(resultado['erro_relativo']))


def demonstrar_exemplos():
    """Os exemplos usam o backend; sua validação automática está em tests/."""
    for titulo, x, y, operacao, limitar in [
        ('Soma simples', '0.12345', '0.67890', '+', False),
        ('Cancelamento', '0.76545', '0.76541', '-', True),
    ]:
        print('\n' + titulo)
        for modo in ('truncar', 'arredondar'):
            print(modo + ':')
            exibir(calcular(x, y, operacao, 4, modo, limitar))
    print('\nDez termos de 0.56786:')
    for resultado in comparar_sequencia('0.56786', 10, 4):
        print(resultado['modo'] + ':')
        for passo in resultado['passos']:
            print(f"  {passo['indice']}: {passo['aproximado']} | Ea acumulado: {passo['erro_absoluto']}")
        print('Er final: ' + formatar_erro_relativo(resultado['erro_relativo']))


def main_loop():
    print('SIMULADOR DE PROPAGAÇÃO DE ERROS NUMÉRICOS')
    while True:
        try:
            print('\n1. Calcular  |  2. Exemplos do projeto  |  3. Sair')
            opcao = input('Opção: ').strip()
            if opcao == '3':
                break
            if opcao == '2':
                demonstrar_exemplos()
                continue
            if opcao != '1':
                print('Escolha 1, 2 ou 3.')
                continue
            print('Enter vazio em x ou y volta ao menu.')
            x = input('x: ').strip()
            if not x:
                continue
            y = input('y: ').strip()
            if not y:
                continue
            operacao = input('Operação (+, -, *, /): ').strip()
            n_digitos = int(input('Dígitos [4]: ').strip() or '4')
            modo = input('Método (truncar/arredondar) [truncar]: ').strip() or 'truncar'
            if modo == 't':
                modo = 'truncar'
            elif modo == 'a':
                modo = 'arredondar'
            limitar = input('Limitar também operandos? (s/n) [n]: ').strip().lower()
            if limitar not in ('', 's', 'n'):
                raise ValueError('Digite s ou n para limitar os operandos.')
            exibir(calcular(x, y, operacao, n_digitos, modo, limitar == 's'))
        except ValueError as erro:
            print(f'Erro: {erro}')
        except DecimalException:
            print('Não foi possível representar esse cálculo. Revise os valores.')
        except KeyboardInterrupt:
            print('\nOperação cancelada. Voltando ao menu.')
        except EOFError:
            break
    print('Encerrando simulador.')
