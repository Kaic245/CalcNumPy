# -*- coding: utf-8 -*-
"""
=====================================================================
SIMULADOR DE PROPAGAÇÃO DE ERROS NUMÉRICOS
Disciplina de Cálculo Numérico - Univasf - Projeto Unidade 1 (Erros)
=====================================================================

Como executar
-------------
    pip install streamlit          (o pandas já vem junto com o Streamlit)
    streamlit run app.py

Mapa do arquivo (para você se achar depois)
-------------------------------------------
    1. CONFIGURAÇÕES E CONSTANTES      -> limites, rótulos, contextos Decimal
    2. MOTOR MATEMÁTICO                -> leitura de números, ajuste de precisão,
                                          operações, erros Ea/Er, soma sequencial
    3. FORMATAÇÃO DE NÚMEROS           -> texto bonito (sem "5.99999e-05"), notação
                                          normalizada 0.d1d2...dn x 10^e
    4. ESTADO DA SESSÃO E CALLBACKS    -> valores padrão, "novo cálculo", "sair"
    5. COMPONENTES DE INTERFACE        -> tabelas, resultado, alertas, histórico
    6. PÁGINA PRINCIPAL                -> abas: Calculadora livre / Demonstração / Ajuda

Decisões de projeto importantes
-------------------------------
* TODO o motor usa `decimal.Decimal` (base 10), e NÃO o `float` do Python.
  Motivo: a "máquina hipotética" do enunciado é decimal (0.7655 x 10^0,
  0.12345 x 10^3 ...), mas o `float` é binário e não guarda 0.7655 nem 28.4 de
  forma exata. Isso fazia o código antigo errar dígitos (ex.: 28.4 virava 28.39
  no truncamento com n=4). O usuário continua digitando "números em ponto
  flutuante" (com ponto decimal), como pede o item 3.1 do enunciado; só a
  representação interna é que é decimal. O "valor exato" também é calculado em
  Decimal com 400 dígitos ("precisão máxima da linguagem", item 3.3).
* Dois jeitos de contar o "n" (o enunciado usa os dois):
    - "significativos": n dígitos significativos, forma normalizada
      0.d1d2...dn x 10^e (item 3.2 do enunciado);
    - "decimais": n casas depois do ponto (é o que o Exemplo 3 do PDF faz:
      1.13572 -> 1.1357).
* Dois jeitos de aplicar o ajuste:
    - "resultado": opera com os valores exatos e ajusta só o resultado (item 3.2);
    - "entradas": a máquina guarda X e Y com n dígitos ANTES de operar e ajusta
      de novo o resultado (é o que o Exemplo 2 do PDF faz).
"""

import re
from decimal import Context, Decimal, ROUND_DOWN, ROUND_HALF_UP, getcontext

import pandas as pd
import streamlit as st

# O set_page_config precisa ser o PRIMEIRO comando do Streamlit no script.
st.set_page_config(page_title="Simulador de Erros Numéricos", page_icon="🧮", layout="wide")


# =====================================================================
# 1. CONFIGURAÇÕES E CONSTANTES
# =====================================================================

# Precisão (nº de dígitos) usada para o cálculo "exato". Com as entradas
# limitadas abaixo, somas, subtrações e multiplicações saem realmente exatas;
# divisões são calculadas com 400 dígitos (na prática, "precisão máxima").
PRECISAO_EXATA = 400
LIMITE_EXP_CONTEXTO = 999999        # faixa de expoentes aceita pelos contextos Decimal

# Limites para o que o usuário pode digitar (evita números absurdos/travamentos).
MAX_DIGITOS_ENTRADA = 50            # dígitos significativos digitados
MAX_EXPOENTE_ENTRADA = 100          # |valor| entre 1e-100 e 1e+100 (ou zero)
N_MIN, N_MAX = 1, 30                # faixa permitida para "n"
MAX_LINHAS_HISTORICO = 50           # tamanho máximo do histórico da sessão

# O contexto Decimal é "por thread" e o Streamlit roda cada sessão em uma thread
# própria. Como este trecho roda a cada execução do script, garantimos aqui que
# qualquer operação Decimal "solta" também use a precisão alta. (Mesmo assim, o
# motor abaixo usa contextos explícitos sempre que a precisão importa.)
getcontext().prec = PRECISAO_EXATA
getcontext().Emax = LIMITE_EXP_CONTEXTO
getcontext().Emin = -LIMITE_EXP_CONTEXTO

# Método de ajuste -> modo de arredondamento do Decimal.
#  - truncamento   : ROUND_DOWN    (corta os dígitos extras, em direção ao zero)
#  - arredondamento: ROUND_HALF_UP (clássico: 5 ou mais sobe; evita o
#                    "arredondamento do banqueiro" que o round() do Python usa)
MODO_DECIMAL = {"truncamento": ROUND_DOWN, "arredondamento": ROUND_HALF_UP}

# Rótulos mostrados na interface (as chaves são os valores usados no código).
OPERACOES = {"+": "+  (soma)", "-": "-  (subtração)", "*": "*  (multiplicação)", "/": "/  (divisão)"}
SIMBOLOS = {"+": "+", "-": "−", "*": "×", "/": "÷"}   # só para exibição
METODOS = {
    "truncamento": "Truncamento (corta os dígitos extras)",
    "arredondamento": "Arredondamento (5 ou mais sobe)",
}
TIPOS_AJUSTE = {
    "significativos": "Dígitos significativos (forma 0.d₁d₂…dₙ × 10ᵉ) — item 3.2 do enunciado",
    "decimais": "Casas decimais (n dígitos depois do ponto) — como no Exemplo 3 do PDF",
}
MODOS_CALCULO = {
    "entradas": "Armazenar X e Y com n dígitos, operar e ajustar o resultado (máquina hipotética — Exemplo 2)",
    "resultado": "Operar com os valores exatos e ajustar só o resultado (item 3.2 do enunciado)",
}
TIPO_CURTO = {"significativos": "dígitos significativos", "decimais": "casas decimais"}
MODO_CURTO = {"entradas": "entradas + resultado", "resultado": "só o resultado"}


# =====================================================================
# 2. MOTOR MATEMÁTICO
# =====================================================================

class ErroSimulador(ValueError):
    """Erro 'esperado' (entrada inválida, divisão por zero...) com mensagem
    amigável, pronta para ser mostrada ao usuário."""


def criar_contexto(precisao=PRECISAO_EXATA, arredondamento=ROUND_HALF_UP):
    """Cria um contexto Decimal com precisão e modo de arredondamento escolhidos."""
    return Context(prec=precisao, rounding=arredondamento,
                   Emin=-LIMITE_EXP_CONTEXTO, Emax=LIMITE_EXP_CONTEXTO)


# Contexto de "precisão máxima": usado para o valor exato, operações da máquina
# e cálculo dos erros. IMPORTANTE: operações "soltas" como abs(d), -d ou
# d.normalize() arredondariam para o contexto padrão (28 dígitos). Por isso
# usamos sempre os métodos do contexto (CTX_EXATO.add...) ou copy_abs().
CTX_EXATO = criar_contexto()

