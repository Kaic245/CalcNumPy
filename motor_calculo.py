from decimal import Context, Decimal, ROUND_DOWN, ROUND_HALF_UP


# =====================================================================
# 1. CONSTANTES E CONTEXTO DE PRECISÃO
# =====================================================================

PRECISAO_EXATA = 400
LIMITE_EXP_CONTEXTO = 999999        # faixa de expoentes aceita pelo Decimal

# Limites do que o usuário pode digitar
MAX_DIGITOS_ENTRADA = 50            # dígitos significativos
MAX_EXPOENTE_ENTRADA = 100          # |valor| entre 1e-100 e 1e+100 (ou zero)
N_MIN, N_MAX = 1, 30                # quantidade de dígitos "n" permitida

METODOS_VALIDOS = ("truncamento", "arredondamento")
TIPOS_VALIDOS = ("significativos", "decimais")

# Nome curto de cada "tipo de ajuste" (usado em mensagens e na interface).
TIPO_CURTO = {"significativos": "dígitos significativos", "decimais": "casas decimais"}


class ErroSimulador(ValueError):
    """Erro 'esperado' (entrada inválida, divisão por zero...), com mensagem
    amigável pronta para ser mostrada ao usuário."""


def criar_contexto(precisao=PRECISAO_EXATA, arredondamento=ROUND_HALF_UP):
    """Cria um contexto Decimal (precisão = nº de dígitos que ele mantém)."""
    return Context(prec=precisao, rounding=arredondamento,
                   Emin=-LIMITE_EXP_CONTEXTO, Emax=LIMITE_EXP_CONTEXTO)


CTX_EXATO = criar_contexto()


# =====================================================================
# 2. NORMALIZAÇÃO  (item 3.2 do enunciado)
# =====================================================================

def normalizar(valor):
    """
    Exemplos:
        123.45   ->  (+1, 0.12345, 3)      porque 123.45 = 0.12345 × 10³
        0.00004  ->  (+1, 0.4,    -4)      porque 0.00004 = 0.4 × 10⁻⁴
        -0.7655  ->  (-1, 0.7655,  0)
    """
    if valor == 0:
        return 1, Decimal(0), 0
    sinal = -1 if valor < 0 else 1
    absoluto = valor.copy_abs()
    expoente = absoluto.adjusted() + 1
    mantissa = absoluto.scaleb(-expoente, CTX_EXATO)
    return sinal, mantissa, expoente


# =====================================================================
# 3. AJUSTE DE PRECISÃO  (o coração do trabalho)
# =====================================================================

def _inteiro_pelo_metodo(positivo, metodo):
    """Transforma um número POSITIVO em inteiro, conforme o método.

        truncamento    : descarta a parte fracionária       (6666.6 -> 6666)
        arredondamento : soma 0.5 e descarta a fracionária  (6666.6 -> 6667,
                                                             6666.4 -> 6666)
    """
    if metodo == "arredondamento":
        positivo = CTX_EXATO.add(positivo, Decimal("0.5"))
    return positivo.to_integral_value(rounding=ROUND_DOWN, context=CTX_EXATO)


def ajustar_precisao(valor, n, metodo, tipo):
    """

    ALGORITMO (tipo "significativos"), exemplo com 0.66666, n = 4:
        1. normaliza:  0.66666 = 0.66666 × 10⁰   (mantissa 0.66666, expoente 0)
        2. desloca n casas a mantissa:   0.66666 → 6666.6
        3. aplica o método na parte fracionária:
               truncamento    -> 6666
               arredondamento -> 6667   (6666.6 + 0.5 = 6667.1 → 6667)
        4. volta as n casas:  6666 → 0.6666   ou   6667 → 0.6667
        5. desnormaliza (× 10^expoente) e devolve o sinal.

    No tipo "decimais" é o mesmo algoritmo sem normalizar: desloca n casas o
    próprio número (1.13572 → 11357.2 → 11357 → 1.1357).

    """

    # TESTES DE ERROS

    if metodo not in METODOS_VALIDOS:
        raise ErroSimulador(f"Método de ajuste desconhecido: {metodo}")
    if tipo not in TIPOS_VALIDOS:
        raise ErroSimulador(f"Tipo de ajuste desconhecido: {tipo}")
    if not (N_MIN <= n <= N_MAX):
        raise ErroSimulador(f"n deve estar entre {N_MIN} e {N_MAX}.")
    if valor == 0:
        return Decimal(0)

    if tipo == "significativos":
        sinal, mantissa, expoente = normalizar(valor)                 # passo 1
        deslocada = mantissa.scaleb(n, CTX_EXATO)                     # passo 2
        inteiro = _inteiro_pelo_metodo(deslocada, metodo)             # passo 3
        mantissa_ajustada = inteiro.scaleb(-n, CTX_EXATO)             # passo 4
        resultado = mantissa_ajustada.scaleb(expoente, CTX_EXATO)     # passo 5
    else:  # "decimais"
        sinal = -1 if valor < 0 else 1
        deslocado = valor.copy_abs().scaleb(n, CTX_EXATO)
        inteiro = _inteiro_pelo_metodo(deslocado, metodo)
        resultado = inteiro.scaleb(-n, CTX_EXATO)

    if resultado == 0:           # evita "-0": o valor ajustado virou zero
        return Decimal(0)
    return resultado if sinal > 0 else resultado.copy_negate()


# =====================================================================
# 4. OPERAÇÃO
# =====================================================================

