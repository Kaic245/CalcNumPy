# -*- coding: utf-8 -*-
"""
=====================================================================
ENTRADA E SAÍDA — leitura do que o usuário digita e texto dos números
Cálculo Numérico • Univasf • Projeto Unidade 1 (Erros)
=====================================================================

Funções de APOIO ao motor (`motor_calculo.py`). Não fazem nenhuma conta do
simulador; só:

    * interpretar_numero()     lê o texto digitado e valida (vírgula, limites...)
    * formatar() e variantes   escrevem Decimals de forma limpa ("0.00004",
                               nunca "4E-5" nem ruído de float)
    * notacao_normalizada()    escreve ±0.d1d2...dn × 10^e (item 3.2 do enunciado)

Também não usa Streamlit: pode ser testado no terminal.
"""

import re
from decimal import Decimal, ROUND_HALF_UP

from motor_calculo import (CTX_EXATO, MAX_DIGITOS_ENTRADA, MAX_EXPOENTE_ENTRADA,
                           ErroSimulador, criar_contexto, normalizar)


# =====================================================================
# ENTRADA: converter o texto digitado em Decimal
# =====================================================================

# Aceita: 12  -12  +12  12.  .5  12.5  1e-5  1.5E+3   (a vírgula é trocada por
# ponto ANTES deste teste). Rejeita letras, NaN, Infinity, "1_000" e dígitos
# não-ASCII (como os árabes), que o Decimal aceitaria sem avisar.
PADRAO_NUMERO = re.compile(r"[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]{1,4})?")


def interpretar_numero(texto, nome):
    """Converte o texto digitado em Decimal, com validação e mensagens claras.

    Aceita ponto OU vírgula como separador decimal e notação científica
    (ex.: 1.5e-3). Lança ErroSimulador se o texto não for um número aceitável.
    O número é lido DIRETAMENTE do texto (Decimal), então nenhum dígito se perde.
    """
    if texto is None or not str(texto).strip():
        raise ErroSimulador(f"O campo {nome} está vazio. Digite um número, por exemplo 0.76545.")

    # strip() remove espaços nas pontas (inclusive o espaço sem quebra que alguns
    # teclados de celular inserem). O sinal de menos "bonito" (−) vira hífen (-).
    t = str(texto).strip().replace("\u2212", "-")
    if any(caractere.isspace() for caractere in t):
        # Espaço no meio provavelmente é erro de digitação ("0,76 545"): melhor
        # avisar do que juntar os dígitos em silêncio e calcular outra coisa.
        raise ErroSimulador(f"Há um espaço no meio do número em {nome}. "
                            f"Digite sem espaços, por exemplo 0.76545.")

    if "," in t and "." in t:
        raise ErroSimulador(
            f"Em {nome}, use só um separador decimal (vírgula OU ponto) e não use "
            f"separador de milhar. Exemplo: 1234.56 ou 1234,56."
        )
    if t.count(",") > 1:
        raise ErroSimulador(f"Em {nome}, há mais de uma vírgula. Exemplo correto: 0,76545.")
    t = t.replace(",", ".")

    if not PADRAO_NUMERO.fullmatch(t):
        raise ErroSimulador(
            f"“{texto}” não é um número válido em {nome}. "
            f"Use algo como 0.76545, 0,76545, -12.5 ou 1.5e-3."
        )

    valor = Decimal(t)

    if valor != 0:
        n_digitos = len(valor.normalize(CTX_EXATO).as_tuple().digits)
        if n_digitos > MAX_DIGITOS_ENTRADA:
            raise ErroSimulador(f"O valor de {nome} tem {n_digitos} dígitos significativos; "
                                f"o máximo aceito é {MAX_DIGITOS_ENTRADA}.")
        if not (-MAX_EXPOENTE_ENTRADA <= valor.adjusted() <= MAX_EXPOENTE_ENTRADA):
            raise ErroSimulador(f"O valor de {nome} está fora da faixa aceita "
                                f"(use 0 ou valores entre 1e-{MAX_EXPOENTE_ENTRADA} e 1e{MAX_EXPOENTE_ENTRADA}).")
    return valor