# Aceita: 12  -12  +12  12.  .5  12.5  1e-5  1.5E+3   (vírgula é trocada por ponto
# antes do teste). Nada de letras, NaN, Infinity, "1_000" ou dígitos não-ASCII.
PADRAO_NUMERO = re.compile(r"[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]{1,4})?")


def interpretar_numero(texto, nome):
    """Converte o texto digitado em Decimal, com validação e mensagens claras.

    Aceita ponto OU vírgula como separador decimal e notação científica
    (ex.: 1.5e-3). Lança ErroSimulador se o texto não for um número aceitável.
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

    valor = Decimal(t)    # leitura direta do texto: nenhum dígito é perdido

    if valor != 0:
        n_digitos = len(valor.normalize(CTX_EXATO).as_tuple().digits)
        if n_digitos > MAX_DIGITOS_ENTRADA:
            raise ErroSimulador(f"O valor de {nome} tem {n_digitos} dígitos significativos; "
                                f"o máximo aceito é {MAX_DIGITOS_ENTRADA}.")
        if not (-MAX_EXPOENTE_ENTRADA <= valor.adjusted() <= MAX_EXPOENTE_ENTRADA):
            raise ErroSimulador(f"O valor de {nome} está fora da faixa aceita "
                                f"(use 0 ou valores entre 1e-{MAX_EXPOENTE_ENTRADA} e 1e{MAX_EXPOENTE_ENTRADA}).")
    return valor


def ajustar_precisao(valor, n, metodo, tipo):
    """Simula o armazenamento de `valor` na máquina hipotética.

    metodo: "truncamento" (corta) ou "arredondamento" (round half up).
    tipo:
      - "significativos": mantém n dígitos significativos. Equivale a normalizar
        para 0.d1d2...dn x 10^e e cortar/arredondar a mantissa em n dígitos.
        Exemplo (n=4): 123.45 = 0.12345 x 10^3 -> 0.1234 x 10^3 = 123.4 (trunc.)
                                              ou 0.1235 x 10^3 = 123.5 (arred.)
      - "decimais": mantém n casas depois do ponto (ex.: n=4, 1.13572 -> 1.1357).

    Tudo é feito em Decimal, então não há erro de representação binária.
    """
    if metodo not in MODO_DECIMAL:
        raise ErroSimulador(f"Método de ajuste desconhecido: {metodo}")
    if not (N_MIN <= n <= N_MAX):
        raise ErroSimulador(f"n deve estar entre {N_MIN} e {N_MAX}.")
    if valor == 0:
        return Decimal(0)

    modo = MODO_DECIMAL[metodo]
    if tipo == "significativos":
        # Um contexto com prec=n e o modo de arredondamento escolhido faz
        # exatamente "manter n dígitos significativos".
        return criar_contexto(n, modo).create_decimal(valor)
    if tipo == "decimais":
        # quantize(10^-n) mantém exatamente n casas depois do ponto.
        ctx = criar_contexto(PRECISAO_EXATA, modo)
        casa = Decimal(1).scaleb(-n, ctx)            # 10^-n
        return valor.quantize(casa, rounding=modo, context=ctx)
    raise ErroSimulador(f"Tipo de ajuste desconhecido: {tipo}")


def operar(x, y, op):
    """Executa a operação aritmética em precisão máxima (sem arredondar)."""
    if op == "+":
        return CTX_EXATO.add(x, y)
    if op == "-":
        return CTX_EXATO.subtract(x, y)
    if op == "*":
        return CTX_EXATO.multiply(x, y)
    if op == "/":
        return CTX_EXATO.divide(x, y)
    raise ErroSimulador(f"Operação desconhecida: {op}")


def erro_absoluto(exato, aprox):
    """Ea = |valor exato - valor aproximado|."""
    return CTX_EXATO.subtract(exato, aprox).copy_abs()


def erro_relativo(ea, aprox):
    """Er = Ea / |valor aproximado|  (definição do enunciado).

    - aproximado != 0 -> Ea / |aprox|.
    - aproximado == 0 e Ea == 0 -> 0 (nada a medir: o resultado é exato).
    - aproximado == 0 e Ea != 0 -> None (indefinido: o enunciado só define Er
      quando o valor aproximado é diferente de zero).
    """
    if aprox == 0:
        return Decimal(0) if ea == 0 else None
    return CTX_EXATO.divide(ea, aprox.copy_abs())


def simular_operacao(x, y, op, n, metodo, tipo, armazenar_entradas):
    """Executa uma operação completa na máquina hipotética e devolve um dicionário.

    Passos:
      1. valor exato = x op y em precisão máxima;
      2. (se armazenar_entradas) X e Y são guardados com n dígitos e a operação
         é refeita com esses valores;
      3. o valor resultante é normalizado e ajustado para n dígitos;
      4. calculam-se Ea e Er.
    """
    if op == "/" and y == 0:
        raise ErroSimulador("Divisão por zero: o divisor (Y) não pode ser 0.")

    exato = operar(x, y, op)

    if armazenar_entradas:
        x_maq = ajustar_precisao(x, n, metodo, tipo)
        y_maq = ajustar_precisao(y, n, metodo, tipo)
        if op == "/" and y_maq == 0:
            raise ErroSimulador(
                f"Ao armazenar Y com n = {n} ({TIPO_CURTO[tipo]}), o valor virou 0 na máquina "
                f"e a divisão ficou impossível. Aumente n ou escolha outro Y."
            )
        bruto = operar(x_maq, y_maq, op)    # resultado com os valores da máquina
    else:
        x_maq = y_maq = None
        bruto = exato                        # item 3.2: ajusta só o resultado

    aprox = ajustar_precisao(bruto, n, metodo, tipo)
    ea = erro_absoluto(exato, aprox)
    er = erro_relativo(ea, aprox)
    return {"x": x, "y": y, "op": op, "n": n, "metodo": metodo, "tipo": tipo,
            "armazenar": armazenar_entradas, "exato": exato, "x_maq": x_maq,
            "y_maq": y_maq, "bruto": bruto, "aprox": aprox, "ea": ea, "er": er}


def simular_operacao_sequencial(valor_base, termo, op, quantidade, n, metodo, tipo, armazenar_operandos):
    """Executa `op` com `termo` repetidamente `quantidade` vezes a partir de `valor_base`.

    Exemplo (+, termo=p, base=None): soma termo quantidade vezes (Exemplo 3).
    A cada iteração, calcula a operação exata acumulada e a operação da máquina com n dígitos.
    """
    v_base = termo if valor_base is None else valor_base
    termo_usado = ajustar_precisao(termo, n, metodo, tipo) if armazenar_operandos else termo
    acumulado = ajustar_precisao(v_base, n, metodo, tipo) if armazenar_operandos else v_base
    exato_acumulado = v_base

    passos = []
    inicio_k = 2 if valor_base is None else 1
    total_iteracoes = quantidade if valor_base is None else quantidade

    for k in range(inicio_k, total_iteracoes + 1):
        passo_num = k - 1 if valor_base is None else k

        if op == "/" and termo_usado == 0:
            raise ErroSimulador("Divisão por zero: o termo repetido virou 0 na máquina.")

        exato_acumulado = operar(exato_acumulado, termo, op)
        bruto = operar(acumulado, termo_usado, op)
        novo = ajustar_precisao(bruto, n, metodo, tipo)
        passos.append({
            "passo": passo_num,
            "anterior": acumulado,
            "termo": termo_usado,
            "op": op,
            "bruto": bruto,
            "apos": novo,
            "exato_parcial": exato_acumulado,
            "erro": erro_absoluto(exato_acumulado, novo)
        })
        acumulado = novo

    ea = erro_absoluto(exato_acumulado, acumulado)
    return {
        "passos": passos,
        "exato": exato_acumulado,
        "final": acumulado,
        "ea": ea,
        "er": erro_relativo(ea, acumulado),
        "termo_usado": termo_usado,
        "base_usada": v_base,
        "op": op,
        "quantidade": quantidade,
        "n": n,
        "metodo": metodo,
        "tipo": tipo,
        "armazenar": armazenar_operandos,
        "tipo_resultado": "sequencial"
    }


def simular_soma_sequencial(parcela, quantidade, n, metodo, tipo, armazenar_parcela):
    """Compatibilidade com o Exemplo 3 do PDF: soma `parcela` `quantidade` vezes."""
    res = simular_operacao_sequencial(None, parcela, "+", quantidade, n, metodo, tipo, armazenar_parcela)
    # Compatibilidade de chaves para código existente do Exemplo 3
    for p in res["passos"]:
        p["soma_anterior"] = p["anterior"]
        p["parcela"] = p["termo"]
    res["p_usada"] = res["termo_usado"]
    return res


def digitos_perdidos_por_cancelamento(r):
    """Detecta cancelamento subtrativo e devolve quantas ordens de grandeza o
    resultado ficou menor que os operandos (0 = não houve cancelamento).

    Só vale para soma/subtração: se |exato| for pelo menos 100 vezes menor que o
    maior operando, os primeiros dígitos se anularam.
    """
    if r["op"] not in ("+", "-") or r["exato"] == 0:
        return 0
    maior = max(r["x"].copy_abs(), r["y"].copy_abs())
    if CTX_EXATO.multiply(r["exato"].copy_abs(), Decimal(100)) <= maior:
        return maior.adjusted() - r["exato"].adjusted()
    return 0


# =====================================================================
# 3. FORMATAÇÃO DE NÚMEROS
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

    Exemplo: 123.45 -> '0.12345 × 10³'.  A mantissa fica sempre em [0.1, 1).
    Se `n` for informado, completa a mantissa com zeros até n dígitos
    (ex.: 0.0001 com n=4 -> '0.1000 × 10⁻³'), mostrando os n dígitos da máquina.
    Funciona também quando o ajuste "estoura" a mantissa (0.99996 -> 1.000):
    como a notação é calculada a partir do valor final, vira 0.1000 × 10¹.
    """
    if valor is None:
        return "—"
    if valor == 0:
        return "0"
    sinal, digitos, _ = valor.normalize(CTX_EXATO).as_tuple()
    texto = "".join(str(d) for d in digitos)
    expoente = valor.adjusted() + 1                   # 0.d1d2... × 10^(adjusted+1)
    if n and len(texto) < n:
        texto = texto.ljust(n, "0")
    if len(texto) > sig_max:
        texto = texto[:sig_max] + "…"
    return f"{'-' if sinal else ''}0.{texto} × 10{sobrescrito(expoente)}"