def operar(x, y, op):

    if op == "+":
        return CTX_EXATO.add(x, y)
    if op == "-":
        return CTX_EXATO.subtract(x, y)
    if op == "*":
        return CTX_EXATO.multiply(x, y)
    if op == "/":
        return CTX_EXATO.divide(x, y)
    raise ErroSimulador(f"Operação desconhecida: {op}")


# =====================================================================
# 5. ERROS ABSOLUTO E RELATIVO  (item 3.3 do enunciado)
# =====================================================================

def erro_absoluto(exato, aprox):
    return CTX_EXATO.subtract(exato, aprox).copy_abs()


def erro_relativo(ea, aprox):
    """Er = Ea / | valor aproximado |   (definição do enunciado).

    Casos especiais:
      * aproximado ≠ 0                 -> Er = Ea / |aprox|
      * aproximado = 0 e Ea = 0        -> Er = 0  (não houve erro nenhum)
      * aproximado = 0 e Ea ≠ 0        -> None = INDEFINIDO. O enunciado só
        define o erro relativo "quando o valor aproximado for diferente de
        zero" (dividir por zero não tem sentido).
    """
    if aprox == 0:
        return Decimal(0) if ea == 0 else None
    return CTX_EXATO.divide(ea, aprox.copy_abs())


# =====================================================================
# 6. SIMULAÇÃO DE UMA OPERAÇÃO  (itens 3.1 a 3.3 do enunciado)
# =====================================================================

def simular_operacao(x, y, op, n, metodo, tipo, armazenar_entradas):
    """Executa UMA operação completa na máquina hipotética.

    Fluxo:
        exato  = x op y                              (precisão máxima)
        [x_maq, y_maq = ajustar(x), ajustar(y)]      (só se armazenar_entradas)
        bruto  = x_maq op y_maq   (ou o próprio exato, se não armazenar)
        aprox  = ajustar(bruto)                      (normaliza e corta/arredonda)
        Ea, Er                                       (item 3.3)

    Devolve um dicionário com tudo (usado pela interface e pelos testes).
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
        bruto = operar(x_maq, y_maq, op)     # conta com os valores da máquina
    else:
        x_maq = y_maq = None
        bruto = exato                         # item 3.2: ajusta só o resultado

    aprox = ajustar_precisao(bruto, n, metodo, tipo)
    ea = erro_absoluto(exato, aprox)
    er = erro_relativo(ea, aprox)
    return {"x": x, "y": y, "op": op, "n": n, "metodo": metodo, "tipo": tipo,
            "armazenar": armazenar_entradas, "exato": exato, "x_maq": x_maq,
            "y_maq": y_maq, "bruto": bruto, "aprox": aprox, "ea": ea, "er": er}


# =====================================================================
# 7. PROPAGAÇÃO DE ERROS EM SEQUÊNCIA  (Exemplo 3 do enunciado)
# =====================================================================

def simular_operacao_sequencial(valor_base, termo, op, quantidade, n, metodo, tipo,
                                armazenar_operandos):
    """Repete uma operação várias vezes, ajustando o resultado a CADA passo."""

    inicio = termo if valor_base is None else valor_base
    operacoes = quantidade - 1 if valor_base is None else quantidade

    termo_usado = ajustar_precisao(termo, n, metodo, tipo) if armazenar_operandos else termo
    acumulado = ajustar_precisao(inicio, n, metodo, tipo) if armazenar_operandos else inicio
    exato_acumulado = inicio

    if op == "/" and termo == 0:
        raise ErroSimulador("Divisão por zero: o termo repetido não pode ser 0.")
    if op == "/" and termo_usado == 0:
        raise ErroSimulador("Divisão por zero: o termo repetido virou 0 ao ser guardado "
                            "na máquina. Aumente n ou desmarque o armazenamento do termo.")

    passos = []
    for passo in range(1, operacoes + 1):
        exato_acumulado = operar(exato_acumulado, termo, op)    # referência, sem ajuste
        bruto = operar(acumulado, termo_usado, op)               # conta da máquina
        novo = ajustar_precisao(bruto, n, metodo, tipo)          # ajuste a cada passo
        passos.append({
            "passo": passo, "anterior": acumulado, "termo": termo_usado, "op": op,
            "bruto": bruto, "apos": novo, "exato_parcial": exato_acumulado,
            "erro": erro_absoluto(exato_acumulado, novo),
        })
        acumulado = novo

    ea = erro_absoluto(exato_acumulado, acumulado)
    return {
        "passos": passos, "exato": exato_acumulado, "final": acumulado, "ea": ea,
        "er": erro_relativo(ea, acumulado), "termo_usado": termo_usado,
        "base_usada": inicio, "op": op, "quantidade": quantidade, "n": n,
        "metodo": metodo, "tipo": tipo, "armazenar": armazenar_operandos,
        "tipo_resultado": "sequencial",
    }


# =====================================================================
# 8. CANCELAMENTO SUBTRATIVO  (Exemplo 2 do enunciado)
# =====================================================================

def digitos_perdidos_por_cancelamento(r):
    """Detecta cancelamento subtrativo e devolve quantas ORDENS DE GRANDEZA o
    resultado ficou menor que os operandos (0 = não houve cancelamento)."""
    if r["op"] not in ("+", "-") or r["exato"] == 0:
        return 0
    maior = max(r["x"].copy_abs(), r["y"].copy_abs())
    if CTX_EXATO.multiply(r["exato"].copy_abs(), Decimal(100)) <= maior:
        return maior.adjusted() - r["exato"].adjusted()
    return 0
