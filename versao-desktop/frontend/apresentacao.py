"""Formatação e exportação de resultados; não realiza cálculos numéricos."""
import csv
from decimal import localcontext


def formatar_erro_relativo(erro):
    if erro is None:
        return 'Indefinido (valor aproximado = 0)'
    # Multiplicar por 100 deve preservar os dígitos antes da formatação visual.
    with localcontext() as contexto:
        contexto.prec = max(50, len(erro.as_tuple().digits) + 2)
        return f'{erro:.6g} ({erro * 100:.2f}%)'


def exportar_sequencia(destino, resultados):
    """Salva os decimais completos em CSV, inclusive os erros de cada etapa."""
    truncamento, arredondamento = resultados
    with open(destino, 'w', encoding='utf-8-sig', newline='') as arquivo:
        escritor = csv.writer(arquivo, delimiter=';')
        escritor.writerow([
            'termo', 'referencia', 'truncamento', 'erro_abs_truncamento',
            'erro_rel_truncamento', 'arredondamento', 'erro_abs_arredondamento',
            'erro_rel_arredondamento',
        ])
        for passo_t, passo_a in zip(truncamento['passos'], arredondamento['passos']):
            erro_t = passo_t['erro_relativo']
            erro_a = passo_a['erro_relativo']
            escritor.writerow([
                passo_t['indice'], passo_t['exato'], passo_t['aproximado'],
                passo_t['erro_absoluto'], 'indefinido' if erro_t is None else erro_t,
                passo_a['aproximado'], passo_a['erro_absoluto'],
                'indefinido' if erro_a is None else erro_a,
            ])