# =====================================================================
# SAÍDA: escrever os números de forma legível
# =====================================================================

_SOBRESCRITO = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def sobrescrito(inteiro):
    """3 -> '³', -5 -> '⁻⁵' (para escrever 10³, 10⁻⁵ sem LaTeX)."""
    return str(inteiro).translate(_SOBRESCRITO)


def formatar(valor, sig_max=40):
    """Texto limpo para um Decimal (nunca '2E-20' nem ruído de float).

    - Faixa comum: notação posicional (0.00004, 5.6786, 12345.6).
    - Muito grande/pequeno: forma científica (4 × 10⁻⁷).
    - Se houver mais de `sig_max` dígitos significativos, mostra só os primeiros
      (TRUNCADOS, sem arredondar) e termina com '…' para avisar que continua.
    """
    if valor is None:
        return "indefinido"
    if valor == 0:
        return "0"
    # normalize() tira os zeros à direita; passamos o contexto para NÃO perder dígitos.
    sinal, digitos, expoente = valor.normalize(CTX_EXATO).as_tuple()
    texto = "".join(str(d) for d in digitos)

    cortado = len(texto) > sig_max
    if cortado:
        expoente += len(texto) - sig_max
        texto = texto[:sig_max]

    exp_cientifico = expoente + len(texto) - 1       # expoente na forma d.ddd × 10^e
    if -6 <= exp_cientifico <= 14:                   # notação posicional
        if expoente >= 0:
            corpo = texto + "0" * expoente
        else:
            casas = -expoente
            if len(texto) > casas:
                corpo = texto[:-casas] + "." + texto[-casas:]
            else:
                corpo = "0." + "0" * (casas - len(texto)) + texto
    else:                                            # notação científica
        mantissa = texto[0] + ("." + texto[1:] if len(texto) > 1 else "")
        corpo = f"{mantissa} × 10{sobrescrito(exp_cientifico)}"
    return ("-" if sinal else "") + corpo + ("…" if cortado else "")


def formatar_aprox(valor, sig=6):
    """Como `formatar`, mas ARREDONDA para `sig` dígitos e marca com '≈' quando
    houve arredondamento. Usado para erros com muitas casas (ex.: Er de 1/3)."""
    if valor is None:
        return "indefinido"
    if valor == 0:
        return "0"
    arred = criar_contexto(sig, ROUND_HALF_UP).create_decimal(valor)
    prefixo = "" if arred == valor else "≈ "
    return prefixo + formatar(arred, sig_max=sig)


def formatar_percentual(er):
    """Er como porcentagem (ex.: 0.6 -> '60%'); '≈' quando arredondado."""
    if er is None:
        return "indefinido"
    return formatar_aprox(CTX_EXATO.multiply(er, Decimal(100)), 4) + "%"


def notacao_normalizada(valor, n=None, sig_max=30):
    """Escreve o valor na forma normalizada  ±0.d₁d₂…dₙ × 10ᵉ  (item 3.2).

    Usa `normalizar()` do motor. Exemplo: 123.45 -> '0.12345 × 10³'.
    Se `n` for informado, completa a mantissa com zeros até n dígitos
    (ex.: 0.0001 com n=4 -> '0.1000 × 10⁻³'), mostrando os n dígitos da máquina.
    Funciona também quando o ajuste "estoura" a mantissa (0.99996 -> 1.000):
    como a notação é calculada a partir do valor final, vira 0.1000 × 10¹.
    """
    if valor is None:
        return "—"
    if valor == 0:
        return "0"
    sinal, mantissa, expoente = normalizar(valor)
    texto = "".join(str(d) for d in mantissa.normalize(CTX_EXATO).as_tuple().digits)
    if n and len(texto) < n:
        texto = texto.ljust(n, "0")
    if len(texto) > sig_max:
        texto = texto[:sig_max] + "…"
    return f"{'-' if sinal < 0 else ''}0.{texto} × 10{sobrescrito(expoente)}"