# =====================================================================
# 4. ESTADO DA SESSÃO E CALLBACKS
# =====================================================================
# O Streamlit reexecuta o script inteiro a cada interação. Tudo que precisa
# "sobreviver" (valores digitados, último resultado, histórico) fica em
# st.session_state. Cada visitante do site (QR code) tem a sua própria sessão.

PADROES_ESTADO = {
    # Modo da calculadora livre ("basica" ou "sequencial")
    "modo_calculadora": "basica",
    # Calculadora livre - Básica (padrão = Exemplo 2 do PDF)
    "x_txt": "0.76545", "op": "-", "y_txt": "0.76541", "n_dig": 4,
    "metodo": "arredondamento", "tipo_ajuste": "significativos", "modo_calc": "entradas",
    # Calculadora livre - Sequencial (repetição n vezes)
    "seq_modo_entrada": "parcela_pura",
    "seq_base_txt": "1.0",
    "seq_termo_txt": "0.56786",
    "seq_op": "+",
    "seq_qtd": 10,
    "seq_n_dig": 4,
    "seq_metodo": "truncamento",
    "seq_tipo_ajuste": "decimais",
    "seq_armazenar": False,
    # Resultado atual, histórico e controle de saída
    "resultado": None, "historico": [], "contador": 0, "encerrado": False,
    # Casos de demonstração (valores do PDF, mas editáveis)
    "d1_x": "0.12345", "d1_y": "0.54321", "d1_n": 4,
    "d2_x": "0.76545", "d2_y": "0.76541", "d2_n": 4,
    "d3_p": "0.56786", "d3_qtd": 10, "d3_n": 4, "d3_metodo": "truncamento",
    "d3_armazenar": False,
}
for _chave, _valor in PADROES_ESTADO.items():
    if _chave not in st.session_state:       # só define na primeira vez
        st.session_state[_chave] = _valor


def novo_calculo():
    """Callback do botão 'Novo cálculo': limpa os campos de valores e o resultado."""
    st.session_state["x_txt"] = ""
    st.session_state["y_txt"] = ""
    st.session_state["seq_base_txt"] = ""
    st.session_state["seq_termo_txt"] = ""
    st.session_state["resultado"] = None


def limpar_historico():
    """Callback do botão 'Limpar histórico'."""
    st.session_state["historico"] = []


def sair():
    """Callback do botão 'Sair': mostra a tela de despedida."""
    st.session_state["encerrado"] = True


def voltar():
    """Callback do botão 'Voltar ao simulador' (na tela de despedida)."""
    st.session_state["encerrado"] = False


def enviar_para_calculadora(x_txt, op, y_txt, n, metodo, tipo, modo):
    """Callback dos botões 'Enviar para a calculadora livre' (aba de demonstração):
    copia os valores do exemplo para os campos da calculadora."""
    novos = {"modo_calculadora": "basica", "x_txt": x_txt, "op": op, "y_txt": y_txt,
             "n_dig": int(n), "metodo": metodo, "tipo_ajuste": tipo, "modo_calc": modo,
             "resultado": None}
    for chave, valor in novos.items():
        st.session_state[chave] = valor
    st.session_state["aviso_envio"] = (
        "Valores enviados! Abra a aba **🧮 Calculadora livre** e clique em **Calcular**."
    )


def registrar_historico(r):
    """Guarda o cálculo no histórico da sessão (só textos, bem leve)."""
    st.session_state["contador"] += 1
    if r.get("tipo_resultado") == "sequencial":
        if r.get("base_usada") == r.get("termo_usado") and r["op"] == "+":
            desc_op = f"Repetir {formatar(r['termo_usado'], 15)} {r['quantidade']}× (+)"
        else:
            desc_op = f"{formatar(r['base_usada'], 12)} {SIMBOLOS[r['op']]} {formatar(r['termo_usado'], 12)} ({r['quantidade']}×)"
        linha = {
            "#": st.session_state["contador"],
            "Operação": desc_op,
            "n": r["n"],
            "Método": r["metodo"],
            "Ajuste": TIPO_CURTO[r["tipo"]],
            "Modo": "sequencial (" + ("operandos na máquina" if r["armazenar"] else "só resultados") + ")",
            "Valor exato": formatar(r["exato"], 20),
            "Valor aproximado": formatar(r["final"], 20),
            "Ea": formatar_aprox(r["ea"], 6),
            "Er": formatar_percentual(r["er"]),
        }
    else:
        linha = {
            "#": st.session_state["contador"],
            "Operação": f"{formatar(r['x'], 20)} {SIMBOLOS[r['op']]} {formatar(r['y'], 20)}",
            "n": r["n"],
            "Método": r["metodo"],
            "Ajuste": TIPO_CURTO[r["tipo"]],
            "Modo": MODO_CURTO["entradas" if r["armazenar"] else "resultado"],
            "Valor exato": formatar(r["exato"], 20),
            "Valor aproximado": formatar(r["aprox"], 20),
            "Ea": formatar_aprox(r["ea"], 6),
            "Er": formatar_percentual(r["er"]),
        }
    st.session_state["historico"] = (st.session_state["historico"] + [linha])[-MAX_LINHAS_HISTORICO:]


# =====================================================================
# 5. COMPONENTES DE INTERFACE
# =====================================================================

def mostrar_tabela(linhas):
    """Mostra uma lista de dicionários como tabela estática.
    A primeira coluna vira o cabeçalho das linhas (fica mais legível)."""
    if not linhas:
        return
    tabela = pd.DataFrame(linhas)
    st.table(tabela.set_index(tabela.columns[0]))


def gerar_alertas(r, rotulo=""):
    """Avisos didáticos sobre o resultado: anulação e cancelamento subtrativo.
    Devolve lista de (tipo, mensagem), onde tipo é 'error' ou 'warning'."""
    prefixo = f"**{rotulo}:** " if rotulo else ""
    alertas = []
    if r["aprox"] == 0 and r["exato"] != 0:
        alertas.append((
            "error",
            prefixo + "o valor aproximado virou **0**: a operação foi **anulada** pela precisão "
                      "limitada (perda total de dígitos significativos). O erro relativo fica "
                      "**indefinido**, pois o enunciado só o define quando o valor aproximado é ≠ 0."
        ))
    perdidos = digitos_perdidos_por_cancelamento(r)
    if perdidos:
        alertas.append((
            "warning",
            prefixo + f"**cancelamento subtrativo:** o resultado é cerca de {perdidos} ordens de "
                      f"grandeza menor que os operandos. Os primeiros dígitos (iguais) se anulam e "
                      f"sobram só os últimos — justamente os mais afetados pelo armazenamento com "
                      f"n dígitos."
        ))
    return alertas


def exibir_alertas(alertas):
    """Mostra os alertas gerados por gerar_alertas()."""
    for tipo, mensagem in alertas:
        if tipo == "error":
            st.error(mensagem)
        else:
            st.warning(mensagem)


def leitura_do_resultado(r):
    """Frase curta interpretando Ea e Er (objetivo: 'calcular e interpretar')."""
    if r["er"] is None:
        return "O valor aproximado é 0, então o erro relativo não está definido."
    if r["ea"] == 0:
        return (f"O valor exato cabe em n = {r['n']} ({TIPO_CURTO[r['tipo']]}); "
                f"a máquina o representa sem erro (Ea = 0).")
    return (f"O erro absoluto foi {formatar_aprox(r['ea'], 6)} e o erro relativo é da ordem de "
            f"10{sobrescrito(r['er'].adjusted())} ({formatar_percentual(r['er'])}).")


def montar_passo_a_passo(r):
    """Texto (markdown) com o caminho do cálculo, no mesmo roteiro do item 3.2."""
    simb, n = SIMBOLOS[r["op"]], r["n"]
    unidade = TIPO_CURTO[r["tipo"]]
    er_txt = "indefinido (aproximado = 0)" if r["er"] is None else formatar_aprox(r["er"], 8)
    linhas = [f"1. **Operação exata** (precisão máxima): "
              f"`{formatar(r['x'])} {simb} {formatar(r['y'])} = {formatar(r['exato'])}`"]
    if r["x_maq"] is not None:
        linhas.append(
            f"2. **Armazenamento das entradas** com n = {n} {unidade} ({r['metodo']}): "
            f"`X = {formatar(r['x'])}` → `{formatar(r['x_maq'])}` e "
            f"`Y = {formatar(r['y'])}` → `{formatar(r['y_maq'])}`. "
            f"Operação com os valores da máquina: "
            f"`{formatar(r['x_maq'])} {simb} {formatar(r['y_maq'])} = {formatar(r['bruto'])}`")
    else:
        linhas.append("2. **Armazenamento das entradas:** não se aplica neste modo — "
                      "só o resultado é ajustado (item 3.2 do enunciado).")
    linhas.append(f"3. **Normalização** do valor a ajustar: "
                  f"`{formatar(r['bruto'])}` = `{notacao_normalizada(r['bruto'])}`")
    n_pad = n if r["tipo"] == "significativos" else None
    linhas.append(f"4. **Ajuste** ({r['metodo']}) para n = {n} {unidade}: "
                  f"`{formatar(r['aprox'])}` = `{notacao_normalizada(r['aprox'], n_pad)}`")
    linhas.append(f"5. **Erros:** `Ea = |{formatar(r['exato'], 20)} − {formatar(r['aprox'])}| = "
                  f"{formatar_aprox(r['ea'], 8)}` e `Er = Ea / |aproximado| = {er_txt}`")
    return "\n".join(linhas)


def mostrar_resultado_sequencial(r):
    """Apresenta o resultado de uma operação sequencial na calculadora livre."""
    n = r["n"]
    n_pad = n if r["tipo"] == "significativos" else None

    st.success("✅ Operação sequencial concluída!")
    st.caption(
        f"Configuração usada: {r['quantidade']} repetições da operação {r['op']} · "
        f"n = {n} · {r['metodo']} · {TIPO_CURTO[r['tipo']]} · "
        f"{'operandos armazenados na máquina' if r['armazenar'] else 'apenas resultados intermediários ajustados'}"
    )

    # Métricas resumidas
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Valor exato final", formatar(r["exato"]))
    c2.metric("Valor aproximado final", formatar(r["final"]))
    c3.metric("Erro absoluto final (Ea)", formatar_aprox(r["ea"], 8))
    c4.metric("Erro relativo final (Er)", formatar_percentual(r["er"]))

    # Tabela comparativa padrão do projeto
    st.markdown("#### Resumo do resultado final")
    if r["er"] is None:
        er_valor, er_notacao = "indefinido (valor aproximado = 0)", "—"
    else:
        er_valor = f"{formatar_aprox(r['er'], 8)}  ({formatar_percentual(r['er'])})"
        er_notacao = notacao_normalizada(r["er"], sig_max=10)
    mostrar_tabela([
        {"Grandeza": "Valor exato final", "Valor": formatar(r["exato"]),
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": notacao_normalizada(r["exato"])},
        {"Grandeza": "Valor aproximado final", "Valor": formatar(r["final"]),
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": notacao_normalizada(r["final"], n_pad)},
        {"Grandeza": "Erro absoluto total Ea = |exato − aproximado|", "Valor": formatar_aprox(r["ea"], 10),
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": notacao_normalizada(r["ea"], sig_max=12)},
        {"Grandeza": "Erro relativo total Er = Ea / |aproximado|", "Valor": er_valor,
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": er_notacao},
    ])

    # Tabela detalhada passo a passo
    simb = SIMBOLOS[r["op"]]
    linhas = [{
        "Passo nº": p["passo"],
        "Operação": f"{formatar(p['anterior'])} {simb} {formatar(p['termo'])}",
        "Valor exato acumulado": formatar(p["exato_parcial"]),
        "Resultado exato do passo": formatar(p["bruto"]),
        "Após o ajuste (máquina)": formatar(p["apos"]),
        "Erro absoluto acumulado": formatar_aprox(p["erro"], 6),
    } for p in r["passos"]]

    st.markdown("#### Evolução passo a passo")
    mostrar_tabela(linhas)

    # Gráfico do acúmulo de erro
    if r["passos"]:
        grafico = pd.DataFrame({
            "Passo": [p["passo"] for p in r["passos"]],
            "Erro absoluto acumulado": [float(p["erro"]) for p in r["passos"]]
        })
        st.line_chart(grafico.set_index("Passo"))
        st.caption("Evolução da propagação do erro acumulado a cada iteração (gráfico ilustrativo).")


def mostrar_resultado(r):
    """Apresenta o resultado de um cálculo da calculadora livre (básica ou sequencial)."""
    if r.get("tipo_resultado") == "sequencial":
        mostrar_resultado_sequencial(r)
        return

    n = r["n"]
    n_pad = n if r["tipo"] == "significativos" else None

    st.success("✅ Cálculo realizado com sucesso!")
    st.caption(f"Configuração usada: n = {n} · {r['metodo']} · {TIPO_CURTO[r['tipo']]} · "
               f"{MODO_CURTO['entradas' if r['armazenar'] else 'resultado']}")

    # --- Os quatro resultados exigidos pelo item 3.3 do enunciado ---
    st.markdown("#### Resultados")
    if r["er"] is None:
        er_valor, er_notacao = "indefinido (valor aproximado = 0)", "—"
    else:
        er_valor = f"{formatar_aprox(r['er'], 8)}  ({formatar_percentual(r['er'])})"
        er_notacao = notacao_normalizada(r["er"], sig_max=10)
    mostrar_tabela([
        {"Grandeza": "Valor exato", "Valor": formatar(r["exato"]),
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": notacao_normalizada(r["exato"])},
        {"Grandeza": "Valor aproximado (simulador)", "Valor": formatar(r["aprox"]),
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": notacao_normalizada(r["aprox"], n_pad)},
        {"Grandeza": "Erro absoluto  Ea = |exato − aproximado|", "Valor": formatar_aprox(r["ea"], 10),
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": notacao_normalizada(r["ea"], sig_max=12)},
        {"Grandeza": "Erro relativo  Er = Ea / |aproximado|", "Valor": er_valor,
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": er_notacao},
    ])

    # --- Entradas (e como a máquina as guardou, se for o caso) ---
    linhas_entrada = [
        {"Entrada": "X digitado", "Valor": formatar(r["x"]), "Notação normalizada": notacao_normalizada(r["x"])},
        {"Entrada": "Y digitado", "Valor": formatar(r["y"]), "Notação normalizada": notacao_normalizada(r["y"])},
    ]
    if r["x_maq"] is not None:
        linhas_entrada += [
            {"Entrada": "X na máquina", "Valor": formatar(r["x_maq"]),
             "Notação normalizada": notacao_normalizada(r["x_maq"], n_pad)},
            {"Entrada": "Y na máquina", "Valor": formatar(r["y_maq"]),
             "Notação normalizada": notacao_normalizada(r["y_maq"], n_pad)},
        ]
    st.markdown("#### Entradas")
    mostrar_tabela(linhas_entrada)
    if r["x_maq"] is None:
        st.caption("Neste modo X e Y entram na operação sem ajuste; apenas o resultado é ajustado.")

    exibir_alertas(gerar_alertas(r))
    st.info("📖 " + leitura_do_resultado(r))

    with st.expander("🔍 Passo a passo do cálculo", expanded=True):
        st.markdown(montar_passo_a_passo(r))


def processar_calculo_sequencial():
    """Lê os campos da operação sequencial, valida e calcula."""
    erros = []
    termo = None
    base = None

    try:
        termo = interpretar_numero(st.session_state["seq_termo_txt"], "Termo repetido")
    except ErroSimulador as erro:
        erros.append(str(erro))

    if st.session_state["seq_modo_entrada"] == "base_e_termo":
        try:
            base = interpretar_numero(st.session_state["seq_base_txt"], "Valor inicial")
        except ErroSimulador as erro:
            erros.append(str(erro))
    else:
        base = None

    if erros:
        st.session_state["resultado"] = None
        for mensagem in erros:
            st.error("⚠️ " + mensagem)
        return

    try:
        r = simular_operacao_sequencial(
            valor_base=base,
            termo=termo,
            op=st.session_state["seq_op"],
            quantidade=int(st.session_state["seq_qtd"]),
            n=int(st.session_state["seq_n_dig"]),
            metodo=st.session_state["seq_metodo"],
            tipo=st.session_state["seq_tipo_ajuste"],
            armazenar_operandos=bool(st.session_state["seq_armazenar"])
        )
    except ErroSimulador as erro:
        st.session_state["resultado"] = None
        st.error("⚠️ " + str(erro))
        return
    except Exception as erro:
        st.session_state["resultado"] = None
        st.error(f"⚠️ Erro inesperado ({type(erro).__name__}). Confira os valores e tente de novo.")
        return

    st.session_state["resultado"] = r
    registrar_historico(r)


def mostrar_historico():
    """Tabela com os cálculos feitos nesta sessão (mais recente primeiro)."""
    historico = st.session_state["historico"]
    with st.expander(f"🕘 Histórico desta sessão ({len(historico)})"):
        if not historico:
            st.write("Nenhum cálculo ainda. Faça um cálculo e ele aparece aqui.")
            return
        tabela = pd.DataFrame(list(reversed(historico)))
        try:
            st.dataframe(tabela, hide_index=True)
        except TypeError:                 # versões antigas do Streamlit não têm hide_index
            st.dataframe(tabela)


def processar_calculo():
    """Lê os campos, valida, calcula e guarda o resultado na sessão.

    Valida X e Y juntos para mostrar todos os problemas de uma vez."""
    erros, x, y = [], None, None
    try:
        x = interpretar_numero(st.session_state["x_txt"], "X")
    except ErroSimulador as erro:
        erros.append(str(erro))
    try:
        y = interpretar_numero(st.session_state["y_txt"], "Y")
    except ErroSimulador as erro:
        erros.append(str(erro))
    if erros:
        st.session_state["resultado"] = None
        for mensagem in erros:
            st.error("⚠️ " + mensagem)
        return

    try:
        r = simular_operacao(
            x, y, st.session_state["op"], int(st.session_state["n_dig"]),
            st.session_state["metodo"], st.session_state["tipo_ajuste"],
            st.session_state["modo_calc"] == "entradas",
        )
    except ErroSimulador as erro:
        st.session_state["resultado"] = None
        st.error("⚠️ " + str(erro))
        return
    except Exception as erro:             # rede de segurança: nunca mostrar "traceback" ao público
        st.session_state["resultado"] = None
        st.error(f"⚠️ Erro inesperado ({type(erro).__name__}). Confira os valores e tente de novo.")
        return

    st.session_state["resultado"] = r
    registrar_historico(r)


# ---------------------------------------------------------------------
# Casos de demonstração (aba 2): cada exemplo usa o modo que o PDF pede.
# ---------------------------------------------------------------------

def explicar_ajuste(exato, n):
    """Explica, com os dígitos do valor exato, de onde vem a diferença entre
    truncamento e arredondamento (procedimento comum de testes, passo 4)."""
    if exato == 0:
        return "O valor exato é 0; não há o que ajustar."
    digitos = "".join(str(d) for d in exato.normalize(CTX_EXATO).as_tuple().digits)
    if len(digitos) <= n:
        return (f"O valor exato tem apenas {len(digitos)} dígito(s) significativo(s) (≤ n = {n}): "
                f"cabe inteiro na máquina, então truncamento e arredondamento coincidem e **Ea = 0**.")
    mantidos, descartado = digitos[:n], int(digitos[n])
    if descartado >= 5:
        regra_arred = "o dígito descartado é ≥ 5, então ele **soma 1** ao último dígito mantido"
    else:
        regra_arred = "o dígito descartado é < 5, então ele **mantém** os dígitos (igual ao truncamento)"
    return (f"Dígitos significativos do valor exato: `{digitos}`. Com n = {n}, a máquina guarda "
            f"`{mantidos}` e descarta o resto (primeiro dígito descartado: **{descartado}**).\n\n"
            f"- **Truncamento:** apenas corta os dígitos extras.\n"
            f"- **Arredondamento:** {regra_arred}.")


def demo_exemplo_1():
    """Exemplo 1: soma de dois números com 5 casas decimais, n = 4 (só o resultado é ajustado)."""
    with st.expander("Exemplo 1 — Operação simples (soma)"):
        st.write("Soma de dois números com 5 casas decimais, com n = 4 dígitos significativos. "
                 "Aqui só o **resultado** é ajustado (item 3.2). Os valores do PDF já estão "
                 "preenchidos, mas você pode editá-los e testar outros.")
        c1, c2, c3 = st.columns(3)
        c1.text_input("X", key="d1_x")
        c2.text_input("Y", key="d1_y")
        c3.number_input("n (dígitos significativos)", min_value=N_MIN, max_value=N_MAX, step=1, key="d1_n")
        try:
            x = interpretar_numero(st.session_state["d1_x"], "X")
            y = interpretar_numero(st.session_state["d1_y"], "Y")
        except ErroSimulador as erro:
            st.error("⚠️ " + str(erro))
            return
        n = int(st.session_state["d1_n"])

        resultados = {m: simular_operacao(x, y, "+", n, m, "significativos", False)
                      for m in ("truncamento", "arredondamento")}
        exato = resultados["truncamento"]["exato"]
        st.write(f"**Operação:** {formatar(x)} + {formatar(y)}  →  valor exato = "
                 f"`{formatar(exato)}` = `{notacao_normalizada(exato)}`")

        linhas = []
        for metodo, r in resultados.items():
            linhas.append({
                "Método": metodo.capitalize(),
                "Valor exato": formatar(r["exato"]),
                "Valor aproximado": formatar(r["aprox"]),
                "Notação normalizada": notacao_normalizada(r["aprox"], n),
                "Erro absoluto (Ea)": formatar_aprox(r["ea"], 10),
                "Erro relativo (Er)": formatar_aprox(r["er"], 8),
                "Er (%)": formatar_percentual(r["er"]),
            })
        mostrar_tabela(linhas)
        st.markdown(explicar_ajuste(exato, n))
        st.button("➡️ Enviar para a calculadora livre", key="d1_enviar",
                  on_click=enviar_para_calculadora,
                  args=(st.session_state["d1_x"], "+", st.session_state["d1_y"], n,
                        "truncamento", "significativos", "resultado"),
                  help="Pré-seleciona truncamento; troque o método lá se quiser comparar.")


def demo_exemplo_2():
    """Exemplo 2: cancelamento subtrativo (X e Y são armazenados com n dígitos antes de subtrair)."""
    with st.expander("Exemplo 2 — Propagação de erro e cancelamento subtrativo"):
        st.write("X e Y são guardados na máquina com n = 4 dígitos significativos **antes** da "
                 "subtração (como no PDF). Veja o que acontece com cada método — com truncamento "
                 "a subtração fica **nula**.")
        c1, c2, c3 = st.columns(3)
        c1.text_input("X", key="d2_x")
        c2.text_input("Y", key="d2_y")
        c3.number_input("n (dígitos significativos)", min_value=N_MIN, max_value=N_MAX, step=1, key="d2_n")
        try:
            x = interpretar_numero(st.session_state["d2_x"], "X")
            y = interpretar_numero(st.session_state["d2_y"], "Y")
        except ErroSimulador as erro:
            st.error("⚠️ " + str(erro))
            return
        n = int(st.session_state["d2_n"])

        resultados = {m: simular_operacao(x, y, "-", n, m, "significativos", True)
                      for m in ("arredondamento", "truncamento")}
        exato = resultados["arredondamento"]["exato"]
        st.write(f"**Valor exato:** {formatar(x)} − {formatar(y)} = `{formatar(exato)}` "
                 f"= `{notacao_normalizada(exato)}`")

        linhas = []
        for metodo, r in resultados.items():
            linhas.append({
                "Método": metodo.capitalize(),
                "X na máquina": formatar(r["x_maq"]),
                "Y na máquina": formatar(r["y_maq"]),
                "Resultado aproximado": formatar(r["aprox"]),
                "Notação normalizada": notacao_normalizada(r["aprox"], n),
                "Erro absoluto (Ea)": formatar_aprox(r["ea"], 10),
                "Erro relativo (Er)": formatar_aprox(r["er"], 8) if r["er"] is not None else "indefinido",
                "Er (%)": formatar_percentual(r["er"]),
            })
        mostrar_tabela(linhas)

        for metodo, r in resultados.items():
            exibir_alertas(gerar_alertas(r, metodo.capitalize()))
        st.markdown(
            "**Por que isso acontece?** X e Y são quase iguais; ao subtraí-los, os primeiros "
            "dígitos se anulam e sobram apenas os últimos — exatamente os que o armazenamento com "
            "n dígitos distorce (arredondamento) ou descarta (truncamento). O resultado, que "
            "deveria ser pequeno e preciso, fica com erro relativo enorme ou até zero."
        )
        st.button("➡️ Enviar para a calculadora livre", key="d2_enviar",
                  on_click=enviar_para_calculadora,
                  args=(st.session_state["d2_x"], "-", st.session_state["d2_y"], n,
                        "arredondamento", "significativos", "entradas"),
                  help="Pré-seleciona arredondamento (como na análise do PDF); troque lá para truncamento.")


def mostrar_soma_sequencial(r, qtd):
    """Resultado do Exemplo 3 para uma variante (casas decimais ou significativos)."""
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Valor exato", formatar(r["exato"]))
    c2.metric("Resultado aproximado final", formatar(r["final"]))
    c3.metric("Erro absoluto total (Ea)", formatar_aprox(r["ea"], 8))
    c4.metric("Erro relativo total (Er)", formatar_percentual(r["er"]))

    linhas = [{
        "Soma nº": p["passo"],
        "Operação": f"{formatar(p['soma_anterior'])} + {formatar(p['parcela'])}",
        "Soma exata do passo": formatar(p["bruto"]),
        "Após o ajuste": formatar(p["apos"]),
        "Valor exato acumulado": formatar(p["exato_parcial"]),
        "Erro acumulado": formatar_aprox(p["erro"], 6),
    } for p in r["passos"]]
    mostrar_tabela(linhas)

    # Gráfico só ilustrativo: float é usado APENAS para desenhar a curva.
    # Nenhum cálculo do simulador usa float.
    if r["passos"]:
        grafico = pd.DataFrame({"Soma nº": [p["passo"] for p in r["passos"]],
                                "Erro acumulado": [float(p["erro"]) for p in r["passos"]]})
        st.line_chart(grafico.set_index("Soma nº"))
        st.caption("Evolução do erro absoluto acumulado a cada soma (gráfico ilustrativo).")


def demo_exemplo_3():
    """Exemplo 3: somar uma parcela várias vezes ajustando a soma a cada passo."""
    with st.expander("Exemplo 3 — Propagação de erro em uma sequência de somas"):
        st.write("Somar 0.56786 dez vezes, ajustando a soma a cada passo. Os valores do PDF já "
                 "estão preenchidos; edite à vontade.")
        c1, c2, c3 = st.columns(3)
        c1.text_input("Parcela", key="d3_p")
        c2.number_input("Quantidade de termos", min_value=2, max_value=100, step=1, key="d3_qtd")
        c3.number_input("n (dígitos)", min_value=N_MIN, max_value=N_MAX, step=1, key="d3_n")
        c4, c5 = st.columns(2)
        c4.radio("Método de ajuste", list(METODOS), key="d3_metodo",
                 format_func=METODOS.get, horizontal=True)
        c5.checkbox("Guardar também a parcela com n dígitos antes de somar (variante “máquina real”)",
                    key="d3_armazenar")
        try:
            parcela = interpretar_numero(st.session_state["d3_p"], "Parcela")
        except ErroSimulador as erro:
            st.error("⚠️ " + str(erro))
            return
        qtd, n = int(st.session_state["d3_qtd"]), int(st.session_state["d3_n"])
        metodo, armazenar = st.session_state["d3_metodo"], bool(st.session_state["d3_armazenar"])

        st.info(
            "ℹ️ **Observação sobre o enunciado:** os passos do PDF (1.1357, 1.7035, 2.2713…) "
            "cortam em **4 casas decimais**, enquanto o item 3.2 define n como **dígitos "
            "significativos** (1.13572 → 1.135 com n = 4). Por isso as duas versões aparecem "
            "abaixo, lado a lado, para comparação."
        )
        aba_dec, aba_sig = st.tabs([f"{n} casas decimais (como no PDF)",
                                    f"{n} dígitos significativos (item 3.2)"])
        for aba, tipo in ((aba_dec, "decimais"), (aba_sig, "significativos")):
            with aba:
                r = simular_soma_sequencial(parcela, qtd, n, metodo, tipo, armazenar)
                mostrar_soma_sequencial(r, qtd)


# =====================================================================
# 6. PÁGINA PRINCIPAL
# =====================================================================

# --- Tela de despedida (botão "Sair") ---------------------------------
if st.session_state["encerrado"]:
    st.title("👋 Sessão encerrada")
    st.write("Obrigado por usar o Simulador de Propagação de Erros Numéricos! "
             "Você já pode fechar esta aba.")
    st.button("↩️ Voltar ao simulador", on_click=voltar)
    st.stop()          # interrompe o script aqui: nada abaixo é desenhado

st.title("🧮 Simulador de Propagação de Erros Numéricos")
st.caption("Cálculo Numérico • Univasf • Projeto Unidade 1 (Erros). Simula uma máquina que guarda "
           "só n dígitos e mostra como truncamento e arredondamento geram e propagam erros.")

aba_calc, aba_demo, aba_ajuda = st.tabs(
    ["🧮 Calculadora livre", "📋 Casos de demonstração (PDF)", "ℹ️ Ajuda e conceitos"])

# ---------------------------------------------------------------------
# ABA 1: CALCULADORA LIVRE
# ---------------------------------------------------------------------
with aba_calc:
    st.subheader("Calculadora de precisão limitada")

    modo_ui = st.radio(
        "Modo de cálculo:",
        ["Operação básica (X e Y)", "Operação sequencial repetida (n vezes)"],
        index=0 if st.session_state["modo_calculadora"] == "basica" else 1,
        horizontal=True,
        help="Escolha entre realizar uma operação direta entre dois números ou repetir uma operação sequencialmente (como no Exemplo 3 do PDF)."
    )
    st.session_state["modo_calculadora"] = "basica" if modo_ui == "Operação básica (X e Y)" else "sequencial"

    if st.session_state["modo_calculadora"] == "basica":
        st.write("Digite **X** e **Y** (ponto ou vírgula), escolha a operação, o número de dígitos **n** "
                 "e o método, e clique em **Calcular**.")

        with st.form("form_calculadora_basica"):
            col_x, col_op, col_y = st.columns([3, 2, 3])
            col_x.text_input("Valor de X", key="x_txt", placeholder="ex.: 0.76545",
                             help="Número com ponto ou vírgula decimal. Aceita notação científica, ex.: 1.5e-3.")
            col_op.selectbox("Operação", list(OPERACOES), key="op", format_func=OPERACOES.get)
            col_y.text_input("Valor de Y", key="y_txt", placeholder="ex.: 0.76541",
                             help="Mesmas regras do X. Na divisão, Y não pode ser 0.")

            col_n, col_m = st.columns([1, 2])
            col_n.number_input("Dígitos (n)", min_value=N_MIN, max_value=N_MAX, step=1, key="n_dig",
                               help="Quantos dígitos a máquina guarda (veja 'tipo de ajuste' nas opções avançadas).")
            col_m.radio("Método de ajuste", list(METODOS), key="metodo", format_func=METODOS.get)

            with st.expander("⚙️ Opções avançadas: tipo de ajuste e modo de cálculo "
                             "(padrão: dígitos significativos + entradas e resultado)"):
                st.radio("O que o “n” conta?", list(TIPOS_AJUSTE), key="tipo_ajuste",
                         format_func=TIPOS_AJUSTE.get)
                st.radio("O que é ajustado?", list(MODOS_CALCULO), key="modo_calc",
                         format_func=MODOS_CALCULO.get)

            calcular = st.form_submit_button("Calcular", type="primary")

        if calcular:
            processar_calculo()

    else:
        st.write("Realize uma operação repetida **k vezes** com ajuste a cada passo para observar o "
                 "acúmulo e propagação de erros numéricos.")

        with st.form("form_calculadora_sequencial"):
            col_m_ent = st.radio(
                "Estrutura da operação repetida:",
                ["Somar/operar o mesmo termo k vezes (ex.: 0.56786 dez vezes)",
                 "Partir de um valor inicial e aplicar a operação k vezes com o termo"],
                index=0 if st.session_state["seq_modo_entrada"] == "parcela_pura" else 1,
                horizontal=True
            )
            st.session_state["seq_modo_entrada"] = (
                "parcela_pura" if col_m_ent.startswith("Somar/operar") else "base_e_termo"
            )

            if st.session_state["seq_modo_entrada"] == "base_e_termo":
                col_b, col_op_s, col_t, col_q = st.columns([3, 2, 3, 2])
                col_b.text_input("Valor inicial", key="seq_base_txt", placeholder="ex.: 10.0",
                                 help="Valor a partir do qual a sequência de operações começará.")
            else:
                col_op_s, col_t, col_q = st.columns([2, 4, 2])

            col_op_s.selectbox("Operação", list(OPERACOES), key="seq_op", format_func=OPERACOES.get)
            col_t.text_input("Termo repetido", key="seq_termo_txt", placeholder="ex.: 0.56786",
                             help="Valor que será operado repetidamente a cada iteração.")
            col_q.number_input("Repetições (k)", min_value=2, max_value=100, step=1, key="seq_qtd",
                               help="Quantidade de termos ou vezes que a operação será executada.")

            col_n_s, col_m_s = st.columns([1, 2])
            col_n_s.number_input("Dígitos (n)", min_value=N_MIN, max_value=N_MAX, step=1, key="seq_n_dig",
                                 help="Quantos dígitos a máquina mantém.")
            col_m_s.radio("Método de ajuste", list(METODOS), key="seq_metodo", format_func=METODOS.get)

            with st.expander("⚙️ Opções avançadas para a operação sequencial"):
                st.radio("O que o “n” conta?", list(TIPOS_AJUSTE), key="seq_tipo_ajuste",
                         format_func=TIPOS_AJUSTE.get)
                st.checkbox("Guardar também o termo com n dígitos na máquina antes de operar",
                            key="seq_armazenar",
                            help="Se marcado, o termo é arredondado/truncado antes de entrar nas operações.")

            calcular_seq = st.form_submit_button("Calcular Operação Sequencial", type="primary")

        if calcular_seq:
            processar_calculo_sequencial()

    if st.session_state["resultado"] is not None:
        mostrar_resultado(st.session_state["resultado"])
    elif not (calcular if st.session_state["modo_calculadora"] == "basica" else calcular_seq):
        st.info("👆 Preencha os campos e clique em **Calcular** para ver o resultado.")

    # --- Ações: novo cálculo / limpar histórico / sair (instrução 4 do enunciado) ---
    b1, b2, b3 = st.columns(3)
    b1.button("🔄 Novo cálculo", on_click=novo_calculo, key="btn_novo",
              help="Limpa X, Y e o resultado para você digitar outro problema.")
    b2.button("🧹 Limpar histórico", on_click=limpar_historico, key="btn_limpar_hist")
    b3.button("🚪 Sair", on_click=sair, key="btn_sair", help="Encerra a sessão.")

    mostrar_historico()

# ---------------------------------------------------------------------
# ABA 2: CASOS DE DEMONSTRAÇÃO (valores do PDF, editáveis)
# ---------------------------------------------------------------------
with aba_demo:
    st.subheader("Exemplos do enunciado")
    st.write("Cada exemplo já vem com os valores do PDF e usa o modo de cálculo que o enunciado pede "
             "para ele. Você pode **editar os valores** para testar outros casos sem reiniciar.")
    aviso = st.session_state.pop("aviso_envio", None)
    if aviso:
        st.success(aviso)
    demo_exemplo_1()
    demo_exemplo_2()
    demo_exemplo_3()

# ---------------------------------------------------------------------
# ABA 3: AJUDA E CONCEITOS
# ---------------------------------------------------------------------
with aba_ajuda:
    st.subheader("Como usar")
    st.markdown(
        "- **Digite os números** com ponto ou vírgula (`0.76545` ou `0,76545`). Também vale "
        "notação científica (`1.5e-3`). Limites: até "
        f"{MAX_DIGITOS_ENTRADA} dígitos significativos e valores entre 1e-{MAX_EXPOENTE_ENTRADA} e "
        f"1e{MAX_EXPOENTE_ENTRADA} (ou 0).\n"
        "- Escolha **operação**, **n** e **método** e clique em **Calcular**.\n"
        "- **Novo cálculo** limpa os campos; o **histórico** guarda tudo que você calculou; "
        "**Sair** encerra a sessão."
    )

    st.subheader("Conceitos")
    st.markdown("**Notação normalizada:** todo número é escrito como 0.d₁d₂…dₙ × 10ᵉ, com d₁ ≠ 0. "
                "Exemplo: 123.45 = 0.12345 × 10³.")
    st.markdown("**Truncamento:** descarta os dígitos além do n-ésimo. "
                "**Arredondamento:** olha o primeiro dígito descartado; se for 5 ou mais, soma 1 "
                "ao último dígito mantido.")
    st.markdown("**Erros (definições do enunciado):**")
    st.latex(r"E_a = \left|\,\text{valor exato} - \text{valor aproximado}\,\right|")
    st.latex(r"E_r = \dfrac{E_a}{\left|\,\text{valor aproximado}\,\right|}")
    st.markdown("Se o valor aproximado for 0, o erro relativo é **indefinido** (a menos que Ea = 0, "
                "caso em que não há erro).")

    st.subheader("Opções avançadas")
    st.markdown(
        "- **O que o “n” conta?** *Dígitos significativos* (item 3.2 do enunciado) ou *casas "
        "decimais* (é o que os passos do Exemplo 3 do PDF fazem: 1.13572 → 1.1357).\n"
        "- **O que é ajustado?** *Só o resultado* (item 3.2: opera com os valores exatos e ajusta o "
        "resultado) ou *entradas e resultado* (a máquina guarda X e Y com n dígitos antes de operar, "
        "como no Exemplo 2). Os dois modos podem dar valores diferentes por causa do ajuste duplo."
    )

    st.subheader("Por que o cálculo usa Decimal?")
    st.markdown(
        "A máquina hipotética do enunciado trabalha em **base 10**. O `float` do Python trabalha em "
        "base 2 e não consegue guardar números como 0.7655 ou 28.4 exatamente, o que distorceria "
        "dígitos no truncamento e no arredondamento. Por isso o simulador lê o que você digita "
        "diretamente como número decimal (`decimal.Decimal`) e calcula o valor exato com 400 dígitos "
        "de precisão. Você continua informando “números em ponto flutuante” normalmente."
    )